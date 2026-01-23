#!/usr/bin/env python3
"""
User Feedback Collection System
Collects and analyzes user feedback for continuous improvement
"""

import json
import sqlite3
import smtplib
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/feedback-collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FeedbackCollector:
    def __init__(self, db_path: str = "feedback.db"):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """Initialize the feedback database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create feedback table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                email TEXT,
                feedback_type TEXT,
                rating INTEGER,
                subject TEXT,
                message TEXT,
                feature_request TEXT,
                bug_report TEXT,
                user_agent TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'new',
                priority TEXT DEFAULT 'medium',
                assigned_to TEXT,
                resolved_at TIMESTAMP,
                resolution_notes TEXT
            )
        ''')
        
        # Create user analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                session_id TEXT,
                event_type TEXT,
                event_data TEXT,
                page_url TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create system metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT,
                metric_value REAL,
                metric_unit TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def collect_feedback(self, feedback_data: Dict) -> bool:
        """Store user feedback in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO feedback (
                    user_id, email, feedback_type, rating, subject, message,
                    feature_request, bug_report, user_agent, ip_address
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                feedback_data.get('user_id'),
                feedback_data.get('email'),
                feedback_data.get('feedback_type'),
                feedback_data.get('rating'),
                feedback_data.get('subject'),
                feedback_data.get('message'),
                feedback_data.get('feature_request'),
                feedback_data.get('bug_report'),
                feedback_data.get('user_agent'),
                feedback_data.get('ip_address')
            ))
            
            feedback_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Feedback collected successfully: ID {feedback_id}")
            
            # Send notification for high-priority feedback
            if feedback_data.get('feedback_type') == 'bug_report' or feedback_data.get('rating', 0) <= 2:
                self.send_priority_notification(feedback_id, feedback_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error collecting feedback: {str(e)}")
            return False
    
    def collect_user_analytics(self, analytics_data: Dict) -> bool:
        """Store user analytics data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_analytics (
                    user_id, session_id, event_type, event_data, page_url
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                analytics_data.get('user_id'),
                analytics_data.get('session_id'),
                analytics_data.get('event_type'),
                json.dumps(analytics_data.get('event_data', {})),
                analytics_data.get('page_url')
            ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error collecting analytics: {str(e)}")
            return False
    
    def collect_system_metrics(self, metric_name: str, metric_value: float, metric_unit: str = "") -> bool:
        """Store system performance metrics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_metrics (metric_name, metric_value, metric_unit)
                VALUES (?, ?, ?)
            ''', (metric_name, metric_value, metric_unit))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {str(e)}")
            return False
    
    def get_feedback_summary(self, days: int = 7) -> Dict:
        """Generate feedback summary for the last N days"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_date = datetime.now() - timedelta(days=days)
            
            # Overall feedback stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_feedback,
                    AVG(rating) as avg_rating,
                    COUNT(CASE WHEN feedback_type = 'bug_report' THEN 1 END) as bug_reports,
                    COUNT(CASE WHEN feedback_type = 'feature_request' THEN 1 END) as feature_requests,
                    COUNT(CASE WHEN feedback_type = 'general' THEN 1 END) as general_feedback
                FROM feedback 
                WHERE created_at >= ?
            ''', (since_date,))
            
            stats = cursor.fetchone()
            
            # Rating distribution
            cursor.execute('''
                SELECT rating, COUNT(*) as count
                FROM feedback 
                WHERE created_at >= ? AND rating IS NOT NULL
                GROUP BY rating
                ORDER BY rating
            ''', (since_date,))
            
            rating_distribution = dict(cursor.fetchall())
            
            # Recent feedback
            cursor.execute('''
                SELECT id, email, feedback_type, rating, subject, created_at
                FROM feedback 
                WHERE created_at >= ?
                ORDER BY created_at DESC
                LIMIT 10
            ''', (since_date,))
            
            recent_feedback = [
                {
                    'id': row[0],
                    'email': row[1],
                    'type': row[2],
                    'rating': row[3],
                    'subject': row[4],
                    'created_at': row[5]
                }
                for row in cursor.fetchall()
            ]
            
            conn.close()
            
            return {
                'period_days': days,
                'total_feedback': stats[0] or 0,
                'average_rating': round(stats[1] or 0, 2),
                'bug_reports': stats[2] or 0,
                'feature_requests': stats[3] or 0,
                'general_feedback': stats[4] or 0,
                'rating_distribution': rating_distribution,
                'recent_feedback': recent_feedback
            }
            
        except Exception as e:
            logger.error(f"Error generating feedback summary: {str(e)}")
            return {}
    
    def get_user_analytics_summary(self, days: int = 7) -> Dict:
        """Generate user analytics summary"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_date = datetime.now() - timedelta(days=days)
            
            # User activity stats
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT user_id) as unique_users,
                    COUNT(DISTINCT session_id) as unique_sessions,
                    COUNT(*) as total_events
                FROM user_analytics 
                WHERE timestamp >= ?
            ''', (since_date,))
            
            stats = cursor.fetchone()
            
            # Popular pages
            cursor.execute('''
                SELECT page_url, COUNT(*) as visits
                FROM user_analytics 
                WHERE timestamp >= ? AND page_url IS NOT NULL
                GROUP BY page_url
                ORDER BY visits DESC
                LIMIT 10
            ''', (since_date,))
            
            popular_pages = [{'page': row[0], 'visits': row[1]} for row in cursor.fetchall()]
            
            # Event types
            cursor.execute('''
                SELECT event_type, COUNT(*) as count
                FROM user_analytics 
                WHERE timestamp >= ?
                GROUP BY event_type
                ORDER BY count DESC
            ''', (since_date,))
            
            event_types = [{'event': row[0], 'count': row[1]} for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                'period_days': days,
                'unique_users': stats[0] or 0,
                'unique_sessions': stats[1] or 0,
                'total_events': stats[2] or 0,
                'popular_pages': popular_pages,
                'event_types': event_types
            }
            
        except Exception as e:
            logger.error(f"Error generating analytics summary: {str(e)}")
            return {}
    
    def get_system_metrics_summary(self, days: int = 7) -> Dict:
        """Generate system metrics summary"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_date = datetime.now() - timedelta(days=days)
            
            # Average metrics
            cursor.execute('''
                SELECT 
                    metric_name,
                    AVG(metric_value) as avg_value,
                    MIN(metric_value) as min_value,
                    MAX(metric_value) as max_value,
                    COUNT(*) as sample_count
                FROM system_metrics 
                WHERE timestamp >= ?
                GROUP BY metric_name
                ORDER BY metric_name
            ''', (since_date,))
            
            metrics = [
                {
                    'metric': row[0],
                    'average': round(row[1], 2),
                    'minimum': row[2],
                    'maximum': row[3],
                    'samples': row[4]
                }
                for row in cursor.fetchall()
            ]
            
            conn.close()
            
            return {
                'period_days': days,
                'metrics': metrics
            }
            
        except Exception as e:
            logger.error(f"Error generating metrics summary: {str(e)}")
            return {}
    
    def send_priority_notification(self, feedback_id: int, feedback_data: Dict):
        """Send notification for high-priority feedback"""
        try:
            # Email notification
            if os.getenv('SMTP_HOST') and os.getenv('NOTIFICATION_EMAIL'):
                self.send_email_notification(feedback_id, feedback_data)
            
            # Slack notification
            if os.getenv('SLACK_WEBHOOK_URL'):
                self.send_slack_notification(feedback_id, feedback_data)
                
        except Exception as e:
            logger.error(f"Error sending priority notification: {str(e)}")
    
    def send_email_notification(self, feedback_id: int, feedback_data: Dict):
        """Send email notification for priority feedback"""
        try:
            smtp_host = os.getenv('SMTP_HOST')
            smtp_port = int(os.getenv('SMTP_PORT', 587))
            smtp_user = os.getenv('SMTP_USER')
            smtp_pass = os.getenv('SMTP_PASS')
            notification_email = os.getenv('NOTIFICATION_EMAIL')
            
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = notification_email
            msg['Subject'] = f"Priority Feedback Alert - ID {feedback_id}"
            
            body = f"""
            Priority feedback received:
            
            ID: {feedback_id}
            Type: {feedback_data.get('feedback_type', 'Unknown')}
            Rating: {feedback_data.get('rating', 'N/A')}
            Subject: {feedback_data.get('subject', 'No subject')}
            Email: {feedback_data.get('email', 'Anonymous')}
            
            Message:
            {feedback_data.get('message', 'No message')}
            
            Please review and respond promptly.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email notification sent for feedback ID {feedback_id}")
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
    
    def send_slack_notification(self, feedback_id: int, feedback_data: Dict):
        """Send Slack notification for priority feedback"""
        try:
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
            
            color = "danger" if feedback_data.get('feedback_type') == 'bug_report' else "warning"
            
            payload = {
                "text": f"Priority Feedback Alert - ID {feedback_id}",
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {
                                "title": "Type",
                                "value": feedback_data.get('feedback_type', 'Unknown'),
                                "short": True
                            },
                            {
                                "title": "Rating",
                                "value": str(feedback_data.get('rating', 'N/A')),
                                "short": True
                            },
                            {
                                "title": "Subject",
                                "value": feedback_data.get('subject', 'No subject'),
                                "short": False
                            },
                            {
                                "title": "Message",
                                "value": feedback_data.get('message', 'No message')[:500] + ("..." if len(feedback_data.get('message', '')) > 500 else ""),
                                "short": False
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            
            logger.info(f"Slack notification sent for feedback ID {feedback_id}")
            
        except Exception as e:
            logger.error(f"Error sending Slack notification: {str(e)}")
    
    def generate_weekly_report(self) -> str:
        """Generate comprehensive weekly report"""
        try:
            feedback_summary = self.get_feedback_summary(7)
            analytics_summary = self.get_user_analytics_summary(7)
            metrics_summary = self.get_system_metrics_summary(7)
            
            report = f"""
