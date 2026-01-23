"""
Authentication Event Logging Service

Handles logging of authentication events for security monitoring and analytics.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base

from ..database import get_db

Base = declarative_base()

class AuthEventType(str, Enum):
    """Authentication event types for logging"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    REGISTER_SUCCESS = "register_success"
    REGISTER_FAILED = "register_failed"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_EXPIRED = "token_expired"
    PASSWORD_CHANGE = "password_change"
    CREDENTIAL_UPDATE = "credential_update"
    ACCOUNT_LOCKED = "account_locked"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

@dataclass
class AuthEvent:
    """Authentication event data structure"""
    event_type: AuthEventType
    user_id: Optional[str]
    email: Optional[str]
    ip_address: str
    user_agent: str
    timestamp: datetime
    success: bool
    details: Dict[str, Any]
    session_id: Optional[str] = None
    risk_score: int = 0

class AuthEventLog(Base):
    """Database model for authentication event logs"""
    __tablename__ = "auth_event_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True)
    user_agent = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    success = Column(Boolean, nullable=False, index=True)
    details = Column(Text, nullable=True)  # JSON string
    session_id = Column(String(255), nullable=True, index=True)
    risk_score = Column(Integer, default=0, index=True)

class AuthLoggingService:
    """Service for logging authentication events"""
    
    def __init__(self):
        self.logger = logging.getLogger("auth_events")
        self.security_logger = logging.getLogger("security")
        
    async def log_auth_event(
        self,
        event_type: AuthEventType,
        ip_address: str,
        user_agent: str,
        success: bool,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        session_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> None:
        """Log an authentication event"""
        
        event = AuthEvent(
            event_type=event_type,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
            success=success,
            details=details or {},
            session_id=session_id,
            risk_score=self._calculate_risk_score(event_type, success, details)
        )
        
        # Log to structured logger
        self._log_to_structured_logger(event)
        
        # Store in database if available
        if db:
            await self._store_in_database(event, db)
        
        # Check for security alerts
        await self._check_security_alerts(event, db)
    
    def _log_to_structured_logger(self, event: AuthEvent) -> None:
        """Log event to structured logger"""
        log_data = {
            "event_type": event.event_type.value,
            "user_id": event.user_id,
            "email": event.email,
            "ip_address": event.ip_address,
            "timestamp": event.timestamp.isoformat(),
            "success": event.success,
            "session_id": event.session_id,
            "risk_score": event.risk_score,
            "details": event.details
        }
        
        if event.success:
            self.logger.info(f"Auth event: {event.event_type.value}", extra=log_data)
        else:
            self.logger.warning(f"Auth failure: {event.event_type.value}", extra=log_data)
            
        # Log high-risk events to security logger
        if event.risk_score >= 7:
            self.security_logger.critical(f"High-risk auth event: {event.event_type.value}", extra=log_data)
        elif event.risk_score >= 5:
            self.security_logger.warning(f"Medium-risk auth event: {event.event_type.value}", extra=log_data)
    
    async def _store_in_database(self, event: AuthEvent, db: Session) -> None:
        """Store event in database"""
        try:
            db_event = AuthEventLog(
                event_type=event.event_type.value,
                user_id=event.user_id,
                email=event.email,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                timestamp=event.timestamp,
                success=event.success,
                details=json.dumps(event.details) if event.details else None,
                session_id=event.session_id,
                risk_score=event.risk_score
            )
            
            db.add(db_event)
            db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to store auth event in database: {e}")
            db.rollback()
    
    def _calculate_risk_score(
        self,
        event_type: AuthEventType,
        success: bool,
        details: Optional[Dict[str, Any]]
    ) -> int:
        """Calculate risk score for the event (0-10 scale)"""
        score = 0
        
        # Base scores by event type
        risk_scores = {
            AuthEventType.LOGIN_FAILED: 3,
            AuthEventType.REGISTER_FAILED: 2,
            AuthEventType.ACCOUNT_LOCKED: 8,
            AuthEventType.SUSPICIOUS_ACTIVITY: 9,
            AuthEventType.RATE_LIMIT_EXCEEDED: 6,
            AuthEventType.TOKEN_EXPIRED: 1,
            AuthEventType.LOGIN_SUCCESS: 0,
            AuthEventType.REGISTER_SUCCESS: 1,
            AuthEventType.LOGOUT: 0,
            AuthEventType.TOKEN_REFRESH: 0,
            AuthEventType.PASSWORD_CHANGE: 2,
            AuthEventType.CREDENTIAL_UPDATE: 2,
        }
        
        score = risk_scores.get(event_type, 0)
        
        # Increase score for failures
        if not success:
            score += 2
        
        # Check details for additional risk factors
        if details:
            if details.get("multiple_failures"):
                score += 3
            if details.get("unusual_location"):
                score += 2
            if details.get("unusual_user_agent"):
                score += 1
            if details.get("brute_force_detected"):
                score += 4
        
        return min(score, 10)  # Cap at 10
    
    async def _check_security_alerts(self, event: AuthEvent, db: Optional[Session]) -> None:
        """Check if event should trigger security alerts"""
        
        # High-risk events trigger immediate alerts
        if event.risk_score >= 8:
            await self._send_security_alert(event, "HIGH_RISK_AUTH_EVENT")
        
        # Check for patterns that indicate attacks
        if db and event.ip_address:
            await self._check_for_attack_patterns(event, db)
    
    async def _send_security_alert(self, event: AuthEvent, alert_type: str) -> None:
        """Send security alert (implement based on your alerting system)"""
        alert_data = {
            "alert_type": alert_type,
            "event": asdict(event),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log critical security alert
        self.security_logger.critical(f"Security alert: {alert_type}", extra=alert_data)
        
        # TODO: Implement actual alerting (email, Slack, PagerDuty, etc.)
        # This could integrate with services like:
        # - Email notifications
        # - Slack webhooks
        # - PagerDuty incidents
        # - SMS alerts
    
    async def _check_for_attack_patterns(self, event: AuthEvent, db: Session) -> None:
        """Check for attack patterns in recent events"""
        try:
            from sqlalchemy import func, and_
            from datetime import timedelta
            
            # Check for multiple failed logins from same IP in last 10 minutes
            recent_time = datetime.utcnow() - timedelta(minutes=10)
            
            failed_attempts = db.query(func.count(AuthEventLog.id)).filter(
                and_(
                    AuthEventLog.ip_address == event.ip_address,
                    AuthEventLog.event_type == AuthEventType.LOGIN_FAILED.value,
                    AuthEventLog.timestamp >= recent_time
                )
            ).scalar()
            
            if failed_attempts >= 5:
                await self._send_security_alert(event, "BRUTE_FORCE_DETECTED")
            
            # Check for multiple failed registrations
            if event.event_type == AuthEventType.REGISTER_FAILED:
                failed_registrations = db.query(func.count(AuthEventLog.id)).filter(
                    and_(
                        AuthEventLog.ip_address == event.ip_address,
                        AuthEventLog.event_type == AuthEventType.REGISTER_FAILED.value,
                        AuthEventLog.timestamp >= recent_time
                    )
                ).scalar()
                
                if failed_registrations >= 3:
                    await self._send_security_alert(event, "REGISTRATION_ABUSE_DETECTED")
        
        except Exception as e:
            self.logger.error(f"Error checking attack patterns: {e}")

# Global instance
auth_logging_service = AuthLoggingService()

# Convenience functions
async def log_login_success(user_id: str, email: str, ip_address: str, user_agent: str, session_id: str, db: Session = None):
    """Log successful login"""
    await auth_logging_service.log_auth_event(
        AuthEventType.LOGIN_SUCCESS, ip_address, user_agent, True,
        user_id=user_id, email=email, session_id=session_id, db=db
    )

async def log_login_failed(email: str, ip_address: str, user_agent: str, reason: str, db: Session = None):
    """Log failed login attempt"""
    await auth_logging_service.log_auth_event(
        AuthEventType.LOGIN_FAILED, ip_address, user_agent, False,
        email=email, details={"reason": reason}, db=db
    )

async def log_registration_success(user_id: str, email: str, ip_address: str, user_agent: str, db: Session = None):
    """Log successful registration"""
    await auth_logging_service.log_auth_event(
        AuthEventType.REGISTER_SUCCESS, ip_address, user_agent, True,
        user_id=user_id, email=email, db=db
    )

async def log_registration_failed(email: str, ip_address: str, user_agent: str, reason: str, db: Session = None):
    """Log failed registration attempt"""
    await auth_logging_service.log_auth_event(
        AuthEventType.REGISTER_FAILED, ip_address, user_agent, False,
        email=email, details={"reason": reason}, db=db
    )

async def log_logout(user_id: str, ip_address: str, user_agent: str, session_id: str, db: Session = None):
    """Log user logout"""
    await auth_logging_service.log_auth_event(
        AuthEventType.LOGOUT, ip_address, user_agent, True,
        user_id=user_id, session_id=session_id, db=db
    )

async def log_rate_limit_exceeded(ip_address: str, user_agent: str, endpoint: str, db: Session = None):
    """Log rate limit exceeded"""
    await auth_logging_service.log_auth_event(
        AuthEventType.RATE_LIMIT_EXCEEDED, ip_address, user_agent, False,
        details={"endpoint": endpoint}, db=db
    )