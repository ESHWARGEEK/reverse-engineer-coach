"""
User Analytics Service

Tracks user behavior, engagement metrics, and provides analytics insights.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import Column, String, DateTime, Integer, Text, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import func, and_, or_

Base = declarative_base()

@dataclass
class UserEngagementMetric:
    """User engagement metric data structure"""
    user_id: str
    event_type: str
    event_data: Dict[str, Any]
    timestamp: datetime
    session_id: Optional[str] = None
    ip_address: Optional[str] = None

@dataclass
class UserAnalytics:
    """User analytics summary"""
    user_id: str
    total_sessions: int
    total_projects: int
    avg_session_duration: float
    last_active: datetime
    registration_date: datetime
    discovery_usage_count: int
    coach_interactions: int
    feature_usage: Dict[str, int]

class UserEventLog(Base):
    """Database model for user event logs"""
    __tablename__ = "user_event_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    event_data = Column(Text, nullable=True)  # JSON string
    timestamp = Column(DateTime, nullable=False, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)

class UserSessionLog(Base):
    """Database model for user session logs"""
    __tablename__ = "user_session_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True, index=True)
    duration_seconds = Column(Integer, nullable=True)
    page_views = Column(Integer, default=0)
    actions_count = Column(Integer, default=0)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

class UserAnalyticsService:
    """Service for tracking and analyzing user behavior"""
    
    def __init__(self):
        self.logger = logging.getLogger("user_analytics")
        
        # Event types for tracking
        self.event_types = {
            "USER_REGISTRATION": "user_registration",
            "USER_LOGIN": "user_login",
            "USER_LOGOUT": "user_logout",
            "PROJECT_CREATED": "project_created",
            "PROJECT_OPENED": "project_opened",
            "PROJECT_DELETED": "project_deleted",
            "DISCOVERY_SEARCH": "discovery_search",
            "REPOSITORY_SELECTED": "repository_selected",
            "COACH_INTERACTION": "coach_interaction",
            "WORKSPACE_OPENED": "workspace_opened",
            "CODE_GENERATED": "code_generated",
            "PROFILE_UPDATED": "profile_updated",
            "CREDENTIALS_UPDATED": "credentials_updated",
            "PAGE_VIEW": "page_view",
            "FEATURE_USED": "feature_used",
            "ERROR_ENCOUNTERED": "error_encountered"
        }
    
    async def track_event(
        self,
        user_id: str,
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        db: Optional[Session] = None
    ) -> None:
        """Track a user event"""
        
        metric = UserEngagementMetric(
            user_id=user_id,
            event_type=event_type,
            event_data=event_data or {},
            timestamp=datetime.utcnow(),
            session_id=session_id,
            ip_address=ip_address
        )
        
        # Log the event
        self._log_event(metric)
        
        # Store in database if available
        if db:
            await self._store_event(metric, db)
    
    def _log_event(self, metric: UserEngagementMetric) -> None:
        """Log event to structured logger"""
        log_data = {
            "user_id": metric.user_id,
            "event_type": metric.event_type,
            "event_data": metric.event_data,
            "timestamp": metric.timestamp.isoformat(),
            "session_id": metric.session_id,
            "ip_address": metric.ip_address
        }
        
        self.logger.info(f"User event: {metric.event_type}", extra=log_data)
    
    async def _store_event(self, metric: UserEngagementMetric, db: Session) -> None:
        """Store event in database"""
        try:
            import json
            
            db_event = UserEventLog(
                user_id=metric.user_id,
                event_type=metric.event_type,
                event_data=json.dumps(metric.event_data) if metric.event_data else None,
                timestamp=metric.timestamp,
                session_id=metric.session_id,
                ip_address=metric.ip_address
            )
            
            db.add(db_event)
            db.commit()
            
        except Exception as e:
            self.logger.error(f"Failed to store user event in database: {e}")
            db.rollback()
    
    async def start_session(
        self,
        user_id: str,
        session_id: str,
        ip_address: str,
        user_agent: str,
        db: Session
    ) -> None:
        """Start tracking a user session"""
        try:
            session_log = UserSessionLog(
                user_id=user_id,
                session_id=session_id,
                start_time=datetime.utcnow(),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            db.add(session_log)
            db.commit()
            
            # Track session start event
            await self.track_event(
                user_id=user_id,
                event_type=self.event_types["USER_LOGIN"],
                session_id=session_id,
                ip_address=ip_address,
                db=db
            )
            
        except Exception as e:
            self.logger.error(f"Failed to start session tracking: {e}")
            db.rollback()
    
    async def end_session(self, session_id: str, db: Session) -> None:
        """End tracking a user session"""
        try:
            session_log = db.query(UserSessionLog).filter(
                UserSessionLog.session_id == session_id,
                UserSessionLog.end_time.is_(None)
            ).first()
            
            if session_log:
                end_time = datetime.utcnow()
                duration = (end_time - session_log.start_time).total_seconds()
                
                session_log.end_time = end_time
                session_log.duration_seconds = int(duration)
                
                db.commit()
                
                # Track session end event
                await self.track_event(
                    user_id=session_log.user_id,
                    event_type=self.event_types["USER_LOGOUT"],
                    event_data={"session_duration": duration},
                    session_id=session_id,
                    db=db
                )
            
        except Exception as e:
            self.logger.error(f"Failed to end session tracking: {e}")
            db.rollback()
    
    async def get_user_analytics(self, user_id: str, db: Session) -> UserAnalytics:
        """Get comprehensive analytics for a user"""
        
        # Get user registration date (from users table or first event)
        first_event = db.query(UserEventLog).filter(
            UserEventLog.user_id == user_id
        ).order_by(UserEventLog.timestamp.asc()).first()
        
        registration_date = first_event.timestamp if first_event else datetime.utcnow()
        
        # Get session statistics
        session_stats = db.query(
            func.count(UserSessionLog.id).label('total_sessions'),
            func.avg(UserSessionLog.duration_seconds).label('avg_duration'),
            func.max(UserSessionLog.start_time).label('last_active')
        ).filter(
            UserSessionLog.user_id == user_id
        ).first()
        
        # Get project count
        project_count = db.query(func.count(UserEventLog.id)).filter(
            and_(
                UserEventLog.user_id == user_id,
                UserEventLog.event_type == self.event_types["PROJECT_CREATED"]
            )
        ).scalar()
        
        # Get discovery usage count
        discovery_count = db.query(func.count(UserEventLog.id)).filter(
            and_(
                UserEventLog.user_id == user_id,
                UserEventLog.event_type == self.event_types["DISCOVERY_SEARCH"]
            )
        ).scalar()
        
        # Get coach interactions count
        coach_count = db.query(func.count(UserEventLog.id)).filter(
            and_(
                UserEventLog.user_id == user_id,
                UserEventLog.event_type == self.event_types["COACH_INTERACTION"]
            )
        ).scalar()
        
        # Get feature usage statistics
        feature_usage = {}
        feature_events = db.query(
            UserEventLog.event_type,
            func.count(UserEventLog.id).label('count')
        ).filter(
            UserEventLog.user_id == user_id
        ).group_by(
            UserEventLog.event_type
        ).all()
        
        for event in feature_events:
            feature_usage[event.event_type] = event.count
        
        return UserAnalytics(
            user_id=user_id,
            total_sessions=session_stats.total_sessions if session_stats else 0,
            total_projects=project_count or 0,
            avg_session_duration=session_stats.avg_duration if session_stats and session_stats.avg_duration else 0.0,
            last_active=session_stats.last_active if session_stats and session_stats.last_active else registration_date,
            registration_date=registration_date,
            discovery_usage_count=discovery_count or 0,
            coach_interactions=coach_count or 0,
            feature_usage=feature_usage
        )
    
    async def get_platform_analytics(self, db: Session, days: int = 30) -> Dict[str, Any]:
        """Get platform-wide analytics"""
        
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        
        # Get user registration statistics
        new_users = db.query(func.count(UserEventLog.id)).filter(
            and_(
                UserEventLog.event_type == self.event_types["USER_REGISTRATION"],
                UserEventLog.timestamp >= start_date
            )
        ).scalar()
        
        # Get active users (users with any activity)
        active_users = db.query(func.count(func.distinct(UserEventLog.user_id))).filter(
            UserEventLog.timestamp >= start_date
        ).scalar()
        
        # Get total sessions
        total_sessions = db.query(func.count(UserSessionLog.id)).filter(
            UserSessionLog.start_time >= start_date
        ).scalar()
        
        # Get average session duration
        avg_session_duration = db.query(func.avg(UserSessionLog.duration_seconds)).filter(
            and_(
                UserSessionLog.start_time >= start_date,
                UserSessionLog.duration_seconds.isnot(None)
            )
        ).scalar()
        
        # Get project creation statistics
        projects_created = db.query(func.count(UserEventLog.id)).filter(
            and_(
                UserEventLog.event_type == self.event_types["PROJECT_CREATED"],
                UserEventLog.timestamp >= start_date
            )
        ).scalar()
        
        # Get discovery usage statistics
        discovery_searches = db.query(func.count(UserEventLog.id)).filter(
            and_(
                UserEventLog.event_type == self.event_types["DISCOVERY_SEARCH"],
                UserEventLog.timestamp >= start_date
            )
        ).scalar()
        
        # Get coach interaction statistics
        coach_interactions = db.query(func.count(UserEventLog.id)).filter(
            and_(
                UserEventLog.event_type == self.event_types["COACH_INTERACTION"],
                UserEventLog.timestamp >= start_date
            )
        ).scalar()
        
        # Get most popular features
        popular_features = db.query(
            UserEventLog.event_type,
            func.count(UserEventLog.id).label('usage_count')
        ).filter(
            UserEventLog.timestamp >= start_date
        ).group_by(
            UserEventLog.event_type
        ).order_by(
            func.count(UserEventLog.id).desc()
        ).limit(10).all()
        
        # Get daily active users trend
        daily_active_users = db.query(
            func.date(UserEventLog.timestamp).label('date'),
            func.count(func.distinct(UserEventLog.user_id)).label('active_users')
        ).filter(
            UserEventLog.timestamp >= start_date
        ).group_by(
            func.date(UserEventLog.timestamp)
        ).order_by(
            func.date(UserEventLog.timestamp)
        ).all()
        
        return {
            "period_days": days,
            "summary": {
                "new_users": new_users or 0,
                "active_users": active_users or 0,
                "total_sessions": total_sessions or 0,
                "avg_session_duration_minutes": round((avg_session_duration or 0) / 60, 2),
                "projects_created": projects_created or 0,
                "discovery_searches": discovery_searches or 0,
                "coach_interactions": coach_interactions or 0
            },
            "popular_features": [
                {
                    "feature": feature.event_type,
                    "usage_count": feature.usage_count
                }
                for feature in popular_features
            ],
            "daily_active_users": [
                {
                    "date": str(day.date),
                    "active_users": day.active_users
                }
                for day in daily_active_users
            ],
            "engagement_metrics": {
                "avg_projects_per_user": round((projects_created or 0) / (active_users or 1), 2),
                "avg_sessions_per_user": round((total_sessions or 0) / (active_users or 1), 2),
                "discovery_adoption_rate": round(((discovery_searches or 0) / (active_users or 1)) * 100, 2)
            },
            "timestamp": now.isoformat()
        }
    
    async def get_user_retention_analysis(self, db: Session) -> Dict[str, Any]:
        """Get user retention analysis"""
        
        now = datetime.utcnow()
        
        # Define cohorts by registration week
        cohort_data = []
        
        for weeks_ago in range(12):  # Last 12 weeks
            cohort_start = now - timedelta(weeks=weeks_ago+1)
            cohort_end = now - timedelta(weeks=weeks_ago)
            
            # Get users who registered in this cohort
            cohort_users = db.query(func.distinct(UserEventLog.user_id)).filter(
                and_(
                    UserEventLog.event_type == self.event_types["USER_REGISTRATION"],
                    UserEventLog.timestamp >= cohort_start,
                    UserEventLog.timestamp < cohort_end
                )
            ).subquery()
            
            cohort_size = db.query(func.count()).select_from(cohort_users).scalar()
            
            if cohort_size > 0:
                # Check retention for different periods
                retention_periods = [1, 2, 4, 8]  # weeks
                retention_rates = {}
                
                for period in retention_periods:
                    period_start = cohort_end
                    period_end = cohort_end + timedelta(weeks=period)
                    
                    if period_end <= now:
                        retained_users = db.query(func.count(func.distinct(UserEventLog.user_id))).filter(
                            and_(
                                UserEventLog.user_id.in_(cohort_users),
                                UserEventLog.timestamp >= period_start,
                                UserEventLog.timestamp < period_end
                            )
                        ).scalar()
                        
                        retention_rates[f"week_{period}"] = round((retained_users / cohort_size) * 100, 2)
                
                cohort_data.append({
                    "cohort_week": cohort_start.strftime("%Y-W%U"),
                    "cohort_size": cohort_size,
                    "retention_rates": retention_rates
                })
        
        return {
            "cohort_analysis": cohort_data,
            "timestamp": now.isoformat()
        }

# Global instance
user_analytics_service = UserAnalyticsService()

# Convenience functions for common events
async def track_user_registration(user_id: str, email: str, ip_address: str, db: Session):
    """Track user registration event"""
    await user_analytics_service.track_event(
        user_id=user_id,
        event_type=user_analytics_service.event_types["USER_REGISTRATION"],
        event_data={"email": email},
        ip_address=ip_address,
        db=db
    )

async def track_project_creation(user_id: str, project_id: str, repository_url: str, session_id: str, db: Session):
    """Track project creation event"""
    await user_analytics_service.track_event(
        user_id=user_id,
        event_type=user_analytics_service.event_types["PROJECT_CREATED"],
        event_data={"project_id": project_id, "repository_url": repository_url},
        session_id=session_id,
        db=db
    )

async def track_discovery_search(user_id: str, search_concept: str, results_count: int, session_id: str, db: Session):
    """Track repository discovery search event"""
    await user_analytics_service.track_event(
        user_id=user_id,
        event_type=user_analytics_service.event_types["DISCOVERY_SEARCH"],
        event_data={"search_concept": search_concept, "results_count": results_count},
        session_id=session_id,
        db=db
    )

async def track_coach_interaction(user_id: str, interaction_type: str, session_id: str, db: Session):
    """Track coach interaction event"""
    await user_analytics_service.track_event(
        user_id=user_id,
        event_type=user_analytics_service.event_types["COACH_INTERACTION"],
        event_data={"interaction_type": interaction_type},
        session_id=session_id,
        db=db
    )