# Weekly User Feedback and Analytics Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Feedback Summary (Last 7 Days)
- Total Feedback: {feedback_summary.get('total_feedback', 0)}
- Average Rating: {feedback_summary.get('average_rating', 0)}/5
- Bug Reports: {feedback_summary.get('bug_reports', 0)}
- Feature Requests: {feedback_summary.get('feature_requests', 0)}
- General Feedback: {feedback_summary.get('general_feedback', 0)}

### Rating Distribution
"""
            
            for rating, count in feedback_summary.get('rating_distribution', {}).items():
                report += f"- {rating} stars: {count} responses\n"
            
            report += f"""

## User Analytics Summary (Last 7 Days)
- Unique Users: {analytics_summary.get('unique_users', 0)}
- Unique Sessions: {analytics_summary.get('unique_sessions', 0)}
- Total Events: {analytics_summary.get('total_events', 0)}

### Popular Pages
"""
            
            for page in analytics_summary.get('popular_pages', [])[:5]:
                report += f"- {page['page']}: {page['visits']} visits\n"
            
            report += f"""

## System Performance Metrics (Last 7 Days)
"""
            
            for metric in metrics_summary.get('metrics', []):
                report += f"- {metric['metric']}: avg {metric['average']}, min {metric['minimum']}, max {metric['maximum']}\n"
            
            report += f"""

