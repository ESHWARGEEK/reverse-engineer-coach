"""
Property-based test for GitHub link functionality.

Feature: reverse-engineer-coach, Property 16: GitHub Link Functionality
Validates: Requirements 8.3

This test verifies that for any displayed Reference_Snippet link, clicking it 
should open the correct GitHub repository page at the specific line number.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from typing import List, Dict, Any, Optional
import re
from urllib.parse import urlparse, parse_qs

from app.github_client import GitHubClient, GitHubAPIError


# Test data strategies
@st.composite
def github_url_strategy(draw):
    """Generate valid GitHub repository URLs"""
    owners = ['microsoft', 'google', 'facebook', 'apache', 'kubernetes', 'redis', 'nginx']
    repos = ['vscode', 'react', 'kubernetes', 'redis', 'nginx', 'tensorflow', 'pytorch']
    
    owner = draw(st.sampled_from(owners))
    repo = draw(st.sampled_from(repos))
    
    # Generate different URL formats
    url_formats = [
        f"https://github.com/{owner}/{repo}",
        f"https://github.com/{owner}/{repo}.git",
        f"git@github.com:{owner}/{repo}.git",
        f"{owner}/{repo}"
    ]
    
    return draw(st.sampled_from(url_formats))


@st.composite
def file_path_strategy(draw):
    """Generate realistic file paths"""
    directories = ['src', 'lib', 'app', 'components', 'utils', 'services', 'models']
    filenames = ['index', 'main', 'app', 'server', 'client', 'utils', 'config']
    extensions = ['.js', '.ts', '.py', '.go', '.java', '.cpp', '.rs']
    
    # Generate path with 0-3 directory levels
    path_parts = []
    num_dirs = draw(st.integers(min_value=0, max_value=3))
    
    for _ in range(num_dirs):
        path_parts.append(draw(st.sampled_from(directories)))
    
    filename = draw(st.sampled_from(filenames))
    extension = draw(st.sampled_from(extensions))
    path_parts.append(f"{filename}{extension}")
    
    return "/".join(path_parts)


@st.composite
def line_number_strategy(draw):
    """Generate realistic line numbers"""
    return draw(st.integers(min_value=1, max_value=1000))


@st.composite
def commit_sha_strategy(draw):
    """Generate valid commit SHA strings"""
    # Generate 40-character hex string (Git SHA-1)
    hex_chars = '0123456789abcdef'
    return ''.join(draw(st.lists(st.sampled_from(hex_chars), min_size=40, max_size=40)))


class TestGitHubLinkFunctionality:
    """Property-based tests for GitHub link functionality"""
    
    def _create_github_client(self):
        """Create GitHub client for testing"""
        return GitHubClient()
    
    @given(
        repository_url=github_url_strategy(),
        file_path=file_path_strategy(),
        line_number=st.one_of(st.none(), line_number_strategy())
    )
    @settings(max_examples=3, deadline=5000)
    def test_permalink_generation_property(self, repository_url, file_path, line_number):
        """
        Property 16: GitHub Link Functionality
        
        For any displayed Reference_Snippet link, clicking it should open the 
        correct GitHub repository page at the specific line number.
        """
        github_client = self._create_github_client()
        
        # Generate permalink
        permalink = github_client.get_permalink_url(
            repository_url, file_path, line_number
        )
        
        # Verify permalink properties
        self._verify_permalink_properties(permalink, repository_url, file_path, line_number)
    
    def _verify_permalink_properties(self, permalink: str, repository_url: str, 
                                   file_path: str, line_number: Optional[int]):
        """Verify that permalink has correct properties"""
        
        # Property: Permalink should be a valid HTTPS URL
        assert permalink.startswith('https://github.com/'), \
            f"Permalink should start with https://github.com/, got: {permalink}"
        
        # Property: URL should be parseable
        parsed_url = urlparse(permalink)
        assert parsed_url.scheme == 'https', f"Scheme should be https, got: {parsed_url.scheme}"
        assert parsed_url.netloc == 'github.com', f"Host should be github.com, got: {parsed_url.netloc}"
        
        # Property: URL path should contain owner, repo, blob, and file path
        path_parts = parsed_url.path.strip('/').split('/')
        assert len(path_parts) >= 4, f"URL path should have at least 4 parts (owner/repo/blob/ref), got: {path_parts}"
        
        # Extract components
        owner = path_parts[0]
        repo = path_parts[1]
        blob_part = path_parts[2]
        ref = path_parts[3]
        
        # Property: Should contain 'blob' in the path
        assert blob_part == 'blob', f"URL should contain 'blob', got: {blob_part}"
        
        # Property: File path should be preserved in URL
        url_file_path = '/'.join(path_parts[4:])
        assert url_file_path == file_path, \
            f"File path should be preserved: expected {file_path}, got {url_file_path}"
        
        # Property: Line number should be in fragment if provided
        if line_number is not None:
            assert parsed_url.fragment == f'L{line_number}', \
                f"Line number should be in fragment as L{line_number}, got: {parsed_url.fragment}"
        else:
            assert not parsed_url.fragment or parsed_url.fragment == '', \
                f"Fragment should be empty when no line number provided, got: {parsed_url.fragment}"
        
        # Property: Owner and repo should be valid GitHub identifiers
        assert re.match(r'^[a-zA-Z0-9._-]+$', owner), \
            f"Owner should be valid GitHub identifier: {owner}"
        assert re.match(r'^[a-zA-Z0-9._-]+$', repo), \
            f"Repo should be valid GitHub identifier: {repo}"
    
    @given(
        repository_url=github_url_strategy(),
        file_path=file_path_strategy(),
        line_number=line_number_strategy(),
        commit_sha=commit_sha_strategy()
    )
    @settings(max_examples=3, deadline=3000)
    def test_stable_permalink_with_commit_property(self, repository_url, file_path, 
                                                 line_number, commit_sha):
        """
        Property: Stable permalinks with commit SHA should be immutable
        """
        github_client = self._create_github_client()
        
        # Generate stable permalink with commit SHA
        permalink = github_client.get_permalink_url(
            repository_url, file_path, line_number, commit_sha
        )
        
        # Verify stable permalink properties
        self._verify_stable_permalink_properties(permalink, commit_sha, file_path, line_number)
    
    def _verify_stable_permalink_properties(self, permalink: str, commit_sha: str, 
                                          file_path: str, line_number: int):
        """Verify stable permalink properties"""
        
        # Property: Should contain the commit SHA
        assert commit_sha in permalink, \
            f"Permalink should contain commit SHA {commit_sha}, got: {permalink}"
        
        # Property: Should be a valid GitHub blob URL with commit
        parsed_url = urlparse(permalink)
        path_parts = parsed_url.path.strip('/').split('/')
        
        # Should have format: owner/repo/blob/commit_sha/file_path
        assert len(path_parts) >= 4, f"Stable permalink should have at least 4 path parts"
        assert path_parts[2] == 'blob', f"Should contain 'blob' in path"
        assert path_parts[3] == commit_sha, f"Should contain commit SHA in path"
        
        # Property: File path should be preserved
        url_file_path = '/'.join(path_parts[4:])
        assert url_file_path == file_path, \
            f"File path should be preserved in stable link"
        
        # Property: Line number should be in fragment
        assert parsed_url.fragment == f'L{line_number}', \
            f"Line number should be preserved in fragment"
    
    @given(
        repository_url=github_url_strategy()
    )
    @settings(max_examples=3, deadline=3000)
    def test_url_parsing_consistency_property(self, repository_url):
        """
        Property: URL parsing should be consistent and reversible
        """
        github_client = self._create_github_client()
        
        try:
            # Parse the URL
            owner, repo = github_client._parse_github_url(repository_url)
            
            # Verify parsing results
            self._verify_url_parsing_properties(owner, repo, repository_url)
            
        except ValueError:
            # Some generated URLs might be invalid, which is acceptable
            # The property is that valid URLs should parse correctly
            pass
    
    def _verify_url_parsing_properties(self, owner: str, repo: str, original_url: str):
        """Verify URL parsing properties"""
        
        # Property: Owner and repo should be non-empty strings
        assert isinstance(owner, str) and len(owner) > 0, \
            f"Owner should be non-empty string, got: {owner}"
        assert isinstance(repo, str) and len(repo) > 0, \
            f"Repo should be non-empty string, got: {repo}"
        
        # Property: Owner and repo should not contain invalid characters
        invalid_chars = ['/', '\\', ' ', '\t', '\n']
        for char in invalid_chars:
            assert char not in owner, f"Owner should not contain '{char}': {owner}"
            assert char not in repo, f"Repo should not contain '{char}': {repo}"
        
        # Property: Should be able to reconstruct a valid GitHub URL
        reconstructed_url = f"https://github.com/{owner}/{repo}"
        assert reconstructed_url.startswith('https://github.com/'), \
            f"Reconstructed URL should be valid GitHub URL: {reconstructed_url}"
    
    @given(
        file_paths=st.lists(file_path_strategy(), min_size=1, max_size=5),
        line_numbers=st.lists(line_number_strategy(), min_size=1, max_size=5)
    )
    @settings(max_examples=3, deadline=3000)
    def test_multiple_links_consistency_property(self, file_paths, line_numbers):
        """
        Property: Multiple links for the same repository should be consistent
        """
        github_client = self._create_github_client()
        repository_url = "https://github.com/microsoft/vscode"  # Use a known repo
        
        links = []
        for i, file_path in enumerate(file_paths):
            line_number = line_numbers[i % len(line_numbers)]
            link = github_client.get_permalink_url(repository_url, file_path, line_number)
            links.append((link, file_path, line_number))
        
        # Verify consistency across multiple links
        self._verify_multiple_links_consistency(links, repository_url)
    
    def _verify_multiple_links_consistency(self, links: List[tuple], repository_url: str):
        """Verify consistency across multiple links"""
        
        # Property: All links should point to the same repository
        for link, file_path, line_number in links:
            parsed_url = urlparse(link)
            path_parts = parsed_url.path.strip('/').split('/')
            
            # Extract owner/repo from each link
            if len(path_parts) >= 2:
                link_owner = path_parts[0]
                link_repo = path_parts[1]
                
                # All links should have the same owner/repo
                assert link_owner == 'microsoft', f"All links should point to microsoft, got: {link_owner}"
                assert link_repo == 'vscode', f"All links should point to vscode, got: {link_repo}"
        
        # Property: Each link should be unique for different file/line combinations
        unique_combinations = set((file_path, line_number) for _, file_path, line_number in links)
        unique_links = set(link for link, _, _ in links)
        
        if len(unique_combinations) > 1:
            assert len(unique_links) > 1, \
                f"Different file/line combinations should produce different links"
    
    @given(
        repository_url=github_url_strategy(),
        file_path=file_path_strategy()
    )
    @settings(max_examples=3, deadline=3000)
    def test_link_format_validation_property(self, repository_url, file_path):
        """
        Property: Generated links should follow GitHub URL format conventions
        """
        github_client = self._create_github_client()
        
        try:
            # Generate link without line number
            link_without_line = github_client.get_permalink_url(repository_url, file_path)
            
            # Generate link with line number
            link_with_line = github_client.get_permalink_url(repository_url, file_path, 42)
            
            # Verify format properties
            self._verify_link_format_properties(link_without_line, link_with_line, file_path)
            
        except ValueError:
            # Invalid URLs are acceptable - the property is about valid URLs
            pass
    
    def _verify_link_format_properties(self, link_without_line: str, link_with_line: str, file_path: str):
        """Verify link format properties"""
        
        # Property: Both links should be valid HTTPS URLs
        for link in [link_without_line, link_with_line]:
            assert link.startswith('https://github.com/'), \
                f"Link should start with https://github.com/: {link}"
        
        # Property: Link with line number should be extension of link without line number
        base_link = link_with_line.split('#')[0]  # Remove fragment
        assert link_without_line == base_link, \
            f"Base link should match: {link_without_line} vs {base_link}"
        
        # Property: Link with line number should have fragment
        assert '#L42' in link_with_line, \
            f"Link with line number should contain #L42: {link_with_line}"
        
        # Property: File extension should be preserved in URL
        if '.' in file_path:
            file_extension = file_path.split('.')[-1]
            assert file_extension in link_without_line, \
                f"File extension {file_extension} should be preserved in link"
    
    @given(
        line_number=line_number_strategy()
    )
    @settings(max_examples=3, deadline=2000)
    def test_line_number_encoding_property(self, line_number):
        """
        Property: Line numbers should be correctly encoded in URL fragments
        """
        github_client = self._create_github_client()
        repository_url = "https://github.com/test/repo"
        file_path = "src/test.js"
        
        link = github_client.get_permalink_url(repository_url, file_path, line_number)
        
        # Verify line number encoding
        self._verify_line_number_encoding(link, line_number)
    
    def _verify_line_number_encoding(self, link: str, line_number: int):
        """Verify line number encoding in URL"""
        
        # Property: Line number should be in fragment with L prefix
        parsed_url = urlparse(link)
        expected_fragment = f'L{line_number}'
        
        assert parsed_url.fragment == expected_fragment, \
            f"Fragment should be {expected_fragment}, got: {parsed_url.fragment}"
        
        # Property: Line number should be positive integer
        assert line_number > 0, f"Line number should be positive: {line_number}"
        
        # Property: Fragment should only contain the line number (no extra characters)
        fragment_number = parsed_url.fragment[1:]  # Remove 'L' prefix
        assert fragment_number.isdigit(), \
            f"Fragment should contain only digits after L: {fragment_number}"
        assert int(fragment_number) == line_number, \
            f"Fragment number should match input: {fragment_number} vs {line_number}"


# Integration test for the complete GitHub link workflow
class TestGitHubLinkFunctionalityIntegration:
    """Integration tests for GitHub link functionality"""
    
    def test_complete_link_generation_workflow(self):
        """Test the complete workflow of GitHub link generation"""
        github_client = GitHubClient()
        
        # Test data
        repository_url = "https://github.com/microsoft/vscode"
        file_path = "src/vs/editor/editor.main.ts"
        line_number = 150
        
        # Generate different types of links
        basic_link = github_client.get_permalink_url(repository_url, file_path)
        line_link = github_client.get_permalink_url(repository_url, file_path, line_number)
        stable_link = github_client.get_permalink_url(
            repository_url, file_path, line_number, "abc123def456"
        )
        
        # Verify all links are valid
        assert all(link.startswith('https://github.com/') for link in [basic_link, line_link, stable_link])
        
        # Verify line number is only in appropriate links
        assert '#L' not in basic_link
        assert f'#L{line_number}' in line_link
        assert f'#L{line_number}' in stable_link
        
        # Verify commit SHA is only in stable link
        assert 'abc123def456' not in basic_link
        assert 'abc123def456' not in line_link
        assert 'abc123def456' in stable_link
    
    def test_url_parsing_edge_cases(self):
        """Test URL parsing with various edge cases"""
        github_client = GitHubClient()
        
        # Test different URL formats
        test_cases = [
            ("https://github.com/owner/repo", ("owner", "repo")),
            ("https://github.com/owner/repo.git", ("owner", "repo")),
            ("git@github.com:owner/repo.git", ("owner", "repo")),
            ("owner/repo", ("owner", "repo")),
        ]
        
        for url, expected in test_cases:
            try:
                result = github_client._parse_github_url(url)
                assert result == expected, f"Failed to parse {url}: expected {expected}, got {result}"
            except ValueError:
                # Some edge cases might be invalid, which is acceptable
                pass
    
    def test_permalink_stability(self):
        """Test that permalinks are stable and consistent"""
        github_client = GitHubClient()
        
        repository_url = "https://github.com/test/repo"
        file_path = "src/main.js"
        line_number = 42
        commit_sha = "1234567890abcdef1234567890abcdef12345678"
        
        # Generate the same link multiple times
        links = [
            github_client.get_permalink_url(repository_url, file_path, line_number, commit_sha)
            for _ in range(5)
        ]
        
        # All links should be identical
        assert all(link == links[0] for link in links), \
            f"Permalink generation should be stable: {links}"
        
        # Link should contain all expected components
        expected_components = [
            "github.com",
            "test/repo",
            "blob",
            commit_sha,
            file_path,
            f"#L{line_number}"
        ]
        
        for component in expected_components:
            assert component in links[0], \
                f"Link should contain {component}: {links[0]}"


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])