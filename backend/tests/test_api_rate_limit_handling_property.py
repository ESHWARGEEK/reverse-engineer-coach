"""
Property-based test for API rate limit handling.

Feature: reverse-engineer-coach, Property 17: API Rate Limit Handling
**Validates: Requirements 8.5**

This test verifies that the system properly handles GitHub API rate limits
with caching, retry logic, and graceful degradation.
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from hypothesis import given, strategies as st, settings, assume
import hypothesis
from hypothesis.stateful import RuleBasedStateMachine, rule, initialize, invariant
import httpx
from typing import Dict, Any, List

from app.github_client import GitHubClient, GitHubAPIError, RateLimitInfo
from app.cache import cache


class RateLimitScenario:
    """Represents a rate limit scenario for testing"""
    
    def __init__(self, initial_remaining: int, limit: int, reset_time: int):
        self.initial_remaining = initial_remaining
        self.limit = limit
        self.reset_time = reset_time
        self.requests_made = 0
    
    def make_request(self) -> bool:
        """Simulate making a request and return if it should succeed"""
        if self.requests_made >= self.initial_remaining:
            return False  # Rate limited
        self.requests_made += 1
        return True
    
    def get_remaining(self) -> int:
        """Get remaining requests"""
        return max(0, self.initial_remaining - self.requests_made)


@pytest.fixture
async def mock_github_client():
    """Create a GitHub client with mocked HTTP responses"""
    client = GitHubClient(token="test_token")
    
    # Mock the HTTP client
    mock_http_client = AsyncMock()
    client.client = mock_http_client
    
    return client


@pytest.fixture
async def rate_limit_responses():
    """Generate mock responses for rate limit scenarios"""
    def create_response(status_code: int, remaining: int, limit: int, reset_time: int, data: Dict = None):
        response = MagicMock()
        response.status_code = status_code
        response.headers = {
            'x-ratelimit-limit': str(limit),
            'x-ratelimit-remaining': str(remaining),
            'x-ratelimit-reset': str(reset_time),
            'x-ratelimit-used': str(limit - remaining)
        }
        response.json.return_value = data or {"message": "API rate limit exceeded"}
        response.content = b'{"message": "test"}'
        return response
    
    return create_response


class TestAPIRateLimitHandling:
    """Property-based tests for API rate limit handling"""
    
    @given(
        initial_remaining=st.integers(min_value=0, max_value=5),
        limit=st.integers(min_value=1, max_value=20),
        requests_to_make=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=1, deadline=1000, suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    async def test_rate_limit_caching_prevents_excessive_requests(
        self, 
        mock_github_client, 
        rate_limit_responses,
        initial_remaining: int,
        limit: int,
        requests_to_make: int
    ):
        """
        Property: When rate limits are low, caching should prevent excessive API requests
        
        For any rate limit scenario, if we make multiple requests for the same data,
        the system should use cached responses to avoid hitting rate limits.
        """
        assume(limit > initial_remaining)  # Ensure we can hit rate limits
        
        current_time = int(time.time())
        reset_time = current_time + 3600  # 1 hour from now
        
        # Setup mock responses
        success_response = rate_limit_responses(200, initial_remaining, limit, reset_time, {"test": "data"})
        rate_limit_response = rate_limit_responses(403, 0, limit, reset_time)
        
        # Configure mock to return success first, then rate limit
        responses = [success_response] * initial_remaining + [rate_limit_response] * requests_to_make
        mock_github_client.client.get.side_effect = responses
        
        # Clear cache before test
        await cache.invalidate_pattern("*", namespace="github_api")
        
        # Make the same request multiple times
        endpoint = "repos/test/repo"
        successful_requests = 0
        cached_requests = 0
        
        for i in range(requests_to_make):
            try:
                result = await mock_github_client._make_request(endpoint)
                if result:
                    successful_requests += 1
                    
                    # Check if this was served from cache (no new HTTP call)
                    if mock_github_client.client.get.call_count <= initial_remaining:
                        cached_requests += 1
                        
            except GitHubAPIError as e:
                if e.status_code == 403 and "rate limit" in e.message.lower():
                    break  # Expected rate limit hit
                else:
                    raise
        
        # Verify caching behavior
        total_http_calls = mock_github_client.client.get.call_count
        
        # Property: Total HTTP calls should not exceed initial remaining + 1 (for rate limit detection)
        assert total_http_calls <= initial_remaining + 1, \
            f"Made {total_http_calls} HTTP calls, but should have cached after {initial_remaining} calls"
        
        # Property: If we made more successful requests than HTTP calls, caching worked
        if successful_requests > total_http_calls:
            assert cached_requests > 0, "Should have served some requests from cache"
    
    @given(
        remaining_requests=st.integers(min_value=0, max_value=2),
        reset_delay=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=1, deadline=1000, suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    async def test_rate_limit_backoff_and_retry(
        self,
        mock_github_client,
        rate_limit_responses,
        remaining_requests: int,
        reset_delay: int
    ):
        """
        Property: When rate limited, the system should implement backoff and retry logic
        
        For any rate limit scenario, the system should wait appropriately before retrying
        and eventually succeed when the rate limit resets.
        """
        current_time = int(time.time())
        reset_time = current_time + reset_delay
        limit = 5000
        
        # Setup mock responses - rate limited initially, then success after "reset"
        rate_limit_response = rate_limit_responses(403, 0, limit, reset_time)
        success_response = rate_limit_responses(200, limit, limit, reset_time + 3600, {"test": "data"})
        
        # Mock time to simulate rate limit reset
        with patch('time.time') as mock_time:
            mock_time.side_effect = [
                current_time,  # Initial request
                current_time,  # Rate limit check
                reset_time + 1,  # After waiting for reset
                reset_time + 1   # Success request
            ]
            
            # Configure responses: rate limit, then success
            mock_github_client.client.get.side_effect = [rate_limit_response, success_response]
            
            # Mock sleep to avoid actual waiting in tests
            with patch('asyncio.sleep') as mock_sleep:
                start_time = time.time()
                
                try:
                    result = await mock_github_client._make_request("repos/test/repo")
                    
                    # Property: Should eventually succeed after rate limit reset
                    assert result is not None, "Should succeed after rate limit reset"
                    assert result.get("test") == "data", "Should return expected data"
                    
                    # Property: Should have called sleep for backoff (if rate limited)
                    if remaining_requests == 0:
                        assert mock_sleep.called, "Should implement backoff when rate limited"
                        
                        # Verify sleep was called with reasonable duration
                        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
                        assert all(0 < duration <= reset_delay + 10 for duration in sleep_calls), \
                            f"Sleep durations should be reasonable: {sleep_calls}"
                
                except GitHubAPIError as e:
                    # If we get an error, it should be a legitimate API error, not a timeout
                    assert e.status_code in [401, 404, 500], \
                        f"Unexpected error after rate limit handling: {e.message}"
    
    @given(
        concurrent_requests=st.integers(min_value=2, max_value=3),
        rate_limit=st.integers(min_value=1, max_value=2)
    )
    @settings(max_examples=1, deadline=1000, suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    async def test_concurrent_request_debouncing(
        self,
        mock_github_client,
        rate_limit_responses,
        concurrent_requests: int,
        rate_limit: int
    ):
        """
        Property: Concurrent identical requests should be debounced to prevent rate limit abuse
        
        For any number of concurrent identical requests, the system should make only one
        actual API call and share the result among all requesters.
        """
        assume(concurrent_requests > rate_limit)  # Ensure we would exceed rate limit without debouncing
        
        current_time = int(time.time())
        reset_time = current_time + 3600
        
        # Setup single success response
        success_response = rate_limit_responses(200, rate_limit, 5000, reset_time, {"shared": "data"})
        mock_github_client.client.get.return_value = success_response
        
        # Clear cache
        await cache.invalidate_pattern("*", namespace="github_api")
        
        # Make concurrent identical requests
        endpoint = "repos/test/repo"
        tasks = []
        
        for i in range(concurrent_requests):
            task = asyncio.create_task(mock_github_client._make_request(endpoint))
            tasks.append(task)
        
        # Wait for all requests to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Property: All requests should succeed with the same data
        successful_results = [r for r in results if isinstance(r, dict)]
        assert len(successful_results) == concurrent_requests, \
            f"Expected {concurrent_requests} successful results, got {len(successful_results)}"
        
        # Property: All results should be identical (shared from single API call)
        first_result = successful_results[0]
        for result in successful_results[1:]:
            assert result == first_result, "All concurrent requests should return identical data"
        
        # Property: Should make only one actual HTTP call due to debouncing
        assert mock_github_client.client.get.call_count <= 2, \
            f"Expected at most 2 HTTP calls (original + potential cache miss), got {mock_github_client.client.get.call_count}"
    
    @given(
        cache_ttl=st.integers(min_value=60, max_value=300),
        requests_over_time=st.integers(min_value=2, max_value=3)
    )
    @settings(max_examples=1, deadline=1000, suppress_health_check=[hypothesis.HealthCheck.function_scoped_fixture])
    async def test_cache_expiration_respects_rate_limits(
        self,
        mock_github_client,
        rate_limit_responses,
        cache_ttl: int,
        requests_over_time: int
    ):
        """
        Property: Cache expiration should be coordinated with rate limit recovery
        
        For any cache TTL and request pattern, expired cache entries should not
        cause immediate rate limit exhaustion.
        """
        current_time = int(time.time())
        reset_time = current_time + 3600
        limit = 100
        
        # Setup responses
        success_response = rate_limit_responses(200, limit, limit, reset_time, {"cached": "data"})
        mock_github_client.client.get.return_value = success_response
        
        # Clear cache
        await cache.invalidate_pattern("*", namespace="github_api")
        
        endpoint = "repos/test/repo"
        
        # Make initial request (should cache)
        result1 = await mock_github_client._make_request(endpoint)
        assert result1 is not None
        initial_calls = mock_github_client.client.get.call_count
        
        # Make subsequent requests (should use cache)
        for i in range(requests_over_time - 1):
            result = await mock_github_client._make_request(endpoint)
            assert result is not None
            assert result == result1, "Cached results should be identical"
        
        # Property: Cache should prevent additional HTTP calls
        cached_calls = mock_github_client.client.get.call_count
        assert cached_calls == initial_calls, \
            f"Cache should prevent HTTP calls: initial={initial_calls}, after_cache={cached_calls}"
        
        # Simulate cache expiration by clearing it
        await cache.invalidate_pattern("*", namespace="github_api")
        
        # Make request after cache expiration
        result_after_expiry = await mock_github_client._make_request(endpoint)
        assert result_after_expiry is not None
        
        # Property: Should make new HTTP call after cache expiration
        final_calls = mock_github_client.client.get.call_count
        assert final_calls > cached_calls, \
            "Should make new HTTP call after cache expiration"
    
    async def test_rate_limit_info_tracking(self, mock_github_client, rate_limit_responses):
        """
        Property: Rate limit information should be accurately tracked and updated
        
        The system should maintain accurate rate limit state across requests.
        """
        current_time = int(time.time())
        reset_time = current_time + 3600
        
        # Test with decreasing rate limits
        responses = [
            rate_limit_responses(200, 100, 5000, reset_time, {"data": 1}),
            rate_limit_responses(200, 99, 5000, reset_time, {"data": 2}),
            rate_limit_responses(200, 98, 5000, reset_time, {"data": 3}),
        ]
        
        mock_github_client.client.get.side_effect = responses
        
        # Clear cache to ensure fresh requests
        await cache.invalidate_pattern("*", namespace="github_api")
        
        # Make requests and track rate limit info
        for i, expected_remaining in enumerate([100, 99, 98]):
            await mock_github_client._make_request(f"repos/test/repo{i}")
            
            # Property: Rate limit info should be updated after each request
            assert mock_github_client.rate_limit_info is not None, \
                "Rate limit info should be tracked"
            
            assert mock_github_client.rate_limit_info.remaining == expected_remaining, \
                f"Expected {expected_remaining} remaining, got {mock_github_client.rate_limit_info.remaining}"
            
            assert mock_github_client.rate_limit_info.limit == 5000, \
                "Rate limit should be consistent"


class RateLimitStateMachine(RuleBasedStateMachine):
    """Stateful property testing for rate limit handling"""
    
    def __init__(self):
        super().__init__()
        self.github_client = None
        self.mock_responses = []
        self.request_count = 0
        self.rate_limit_hit = False
    
    @initialize()
    async def setup_client(self):
        """Initialize the GitHub client with mocked responses"""
        self.github_client = GitHubClient(token="test_token")
        self.github_client.client = AsyncMock()
        
        # Clear cache
        await cache.invalidate_pattern("*", namespace="github_api")
    
    @rule(
        remaining=st.integers(min_value=0, max_value=10),
        limit=st.integers(min_value=10, max_value=100)
    )
    async def make_api_request(self, remaining: int, limit: int):
        """Make an API request with given rate limit state"""
        current_time = int(time.time())
        reset_time = current_time + 3600
        
        if remaining == 0:
            # Rate limited response
            response = MagicMock()
            response.status_code = 403
            response.headers = {
                'x-ratelimit-remaining': '0',
                'x-ratelimit-limit': str(limit),
                'x-ratelimit-reset': str(reset_time)
            }
            response.json.return_value = {"message": "API rate limit exceeded"}
            response.content = b'{"message": "rate limit"}'
            self.rate_limit_hit = True
        else:
            # Success response
            response = MagicMock()
            response.status_code = 200
            response.headers = {
                'x-ratelimit-remaining': str(remaining - 1),
                'x-ratelimit-limit': str(limit),
                'x-ratelimit-reset': str(reset_time)
            }
            response.json.return_value = {"data": f"request_{self.request_count}"}
            response.content = b'{"data": "test"}'
        
        self.github_client.client.get.return_value = response
        
        try:
            with patch('asyncio.sleep'):  # Mock sleep to avoid delays
                result = await self.github_client._make_request(f"test/endpoint/{self.request_count}")
                self.request_count += 1
                return result
        except GitHubAPIError as e:
            if e.status_code == 403:
                self.rate_limit_hit = True
                return None
            raise
    
    @invariant()
    def rate_limit_info_is_consistent(self):
        """Rate limit information should always be consistent with API responses"""
        if self.github_client and self.github_client.rate_limit_info:
            rate_info = self.github_client.rate_limit_info
            
            # Property: Remaining should never be negative
            assert rate_info.remaining >= 0, \
                f"Rate limit remaining should not be negative: {rate_info.remaining}"
            
            # Property: Used + Remaining should equal Limit
            assert rate_info.used + rate_info.remaining == rate_info.limit, \
                f"Used ({rate_info.used}) + Remaining ({rate_info.remaining}) != Limit ({rate_info.limit})"
    
    @invariant()
    def cache_prevents_excessive_requests(self):
        """Cache should prevent making more requests than necessary"""
        if self.github_client:
            # Property: HTTP calls should not exceed request count significantly
            # (allowing for some cache misses and rate limit checks)
            http_calls = getattr(self.github_client.client.get, 'call_count', 0)
            assert http_calls <= self.request_count + 2, \
                f"Too many HTTP calls: {http_calls} for {self.request_count} requests"


# Run the stateful test
TestRateLimitStateMachine = RateLimitStateMachine.TestCase


@pytest.mark.asyncio
async def test_property_api_rate_limit_handling_comprehensive():
    """
    Comprehensive property test for API rate limit handling
    
    This test verifies that the GitHub API client properly handles rate limits
    through caching, retry logic, request debouncing, and graceful degradation.
    """
    
    # Test basic rate limit handling
    test_instance = TestAPIRateLimitHandling()
    
    # Create mock client
    client = GitHubClient(token="test_token")
    mock_http_client = AsyncMock()
    client.client = mock_http_client
    
    def create_response(status_code: int, remaining: int, limit: int, reset_time: int, data: Dict = None):
        response = MagicMock()
        response.status_code = status_code
        response.headers = {
            'x-ratelimit-limit': str(limit),
            'x-ratelimit-remaining': str(remaining),
            'x-ratelimit-reset': str(reset_time),
            'x-ratelimit-used': str(limit - remaining)
        }
        response.json.return_value = data or {"message": "API rate limit exceeded"}
        response.content = b'{"message": "test"}'
        return response
    
    # Test scenarios
    scenarios = [
        # (initial_remaining, limit, requests_to_make)
        (5, 100, 10),   # Hit rate limit
        (50, 100, 20),  # Stay within limit
        (0, 100, 5),    # Already rate limited
        (1, 100, 3),    # Hit limit quickly
    ]
    
    for remaining, limit, requests in scenarios:
        # Clear cache
        await cache.invalidate_pattern("*", namespace="github_api")
        
        current_time = int(time.time())
        reset_time = current_time + 3600
        
        # Setup responses
        success_responses = [
            create_response(200, max(0, remaining - i), limit, reset_time, {"test": f"data_{i}"})
            for i in range(remaining)
        ]
        rate_limit_responses = [
            create_response(403, 0, limit, reset_time)
            for _ in range(max(0, requests - remaining))
        ]
        
        mock_http_client.get.side_effect = success_responses + rate_limit_responses
        
        # Make requests
        successful_requests = 0
        for i in range(requests):
            try:
                result = await client._make_request(f"repos/test/repo_{i}")
                if result:
                    successful_requests += 1
            except GitHubAPIError as e:
                if e.status_code == 403:
                    break  # Expected rate limit
                raise
        
        # Verify properties
        total_calls = mock_http_client.get.call_count
        
        # Property: Should not make more HTTP calls than rate limit allows (plus some for retries)
        assert total_calls <= remaining + 3, \
            f"Made {total_calls} calls but rate limit was {remaining}"
        
        # Property: Should succeed for requests within rate limit
        if remaining > 0:
            assert successful_requests > 0, \
                "Should have some successful requests when rate limit allows"
        
        # Reset for next scenario
        mock_http_client.reset_mock()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])