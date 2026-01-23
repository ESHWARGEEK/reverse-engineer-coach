"""
Security Monitoring Service

Monitors security events and provides real-time threat detection and response.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from collections import defaultdict, deque
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .auth_logging_service import AuthEventLog, AuthEventType

@dataclass
class SecurityThreat:
    """Security threat detection result"""
    threat_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    ip_address: str
    description: str
    evidence: List[str]
    timestamp: datetime
    recommended_action: str

@dataclass
class IPAnalytics:
    """IP address analytics data"""
    ip_address: str
    total_requests: int
    failed_attempts: int
    success_rate: float
    first_seen: datetime
    last_seen: datetime
    user_agents: Set[str]
    event_types: Dict[str, int]

class SecurityMonitoringService:
    """Service for real-time security monitoring and threat detection"""
    
    def __init__(self):
        self.logger = logging.getLogger("security_monitoring")
        
        # In-memory tracking for real-time analysis
        self.ip_request_counts = defaultdict(lambda: deque(maxlen=100))
        self.failed_login_attempts = defaultdict(lambda: deque(maxlen=50))
        self.suspicious_ips = set()
        self.blocked_ips = set()
        
        # Thresholds for threat detection
        self.thresholds = {
            "max_requests_per_minute": 60,
            "max_failed_logins_per_hour": 10,
            "max_registration_attempts_per_hour": 5,
            "suspicious_user_agent_patterns": [
                "bot", "crawler", "scanner", "sqlmap", "nikto", "nmap"
            ],
            "rate_limit_threshold": 100,
            "brute_force_threshold": 5
        }
    
    async def analyze_auth_event(self, event_data: Dict, db: Session) -> Optional[SecurityThreat]:
        """Analyze an authentication event for security threats"""
        
        ip_address = event_data.get("ip_address")
        event_type = event_data.get("event_type")
        success = event_data.get("success", False)
        user_agent = event_data.get("user_agent", "")
        
        if not ip_address:
            return None
        
        # Update real-time tracking
        self._update_ip_tracking(ip_address, event_type, success, user_agent)
        
        # Check for various threat patterns
        threats = []
        
        # Check for brute force attacks
        brute_force_threat = await self._check_brute_force_attack(ip_address, db)
        if brute_force_threat:
            threats.append(brute_force_threat)
        
        # Check for rate limiting violations
        rate_limit_threat = self._check_rate_limiting_violation(ip_address)
        if rate_limit_threat:
            threats.append(rate_limit_threat)
        
        # Check for suspicious user agents
        user_agent_threat = self._check_suspicious_user_agent(ip_address, user_agent)
        if user_agent_threat:
            threats.append(user_agent_threat)
        
        # Check for registration abuse
        if event_type == AuthEventType.REGISTER_FAILED.value:
            registration_threat = await self._check_registration_abuse(ip_address, db)
            if registration_threat:
                threats.append(registration_threat)
        
        # Check for credential stuffing
        credential_stuffing_threat = await self._check_credential_stuffing(ip_address, db)
        if credential_stuffing_threat:
            threats.append(credential_stuffing_threat)
        
        # Return the highest severity threat
        if threats:
            threats.sort(key=lambda t: self._get_severity_score(t.severity), reverse=True)
            return threats[0]
        
        return None
    
    def _update_ip_tracking(self, ip_address: str, event_type: str, success: bool, user_agent: str):
        """Update real-time IP tracking data"""
        now = datetime.utcnow()
        
        # Track request counts
        self.ip_request_counts[ip_address].append(now)
        
        # Track failed login attempts
        if event_type == AuthEventType.LOGIN_FAILED.value:
            self.failed_login_attempts[ip_address].append(now)
    
    async def _check_brute_force_attack(self, ip_address: str, db: Session) -> Optional[SecurityThreat]:
        """Check for brute force attack patterns"""
        
        # Check recent failed login attempts from database
        recent_time = datetime.utcnow() - timedelta(hours=1)
        
        failed_attempts = db.query(func.count(AuthEventLog.id)).filter(
            and_(
                AuthEventLog.ip_address == ip_address,
                AuthEventLog.event_type == AuthEventType.LOGIN_FAILED.value,
                AuthEventLog.timestamp >= recent_time
            )
        ).scalar()
        
        if failed_attempts >= self.thresholds["brute_force_threshold"]:
            return SecurityThreat(
                threat_type="BRUTE_FORCE_ATTACK",
                severity="HIGH",
                ip_address=ip_address,
                description=f"Brute force attack detected: {failed_attempts} failed login attempts in the last hour",
                evidence=[f"Failed login attempts: {failed_attempts}"],
                timestamp=datetime.utcnow(),
                recommended_action="Block IP address and alert security team"
            )
        
        return None
    
    def _check_rate_limiting_violation(self, ip_address: str) -> Optional[SecurityThreat]:
        """Check for rate limiting violations"""
        
        # Count requests in the last minute
        now = datetime.utcnow()
        one_minute_ago = now - timedelta(minutes=1)
        
        recent_requests = [
            req_time for req_time in self.ip_request_counts[ip_address]
            if req_time >= one_minute_ago
        ]
        
        if len(recent_requests) > self.thresholds["max_requests_per_minute"]:
            return SecurityThreat(
                threat_type="RATE_LIMIT_VIOLATION",
                severity="MEDIUM",
                ip_address=ip_address,
                description=f"Rate limit exceeded: {len(recent_requests)} requests in the last minute",
                evidence=[f"Request count: {len(recent_requests)}"],
                timestamp=datetime.utcnow(),
                recommended_action="Apply rate limiting and monitor for continued abuse"
            )
        
        return None
    
    def _check_suspicious_user_agent(self, ip_address: str, user_agent: str) -> Optional[SecurityThreat]:
        """Check for suspicious user agent patterns"""
        
        user_agent_lower = user_agent.lower()
        
        for pattern in self.thresholds["suspicious_user_agent_patterns"]:
            if pattern in user_agent_lower:
                return SecurityThreat(
                    threat_type="SUSPICIOUS_USER_AGENT",
                    severity="MEDIUM",
                    ip_address=ip_address,
                    description=f"Suspicious user agent detected: {user_agent}",
                    evidence=[f"User agent contains: {pattern}"],
                    timestamp=datetime.utcnow(),
                    recommended_action="Monitor closely and consider blocking if abuse continues"
                )
        
        return None
    
    async def _check_registration_abuse(self, ip_address: str, db: Session) -> Optional[SecurityThreat]:
        """Check for registration abuse patterns"""
        
        recent_time = datetime.utcnow() - timedelta(hours=1)
        
        registration_attempts = db.query(func.count(AuthEventLog.id)).filter(
            and_(
                AuthEventLog.ip_address == ip_address,
                or_(
                    AuthEventLog.event_type == AuthEventType.REGISTER_FAILED.value,
                    AuthEventLog.event_type == AuthEventType.REGISTER_SUCCESS.value
                ),
                AuthEventLog.timestamp >= recent_time
            )
        ).scalar()
        
        if registration_attempts >= self.thresholds["max_registration_attempts_per_hour"]:
            return SecurityThreat(
                threat_type="REGISTRATION_ABUSE",
                severity="MEDIUM",
                ip_address=ip_address,
                description=f"Registration abuse detected: {registration_attempts} attempts in the last hour",
                evidence=[f"Registration attempts: {registration_attempts}"],
                timestamp=datetime.utcnow(),
                recommended_action="Implement CAPTCHA and monitor for continued abuse"
            )
        
        return None
    
    async def _check_credential_stuffing(self, ip_address: str, db: Session) -> Optional[SecurityThreat]:
        """Check for credential stuffing attack patterns"""
        
        recent_time = datetime.utcnow() - timedelta(hours=1)
        
        # Check for failed logins across multiple different email addresses
        unique_emails = db.query(func.count(func.distinct(AuthEventLog.email))).filter(
            and_(
                AuthEventLog.ip_address == ip_address,
                AuthEventLog.event_type == AuthEventType.LOGIN_FAILED.value,
                AuthEventLog.timestamp >= recent_time,
                AuthEventLog.email.isnot(None)
            )
        ).scalar()
        
        total_failed = db.query(func.count(AuthEventLog.id)).filter(
            and_(
                AuthEventLog.ip_address == ip_address,
                AuthEventLog.event_type == AuthEventType.LOGIN_FAILED.value,
                AuthEventLog.timestamp >= recent_time
            )
        ).scalar()
        
        # If many different emails with failed attempts, likely credential stuffing
        if unique_emails >= 5 and total_failed >= 10:
            return SecurityThreat(
                threat_type="CREDENTIAL_STUFFING",
                severity="HIGH",
                ip_address=ip_address,
                description=f"Credential stuffing attack detected: {total_failed} failed logins across {unique_emails} different accounts",
                evidence=[
                    f"Unique email addresses: {unique_emails}",
                    f"Total failed attempts: {total_failed}"
                ],
                timestamp=datetime.utcnow(),
                recommended_action="Block IP address immediately and alert security team"
            )
        
        return None
    
    def _get_severity_score(self, severity: str) -> int:
        """Get numeric score for severity level"""
        scores = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        return scores.get(severity, 0)
    
    async def get_ip_analytics(self, ip_address: str, db: Session) -> IPAnalytics:
        """Get comprehensive analytics for an IP address"""
        
        # Query all events for this IP
        events = db.query(AuthEventLog).filter(
            AuthEventLog.ip_address == ip_address
        ).all()
        
        if not events:
            return IPAnalytics(
                ip_address=ip_address,
                total_requests=0,
                failed_attempts=0,
                success_rate=0.0,
                first_seen=datetime.utcnow(),
                last_seen=datetime.utcnow(),
                user_agents=set(),
                event_types={}
            )
        
        total_requests = len(events)
        failed_attempts = sum(1 for event in events if not event.success)
        success_rate = (total_requests - failed_attempts) / total_requests * 100
        
        user_agents = set(event.user_agent for event in events if event.user_agent)
        event_types = defaultdict(int)
        
        for event in events:
            event_types[event.event_type] += 1
        
        return IPAnalytics(
            ip_address=ip_address,
            total_requests=total_requests,
            failed_attempts=failed_attempts,
            success_rate=success_rate,
            first_seen=min(event.timestamp for event in events),
            last_seen=max(event.timestamp for event in events),
            user_agents=user_agents,
            event_types=dict(event_types)
        )
    
    async def get_security_dashboard_data(self, db: Session) -> Dict:
        """Get data for security monitoring dashboard"""
        
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_hour = now - timedelta(hours=1)
        
        # Get recent threat statistics
        total_events_24h = db.query(func.count(AuthEventLog.id)).filter(
            AuthEventLog.timestamp >= last_24h
        ).scalar()
        
        failed_events_24h = db.query(func.count(AuthEventLog.id)).filter(
            and_(
                AuthEventLog.timestamp >= last_24h,
                AuthEventLog.success == False
            )
        ).scalar()
        
        unique_ips_24h = db.query(func.count(func.distinct(AuthEventLog.ip_address))).filter(
            AuthEventLog.timestamp >= last_24h
        ).scalar()
        
        high_risk_events_24h = db.query(func.count(AuthEventLog.id)).filter(
            and_(
                AuthEventLog.timestamp >= last_24h,
                AuthEventLog.risk_score >= 7
            )
        ).scalar()
        
        # Get top suspicious IPs
        suspicious_ips = db.query(
            AuthEventLog.ip_address,
            func.count(AuthEventLog.id).label('event_count'),
            func.sum(AuthEventLog.risk_score).label('total_risk_score')
        ).filter(
            AuthEventLog.timestamp >= last_24h
        ).group_by(
            AuthEventLog.ip_address
        ).having(
            func.sum(AuthEventLog.risk_score) >= 20
        ).order_by(
            func.sum(AuthEventLog.risk_score).desc()
        ).limit(10).all()
        
        return {
            "summary": {
                "total_events_24h": total_events_24h,
                "failed_events_24h": failed_events_24h,
                "unique_ips_24h": unique_ips_24h,
                "high_risk_events_24h": high_risk_events_24h,
                "success_rate_24h": ((total_events_24h - failed_events_24h) / total_events_24h * 100) if total_events_24h > 0 else 100
            },
            "suspicious_ips": [
                {
                    "ip_address": ip.ip_address,
                    "event_count": ip.event_count,
                    "total_risk_score": ip.total_risk_score
                }
                for ip in suspicious_ips
            ],
            "blocked_ips": list(self.blocked_ips),
            "timestamp": now.isoformat()
        }
    
    def block_ip(self, ip_address: str, reason: str) -> None:
        """Block an IP address"""
        self.blocked_ips.add(ip_address)
        self.logger.warning(f"IP address blocked: {ip_address}, reason: {reason}")
    
    def unblock_ip(self, ip_address: str) -> None:
        """Unblock an IP address"""
        self.blocked_ips.discard(ip_address)
        self.logger.info(f"IP address unblocked: {ip_address}")
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if an IP address is blocked"""
        return ip_address in self.blocked_ips

# Global instance
security_monitoring_service = SecurityMonitoringService()