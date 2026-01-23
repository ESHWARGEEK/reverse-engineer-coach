#!/usr/bin/env python3
"""
Complete Production Deployment Orchestrator
Comprehensive deployment system that handles all aspects of production deployment
including monitoring, user feedback collection, and post-deployment validation
"""

import os
import sys
import json
import time
import subprocess
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import argparse
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/complete-deployment-{datetime.now().strftime("%Y%m%d-%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionDeploymentOrchestrator:
    def __init__(self, config_file: str = "deployment-config.json"):
        self.config = self.load_config(config_file)
        self.deployment_id = f"deploy-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.monitoring_process = None
        self.dashboard_process = None
        self.feedback_collector = None
        self.deployment_success = False
        self.setup_signal_handlers()
        
    def load_config(self, config_file: str) -> Dict:
        """Load deployment configuration"""
        default_config = {
            "environment": "production",
            "version": "latest",
            "domain": "",
            "backup_enabled": True,
            "validation_enabled": True,
            "monitoring_duration_minutes": 60,
            "dashboard_enabled": True,
            "dashboard_port": 5000,
            "feedback_collection_enabled": True,
            "notification_settings": {
                "email_enabled": False,
                "slack_enabled": False,
                "webhook_url": ""
            },
            "rollback_settings": {
                "auto_rollback_on_failure": False,
                "rollback_threshold_error_rate": 10,
                "rollback_threshold_response_time": 5000
            },
            "health_check_settings": {
                "initial_wait_seconds": 60,
                "check_interval_seconds": 30,
                "max_retries": 10
            }
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
        except Exception as e:
            logger.warning(f"Could not load config file {config_file}: {e}")
            
        return default_config
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.cleanup()
        sys.exit(0)
    
    def create_deployment_manifest(self) -> Dict:
        """Create deployment manifest with all deployment details"""
        manifest = {
            "deployment_id": self.deployment_id,
            "timestamp": datetime.now().isoformat(),
            "environment": self.config["environment"],
            "version": self.config["version"],
            "domain": self.config["domain"],
            "config": self.config,
            "phases": {
                "pre_deployment": {"status": "pending", "start_time": None, "end_time": None},
                "deployment": {"status": "pending", "start_time": None, "end_time": None},
                "validation": {"status": "pending", "start_time": None, "end_time": None},
                "monitoring": {"status": "pending", "start_time": None, "end_time": None},
                "post_deployment": {"status": "pending", "start_time": None, "end_time": None}
            },
            "metrics": {
                "deployment_duration_seconds": 0,
                "validation_duration_seconds": 0,
                "monitoring_duration_seconds": 0,
                "total_duration_seconds": 0
            },
            "results": {
                "deployment_success": False,
                "validation_success": False,
                "monitoring_success": False,
                "rollback_performed": False,
                "issues_detected": []
            }
        }
        
        # Save manifest
        os.makedirs("deployments", exist_ok=True)
        with open(f"deployments/{self.deployment_id}-manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return manifest
    
    def update_manifest_phase(self, manifest: Dict, phase: str, status: str, 
                            start_time: Optional[datetime] = None, 
                            end_time: Optional[datetime] = None) -> Dict:
        """Update deployment manifest phase status"""
        if start_time:
            manifest["phases"][phase]["start_time"] = start_time.isoformat()
        if end_time:
            manifest["phases"][phase]["end_time"] = end_time.isoformat()
        manifest["phases"][phase]["status"] = status
        
        # Save updated manifest
        with open(f"deployments/{self.deployment_id}-manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return manifest
    
    def run_command(self, command: List[str], cwd: Optional[str] = None, 
                   timeout: Optional[int] = None) -> Tuple[bool, str, str]:
        """Run a command and return success status, stdout, and stderr"""
        try:
            logger.info(f"Running command: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            success = result.returncode == 0
            
            if not success:
                logger.error(f"Command failed with return code {result.returncode}")
                logger.error(f"STDERR: {result.stderr}")
            
            return success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out after {timeout} seconds")
            return False, "", "Command timed out"
        except Exception as e:
            logger.error(f"Error running command: {e}")
            return False, "", str(e)
    
    def pre_deployment_checks(self, manifest: Dict) -> bool:
        """Perform pre-deployment checks and preparations"""
        logger.info("=== Starting Pre-Deployment Phase ===")
        start_time = datetime.now()
        self.update_manifest_phase(manifest, "pre_deployment", "in_progress", start_time)
        
        try:
            # Check prerequisites
            logger.info("Checking deployment prerequisites...")
            
            # Check Docker
            success, stdout, stderr = self.run_command(["docker", "--version"])
            if not success:
                raise Exception("Docker is not available")
            
            # Check Docker Compose
            success, stdout, stderr = self.run_command(["docker-compose", "--version"])
            if not success:
                raise Exception("Docker Compose is not available")
            
            # Check environment file
            env_file = f".env.{self.config['environment']}"
            if not os.path.exists(env_file):
                raise Exception(f"Environment file not found: {env_file}")
            
            # Create necessary directories
            os.makedirs("logs", exist_ok=True)
            os.makedirs("backups", exist_ok=True)
            os.makedirs("reports", exist_ok=True)
            
            logger.info("✓ Pre-deployment checks completed successfully")
            
            end_time = datetime.now()
            self.update_manifest_phase(manifest, "pre_deployment", "completed", end_time=end_time)
            return True
            
        except Exception as e:
            logger.error(f"Pre-deployment checks failed: {e}")
            end_time = datetime.now()
            self.update_manifest_phase(manifest, "pre_deployment", "failed", end_time=end_time)
            manifest["results"]["issues_detected"].append(f"Pre-deployment: {str(e)}")
            return False
    
    def perform_deployment(self, manifest: Dict) -> bool:
        """Perform the actual deployment"""
        logger.info("=== Starting Deployment Phase ===")
        start_time = datetime.now()
        self.update_manifest_phase(manifest, "deployment", "in_progress", start_time)
        
        try:
            # Determine deployment script based on platform
            if os.name == 'nt':  # Windows
                script_path = "scripts/production-deployment.ps1"
                command = [
                    "powershell", "-ExecutionPolicy", "Bypass", "-File", script_path,
                    "-Environment", self.config["environment"],
                    "-Version", self.config["version"]
                ]
                
                if self.config["domain"]:
                    command.extend(["-Domain", self.config["domain"]])
                if not self.config["backup_enabled"]:
                    command.append("-SkipBackup")
                if not self.config["validation_enabled"]:
                    command.append("-SkipValidation")
                    
            else:  # Unix-like systems
                script_path = "scripts/production-deployment.sh"
                command = [script_path, self.config["environment"], self.config["version"]]
                
                if self.config["domain"]:
                    command.append(self.config["domain"])
                
                # Set environment variables for Unix script
                env = os.environ.copy()
                if not self.config["backup_enabled"]:
                    env["SKIP_BACKUP"] = "true"
                if not self.config["validation_enabled"]:
                    env["SKIP_VALIDATION"] = "true"
            
            # Run deployment script
            logger.info(f"Executing deployment script: {script_path}")
            success, stdout, stderr = self.run_command(command, timeout=1800)  # 30 minute timeout
            
            if success:
                logger.info("✓ Deployment completed successfully")
                self.deployment_success = True
                end_time = datetime.now()
                self.update_manifest_phase(manifest, "deployment", "completed", end_time=end_time)
                manifest["results"]["deployment_success"] = True
                return True
            else:
                raise Exception(f"Deployment script failed: {stderr}")
                
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            end_time = datetime.now()
            self.update_manifest_phase(manifest, "deployment", "failed", end_time=end_time)
            manifest["results"]["issues_detected"].append(f"Deployment: {str(e)}")
            return False
    
    def perform_validation(self, manifest: Dict) -> bool:
        """Perform post-deployment validation"""
        logger.info("=== Starting Validation Phase ===")
        start_time = datetime.now()
        self.update_manifest_phase(manifest, "validation", "in_progress", start_time)
        
        try:
            # Wait for services to stabilize
            wait_time = self.config["health_check_settings"]["initial_wait_seconds"]
            logger.info(f"Waiting {wait_time} seconds for services to stabilize...")
            time.sleep(wait_time)
            
            # Run health checks
            if os.name == 'nt':  # Windows
                script_path = "scripts/health-checks.ps1"
                command = ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path]
            else:  # Unix-like systems
                script_path = "scripts/health-checks.sh"
                command = [script_path]
            
            # Set API URLs based on domain
            env = os.environ.copy()
            if self.config["domain"]:
                env["API_BASE_URL"] = f"https://{self.config['domain']}"
                env["FRONTEND_URL"] = f"https://{self.config['domain']}"
            else:
                env["API_BASE_URL"] = "http://localhost:8000"
                env["FRONTEND_URL"] = "http://localhost"
            
            success, stdout, stderr = self.run_command(command, timeout=300)  # 5 minute timeout
            
            if success:
                logger.info("✓ Validation completed successfully")
                end_time = datetime.now()
                self.update_manifest_phase(manifest, "validation", "completed", end_time=end_time)
                manifest["results"]["validation_success"] = True
                return True
            else:
                raise Exception(f"Validation failed: {stderr}")
                
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            end_time = datetime.now()
            self.update_manifest_phase(manifest, "validation", "failed", end_time=end_time)
            manifest["results"]["issues_detected"].append(f"Validation: {str(e)}")
            return False
    
    def start_monitoring(self, manifest: Dict) -> bool:
        """Start post-deployment monitoring"""
        logger.info("=== Starting Monitoring Phase ===")
        start_time = datetime.now()
        self.update_manifest_phase(manifest, "monitoring", "in_progress", start_time)
        
        try:
            # Start monitoring process
            monitoring_duration = self.config["monitoring_duration_minutes"]
            
            monitoring_command = [
                sys.executable, "scripts/deployment-monitoring.py",
                "--action", "monitor",
                "--duration", str(monitoring_duration)
            ]
            
            logger.info(f"Starting monitoring for {monitoring_duration} minutes...")
            self.monitoring_process = subprocess.Popen(
                monitoring_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Start dashboard if enabled
            if self.config["dashboard_enabled"]:
                dashboard_command = [
                    sys.executable, "scripts/deployment-status-dashboard.py",
                    "--host", "0.0.0.0",
                    "--port", str(self.config["dashboard_port"])
                ]
                
                logger.info(f"Starting dashboard on port {self.config['dashboard_port']}...")
                self.dashboard_process = subprocess.Popen(
                    dashboard_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                logger.info(f"Dashboard available at: http://localhost:{self.config['dashboard_port']}")
            
            # Wait for monitoring to complete
            stdout, stderr = self.monitoring_process.communicate()
            monitoring_success = self.monitoring_process.returncode == 0
            
            if monitoring_success:
                logger.info("✓ Monitoring completed successfully")
                end_time = datetime.now()
                self.update_manifest_phase(manifest, "monitoring", "completed", end_time=end_time)
                manifest["results"]["monitoring_success"] = True
                return True
            else:
                raise Exception(f"Monitoring failed: {stderr}")
                
        except Exception as e:
            logger.error(f"Monitoring failed: {e}")
            end_time = datetime.now()
            self.update_manifest_phase(manifest, "monitoring", "failed", end_time=end_time)
            manifest["results"]["issues_detected"].append(f"Monitoring: {str(e)}")
            return False
    
    def start_feedback_collection(self):
        """Start user feedback collection system"""
        if not self.config["feedback_collection_enabled"]:
            return
        
        try:
            logger.info("Starting user feedback collection system...")
            
            # Import and initialize feedback collector
            sys.path.append("scripts")
            from collect_user_feedback import FeedbackCollector
            
            self.feedback_collector = FeedbackCollector()
            logger.info("✓ Feedback collection system started")
            
        except Exception as e:
            logger.error(f"Failed to start feedback collection: {e}")
    
    def generate_deployment_report(self, manifest: Dict) -> str:
        """Generate comprehensive deployment report"""
        try:
            # Calculate durations
            total_start = datetime.fromisoformat(manifest["phases"]["pre_deployment"]["start_time"])
            total_end = datetime.now()
            total_duration = (total_end - total_start).total_seconds()
            
            # Update manifest with final metrics
            manifest["metrics"]["total_duration_seconds"] = total_duration
            
            # Generate report
            report = f"""
# Production Deployment Report
**Deployment ID:** {self.deployment_id}
**Environment:** {self.config['environment']}
**Version:** {self.config['version']}
**Domain:** {self.config['domain'] or 'localhost'}
**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Deployment Summary
- **Overall Status:** {'✅ SUCCESS' if self.deployment_success else '❌ FAILED'}
- **Total Duration:** {total_duration/60:.1f} minutes
- **Phases Completed:** {sum(1 for phase in manifest['phases'].values() if phase['status'] == 'completed')}/5

## Phase Results
"""
            
            for phase_name, phase_data in manifest["phases"].items():
                status_icon = "✅" if phase_data["status"] == "completed" else "❌" if phase_data["status"] == "failed" else "⏳"
                report += f"- **{phase_name.replace('_', ' ').title()}:** {status_icon} {phase_data['status']}\n"
            
            if manifest["results"]["issues_detected"]:
                report += "\n## Issues Detected\n"
                for issue in manifest["results"]["issues_detected"]:
                    report += f"- {issue}\n"
            
            # Add monitoring results if available
            if os.path.exists("monitoring.db"):
                try:
                    monitoring_command = [
                        sys.executable, "scripts/deployment-monitoring.py",
                        "--action", "report",
                        "--hours", "1"
                    ]
                    success, monitoring_report, _ = self.run_command(monitoring_command)
                    if success:
                        report += f"\n## Monitoring Results\n{monitoring_report}"
                except Exception as e:
                    logger.error(f"Error getting monitoring report: {e}")
            
            # Add user feedback summary if available
            if self.feedback_collector:
                try:
                    feedback_summary = self.feedback_collector.get_feedback_summary(1)  # Last 1 day
                    if feedback_summary.get('total_feedback', 0) > 0:
                        report += f"""
## User Feedback Summary (Last 24 Hours)
- **Total Feedback:** {feedback_summary.get('total_feedback', 0)}
- **Average Rating:** {feedback_summary.get('average_rating', 0)}/5
- **Bug Reports:** {feedback_summary.get('bug_reports', 0)}
- **Feature Requests:** {feedback_summary.get('feature_requests', 0)}
"""
                except Exception as e:
                    logger.error(f"Error getting feedback summary: {e}")
            
            report += f"""

## Next Steps
{'- Monitor system performance and user adoption' if self.deployment_success else '- Investigate deployment issues and consider rollback'}
- Review monitoring dashboard: http://localhost:{self.config['dashboard_port']}
- Check application logs for any issues
- Collect user feedback for continuous improvement

## Files Generated
- Deployment manifest: deployments/{self.deployment_id}-manifest.json
- Deployment logs: logs/complete-deployment-*.log
- Monitoring data: monitoring.db
"""
            
            # Save report
            report_file = f"reports/deployment-report-{self.deployment_id}.md"
            with open(report_file, 'w') as f:
                f.write(report)
            
            logger.info(f"Deployment report saved: {report_file}")
            return report
            
        except Exception as e:
            logger.error(f"Error generating deployment report: {e}")
            return "Error generating deployment report"
    
    def send_deployment_notification(self, success: bool, report: str):
        """Send deployment completion notification"""
        try:
            if not self.config["notification_settings"].get("email_enabled") and \
               not self.config["notification_settings"].get("slack_enabled"):
                return
            
            status = "SUCCESS" if success else "FAILED"
            emoji = "🎉" if success else "❌"
            
            message = f"{emoji} Production Deployment {status}\n\n"
            message += f"Environment: {self.config['environment']}\n"
            message += f"Version: {self.config['version']}\n"
            message += f"Deployment ID: {self.deployment_id}\n\n"
            message += "See full report for details."
            
            # Send notifications (implementation would depend on specific services)
            logger.info(f"Deployment notification: {message}")
            
        except Exception as e:
            logger.error(f"Error sending deployment notification: {e}")
    
    def cleanup(self):
        """Cleanup resources and processes"""
        logger.info("Cleaning up deployment resources...")
        
        try:
            # Stop monitoring process
            if self.monitoring_process and self.monitoring_process.poll() is None:
                self.monitoring_process.terminate()
                self.monitoring_process.wait(timeout=10)
                logger.info("✓ Monitoring process stopped")
        except Exception as e:
            logger.error(f"Error stopping monitoring process: {e}")
        
        try:
            # Stop dashboard process
            if self.dashboard_process and self.dashboard_process.poll() is None:
                self.dashboard_process.terminate()
                self.dashboard_process.wait(timeout=10)
                logger.info("✓ Dashboard process stopped")
        except Exception as e:
            logger.error(f"Error stopping dashboard process: {e}")
    
    def deploy(self) -> bool:
        """Execute complete deployment process"""
        logger.info(f"🚀 Starting Complete Production Deployment - ID: {self.deployment_id}")
        
        # Create deployment manifest
        manifest = self.create_deployment_manifest()
        
        try:
            # Phase 1: Pre-deployment checks
            if not self.pre_deployment_checks(manifest):
                return False
            
            # Phase 2: Deployment
            if not self.perform_deployment(manifest):
                return False
            
            # Phase 3: Validation
            if not self.perform_validation(manifest):
                return False
            
            # Phase 4: Start feedback collection
            self.start_feedback_collection()
            
            # Phase 5: Monitoring
            if not self.start_monitoring(manifest):
                logger.warning("Monitoring failed, but deployment will continue")
            
            # Generate final report
            report = self.generate_deployment_report(manifest)
            
            # Send notifications
            self.send_deployment_notification(True, report)
            
            logger.info("🎉 Complete production deployment finished successfully!")
            logger.info(f"Dashboard: http://localhost:{self.config['dashboard_port']}")
            logger.info(f"Report: reports/deployment-report-{self.deployment_id}.md")
            
            return True
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            
            # Generate failure report
            report = self.generate_deployment_report(manifest)
            self.send_deployment_notification(False, report)
            
            return False
        
        finally:
            # Keep dashboard running but cleanup monitoring
            if self.monitoring_process:
                try:
                    self.monitoring_process.terminate()
                except:
                    pass

def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='Complete Production Deployment Orchestrator')
    parser.add_argument('--config', type=str, default='deployment-config.json',
                       help='Configuration file path')
    parser.add_argument('--environment', type=str, default='production',
                       help='Deployment environment')
    parser.add_argument('--version', type=str, default='latest',
                       help='Version to deploy')
    parser.add_argument('--domain', type=str, default='',
                       help='Domain name for the deployment')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip backup creation')
    parser.add_argument('--no-validation', action='store_true',
                       help='Skip post-deployment validation')
    parser.add_argument('--no-monitoring', action='store_true',
                       help='Skip post-deployment monitoring')
    parser.add_argument('--no-dashboard', action='store_true',
                       help='Skip dashboard startup')
    parser.add_argument('--monitoring-duration', type=int, default=60,
                       help='Monitoring duration in minutes')
    parser.add_argument('--dashboard-port', type=int, default=5000,
                       help='Dashboard port')
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = ProductionDeploymentOrchestrator(args.config)
    
    # Override config with command line arguments
    orchestrator.config.update({
        'environment': args.environment,
        'version': args.version,
        'domain': args.domain,
        'backup_enabled': not args.no_backup,
        'validation_enabled': not args.no_validation,
        'monitoring_duration_minutes': args.monitoring_duration,
        'dashboard_enabled': not args.no_dashboard,
        'dashboard_port': args.dashboard_port
    })
    
    # Execute deployment
    success = orchestrator.deploy()
    
    if success:
        logger.info("Deployment completed successfully. Dashboard will continue running.")
        logger.info("Press Ctrl+C to stop the dashboard and exit.")
        
        # Keep the main process alive to maintain dashboard
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            orchestrator.cleanup()
    else:
        logger.error("Deployment failed. Check logs for details.")
        orchestrator.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()