## Recent Feedback Highlights
"""
            
            for feedback in feedback_summary.get('recent_feedback', [])[:5]:
                report += f"- [{feedback['type']}] {feedback['subject']} (Rating: {feedback['rating'] or 'N/A'})\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {str(e)}")
            return "Error generating report"
    
    def export_feedback_data(self, output_file: str, days: int = 30) -> bool:
        """Export feedback data to JSON file"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            since_date = datetime.now() - timedelta(days=days)
            
            cursor.execute('''
                SELECT * FROM feedback 
                WHERE created_at >= ?
                ORDER BY created_at DESC
            ''', (since_date,))
            
            columns = [description[0] for description in cursor.description]
            feedback_data = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            conn.close()
            
            with open(output_file, 'w') as f:
                json.dump(feedback_data, f, indent=2, default=str)
            
            logger.info(f"Feedback data exported to {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting feedback data: {str(e)}")
            return False

def main():
    """Main function for command-line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='User Feedback Collection System')
    parser.add_argument('--action', choices=['report', 'export', 'summary'], default='summary',
                       help='Action to perform')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to include in report/export')
    parser.add_argument('--output', type=str,
                       help='Output file for export action')
    
    args = parser.parse_args()
    
    collector = FeedbackCollector()
    
    if args.action == 'report':
        report = collector.generate_weekly_report()
        print(report)
        
        # Save report to file
        report_file = f"reports/weekly-report-{datetime.now().strftime('%Y%m%d')}.md"
        os.makedirs('reports', exist_ok=True)
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\nReport saved to: {report_file}")
        
    elif args.action == 'export':
        output_file = args.output or f"feedback-export-{datetime.now().strftime('%Y%m%d')}.json"
        if collector.export_feedback_data(output_file, args.days):
            print(f"Feedback data exported to: {output_file}")
        else:
            print("Export failed")
            
    elif args.action == 'summary':
        feedback_summary = collector.get_feedback_summary(args.days)
        analytics_summary = collector.get_user_analytics_summary(args.days)
        
        print(f"=== Feedback Summary (Last {args.days} days) ===")
        print(f"Total Feedback: {feedback_summary.get('total_feedback', 0)}")
        print(f"Average Rating: {feedback_summary.get('average_rating', 0)}")
        print(f"Bug Reports: {feedback_summary.get('bug_reports', 0)}")
        print(f"Feature Requests: {feedback_summary.get('feature_requests', 0)}")
        
        print(f"\n=== User Analytics Summary (Last {args.days} days) ===")
        print(f"Unique Users: {analytics_summary.get('unique_users', 0)}")
        print(f"Unique Sessions: {analytics_summary.get('unique_sessions', 0)}")
        print(f"Total Events: {analytics_summary.get('total_events', 0)}")

if __name__ == "__main__":
    main()