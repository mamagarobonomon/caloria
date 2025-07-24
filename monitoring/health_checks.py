"""
Health Check System for Caloria Application
Provides comprehensive health monitoring and status endpoints
"""

import os
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from flask import Blueprint, jsonify, request

from config.constants import StatusCodes
from services.logging_service import caloria_logger
from services.metrics_service import metrics, generate_metrics_report
from services.caching_service import cache, maintain_cache
from services.database_service import DatabaseService
from exceptions import CaloriaException

# Create health check blueprint
health_bp = Blueprint('health', __name__, url_prefix='/health')

class HealthChecker:
    """Comprehensive health checking system"""
    
    def __init__(self, db=None):
        self.db = db
        self.logger = caloria_logger
        self.db_service = DatabaseService(db) if db else None
        
        # Health check thresholds
        self.thresholds = {
            'response_time_ms': 5000,  # 5 seconds
            'error_rate_percent': 5,   # 5% error rate
            'memory_usage_percent': 85, # 85% memory usage
            'disk_usage_percent': 90,  # 90% disk usage
            'cache_hit_rate_percent': 30  # 30% minimum hit rate
        }
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall application health status"""
        start_time = time.time()
        
        try:
            health_checks = {
                'database': self._check_database_health(),
                'external_apis': self._check_external_apis_health(),
                'system_resources': self._check_system_resources(),
                'application_metrics': self._check_application_metrics(),
                'cache_performance': self._check_cache_performance()
            }
            
            # Determine overall status
            overall_status = self._determine_overall_status(health_checks)
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            return {
                'status': overall_status,
                'timestamp': datetime.utcnow().isoformat(),
                'response_time_ms': round(response_time, 2),
                'checks': health_checks,
                'version': self._get_application_version(),
                'uptime_seconds': self._get_uptime_seconds()
            }
            
        except Exception as e:
            self.logger.error("Health check failed", e)
            return {
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
                'checks': {}
            }
    
    def get_readiness_status(self) -> Dict[str, Any]:
        """Check if application is ready to serve requests"""
        try:
            # Essential readiness checks
            db_ready = self._check_database_connectivity()
            config_ready = self._check_configuration()
            
            ready = db_ready and config_ready
            
            return {
                'ready': ready,
                'timestamp': datetime.utcnow().isoformat(),
                'checks': {
                    'database_connectivity': db_ready,
                    'configuration': config_ready
                }
            }
            
        except Exception as e:
            self.logger.error("Readiness check failed", e)
            return {
                'ready': False,
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    def get_liveness_status(self) -> Dict[str, Any]:
        """Check if application is alive and responding"""
        try:
            # Basic liveness checks
            alive = True
            current_time = datetime.utcnow()
            
            return {
                'alive': alive,
                'timestamp': current_time.isoformat(),
                'server_time': current_time.isoformat(),
                'process_id': os.getpid()
            }
            
        except Exception as e:
            self.logger.error("Liveness check failed", e)
            return {
                'alive': False,
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database health and performance"""
        try:
            if not self.db_service:
                return {
                    'status': 'unknown',
                    'message': 'Database service not available'
                }
            
            health_data = self.db_service.get_database_health()
            
            if health_data.get('connectivity') == 'healthy':
                # Check performance metrics
                table_sizes = health_data.get('table_sizes', {})
                total_records = sum(table_sizes.values())
                
                # Determine health status based on performance
                if total_records > 1000000:  # 1M records
                    status = 'degraded'
                    message = 'Large dataset detected, performance may be impacted'
                else:
                    status = 'healthy'
                    message = 'Database operating normally'
                
                return {
                    'status': status,
                    'message': message,
                    'details': health_data
                }
            else:
                return {
                    'status': 'unhealthy',
                    'message': 'Database connectivity issues',
                    'details': health_data
                }
                
        except Exception as e:
            self.logger.error("Database health check failed", e)
            return {
                'status': 'unhealthy',
                'message': f'Database health check failed: {str(e)}'
            }
    
    def _check_external_apis_health(self) -> Dict[str, Any]:
        """Check health of external API dependencies"""
        api_statuses = {}
        
        # Check Spoonacular API
        api_statuses['spoonacular'] = self._check_api_endpoint(
            'https://api.spoonacular.com/food/ingredients/search',
            {'query': 'apple', 'number': 1},
            headers={'X-RapidAPI-Key': os.getenv('SPOONACULAR_API_KEY', 'test')},
            timeout=5
        )
        
        # Check Google Cloud APIs (simplified)
        try:
            from google.cloud import vision
            api_statuses['google_cloud'] = {
                'status': 'healthy',
                'message': 'Google Cloud client available'
            }
        except Exception:
            api_statuses['google_cloud'] = {
                'status': 'degraded',
                'message': 'Google Cloud client not properly configured'
            }
        
        # Determine overall API health
        healthy_apis = sum(1 for api in api_statuses.values() if api['status'] == 'healthy')
        total_apis = len(api_statuses)
        
        if healthy_apis == total_apis:
            overall_status = 'healthy'
            message = 'All external APIs are healthy'
        elif healthy_apis > 0:
            overall_status = 'degraded'
            message = f'{healthy_apis}/{total_apis} APIs are healthy'
        else:
            overall_status = 'unhealthy'
            message = 'All external APIs are unhealthy'
        
        return {
            'status': overall_status,
            'message': message,
            'apis': api_statuses
        }
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Determine status based on thresholds
            issues = []
            if memory_percent > self.thresholds['memory_usage_percent']:
                issues.append(f'High memory usage: {memory_percent:.1f}%')
            if disk_percent > self.thresholds['disk_usage_percent']:
                issues.append(f'High disk usage: {disk_percent:.1f}%')
            if cpu_percent > 90:  # High CPU threshold
                issues.append(f'High CPU usage: {cpu_percent:.1f}%')
            
            if issues:
                status = 'degraded'
                message = '; '.join(issues)
            else:
                status = 'healthy'
                message = 'System resources within normal limits'
            
            return {
                'status': status,
                'message': message,
                'metrics': {
                    'cpu_percent': round(cpu_percent, 1),
                    'memory_percent': round(memory_percent, 1),
                    'disk_percent': round(disk_percent, 1),
                    'memory_available_gb': round(memory.available / (1024**3), 2),
                    'disk_free_gb': round(disk.free / (1024**3), 2)
                }
            }
            
        except ImportError:
            return {
                'status': 'unknown',
                'message': 'psutil not available for system monitoring'
            }
        except Exception as e:
            self.logger.error("System resource check failed", e)
            return {
                'status': 'unknown',
                'message': f'System resource check failed: {str(e)}'
            }
    
    def _check_application_metrics(self) -> Dict[str, Any]:
        """Check application performance metrics"""
        try:
            health_metrics = metrics.get_health_metrics()
            
            status = health_metrics['status']
            issues = health_metrics.get('issues', [])
            
            return {
                'status': status,
                'message': '; '.join(issues) if issues else 'Application metrics are healthy',
                'metrics': health_metrics['metrics']
            }
            
        except Exception as e:
            self.logger.error("Application metrics check failed", e)
            return {
                'status': 'unknown',
                'message': f'Metrics check failed: {str(e)}'
            }
    
    def _check_cache_performance(self) -> Dict[str, Any]:
        """Check cache performance and health"""
        try:
            cache_stats = cache.get_stats()
            
            hit_rate = cache_stats.get('hit_rate_percent', 0)
            valid_entries = cache_stats.get('valid_entries', 0)
            
            if hit_rate < self.thresholds['cache_hit_rate_percent']:
                status = 'degraded'
                message = f'Low cache hit rate: {hit_rate}%'
            elif valid_entries == 0:
                status = 'degraded'
                message = 'Cache is empty'
            else:
                status = 'healthy'
                message = 'Cache performance is good'
            
            return {
                'status': status,
                'message': message,
                'metrics': cache_stats
            }
            
        except Exception as e:
            self.logger.error("Cache performance check failed", e)
            return {
                'status': 'unknown',
                'message': f'Cache check failed: {str(e)}'
            }
    
    def _check_database_connectivity(self) -> bool:
        """Check basic database connectivity"""
        try:
            if not self.db:
                return False
            
            # Simple connectivity test
            from sqlalchemy import text
            with self.db.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            return True
            
        except Exception as e:
            self.logger.error("Database connectivity check failed", e)
            return False
    
    def _check_configuration(self) -> bool:
        """Check essential configuration"""
        try:
            required_env_vars = [
                'SECRET_KEY',
                'SPOONACULAR_API_KEY',
                'MANYCHAT_API_TOKEN'
            ]
            
            for var in required_env_vars:
                if not os.getenv(var):
                    self.logger.warning(f"Missing required environment variable: {var}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error("Configuration check failed", e)
            return False
    
    def _check_api_endpoint(self, url: str, params: Dict = None, 
                           headers: Dict = None, timeout: int = 5) -> Dict[str, Any]:
        """Check health of an external API endpoint"""
        try:
            start_time = time.time()
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response_time = (time.time() - start_time) * 1000
            
            if 200 <= response.status_code < 300:
                status = 'healthy'
                message = f'API responding normally ({response.status_code})'
            elif 400 <= response.status_code < 500:
                status = 'degraded'
                message = f'API client error ({response.status_code})'
            else:
                status = 'unhealthy'
                message = f'API server error ({response.status_code})'
            
            return {
                'status': status,
                'message': message,
                'response_time_ms': round(response_time, 2),
                'status_code': response.status_code
            }
            
        except requests.Timeout:
            return {
                'status': 'unhealthy',
                'message': 'API request timed out'
            }
        except requests.ConnectionError:
            return {
                'status': 'unhealthy',
                'message': 'Cannot connect to API'
            }
        except Exception as e:
            return {
                'status': 'unknown',
                'message': f'API check failed: {str(e)}'
            }
    
    def _determine_overall_status(self, health_checks: Dict[str, Any]) -> str:
        """Determine overall application health status"""
        statuses = []
        for check in health_checks.values():
            if isinstance(check, dict) and 'status' in check:
                statuses.append(check['status'])
        
        if 'unhealthy' in statuses:
            return 'unhealthy'
        elif 'degraded' in statuses:
            return 'degraded'
        elif 'healthy' in statuses:
            return 'healthy'
        else:
            return 'unknown'
    
    def _get_application_version(self) -> str:
        """Get application version"""
        try:
            # Try to read version from file or environment
            version = os.getenv('APP_VERSION', '1.0.0')
            return version
        except Exception:
            return 'unknown'
    
    def _get_uptime_seconds(self) -> float:
        """Get application uptime in seconds"""
        try:
            uptime = (datetime.utcnow() - metrics.startup_time).total_seconds()
            return round(uptime, 2)
        except Exception:
            return 0.0

# Initialize health checker
health_checker = HealthChecker()

# Health check routes
@health_bp.route('/')
def health_overview():
    """Overall health status endpoint"""
    health_status = health_checker.get_overall_health()
    
    # Set appropriate HTTP status code
    if health_status['status'] == 'healthy':
        status_code = StatusCodes.OK
    elif health_status['status'] == 'degraded':
        status_code = StatusCodes.OK  # Still serving requests
    else:
        status_code = StatusCodes.SERVICE_UNAVAILABLE
    
    return jsonify(health_status), status_code

@health_bp.route('/ready')
def readiness_probe():
    """Kubernetes readiness probe endpoint"""
    readiness_status = health_checker.get_readiness_status()
    
    status_code = StatusCodes.OK if readiness_status['ready'] else StatusCodes.SERVICE_UNAVAILABLE
    
    return jsonify(readiness_status), status_code

@health_bp.route('/live')
def liveness_probe():
    """Kubernetes liveness probe endpoint"""
    liveness_status = health_checker.get_liveness_status()
    
    status_code = StatusCodes.OK if liveness_status['alive'] else StatusCodes.SERVICE_UNAVAILABLE
    
    return jsonify(liveness_status), status_code

@health_bp.route('/metrics')
def metrics_endpoint():
    """Application metrics endpoint"""
    try:
        metrics_report = generate_metrics_report()
        return jsonify(metrics_report), StatusCodes.OK
    except Exception as e:
        caloria_logger.error("Metrics endpoint failed", e)
        return jsonify({
            'error': 'Metrics collection failed',
            'message': str(e)
        }), StatusCodes.INTERNAL_ERROR

@health_bp.route('/database')
def database_health():
    """Detailed database health endpoint"""
    try:
        db_health = health_checker._check_database_health()
        
        if db_health['status'] == 'healthy':
            status_code = StatusCodes.OK
        elif db_health['status'] == 'degraded':
            status_code = StatusCodes.OK
        else:
            status_code = StatusCodes.SERVICE_UNAVAILABLE
        
        return jsonify(db_health), status_code
    except Exception as e:
        caloria_logger.error("Database health check failed", e)
        return jsonify({
            'status': 'unhealthy',
            'message': str(e)
        }), StatusCodes.INTERNAL_ERROR

@health_bp.route('/cache')
def cache_health():
    """Cache health and maintenance endpoint"""
    try:
        # Perform cache maintenance
        maintenance_result = maintain_cache()
        
        # Get cache health
        cache_health = health_checker._check_cache_performance()
        
        response = {
            'cache_health': cache_health,
            'maintenance': maintenance_result
        }
        
        return jsonify(response), StatusCodes.OK
    except Exception as e:
        caloria_logger.error("Cache health check failed", e)
        return jsonify({
            'status': 'unhealthy',
            'message': str(e)
        }), StatusCodes.INTERNAL_ERROR

@health_bp.route('/version')
def version_info():
    """Application version information"""
    try:
        version_data = {
            'version': health_checker._get_application_version(),
            'build_time': os.getenv('BUILD_TIME', 'unknown'),
            'git_commit': os.getenv('GIT_COMMIT', 'unknown'),
            'environment': os.getenv('FLASK_ENV', 'unknown'),
            'python_version': os.sys.version,
            'uptime_seconds': health_checker._get_uptime_seconds()
        }
        
        return jsonify(version_data), StatusCodes.OK
    except Exception as e:
        caloria_logger.error("Version info failed", e)
        return jsonify({
            'error': 'Version info failed',
            'message': str(e)
        }), StatusCodes.INTERNAL_ERROR

# Monitoring utilities
def register_health_checks(app, db):
    """Register health checks with Flask app"""
    # Initialize health checker with database
    global health_checker
    health_checker = HealthChecker(db)
    
    # Register blueprint
    app.register_blueprint(health_bp)
    
    # Add health check to app context
    app.health_checker = health_checker
    
    caloria_logger.info("Health check endpoints registered")

def get_health_summary() -> Dict[str, Any]:
    """Get a summary of health status for dashboards"""
    try:
        health_status = health_checker.get_overall_health()
        
        summary = {
            'overall_status': health_status['status'],
            'timestamp': health_status['timestamp'],
            'uptime_hours': round(health_status.get('uptime_seconds', 0) / 3600, 1),
            'response_time_ms': health_status.get('response_time_ms', 0),
            'issues': []
        }
        
        # Extract issues from health checks
        for check_name, check_data in health_status.get('checks', {}).items():
            if isinstance(check_data, dict):
                status = check_data.get('status', 'unknown')
                if status in ['degraded', 'unhealthy']:
                    summary['issues'].append({
                        'component': check_name,
                        'status': status,
                        'message': check_data.get('message', 'No details available')
                    })
        
        return summary
        
    except Exception as e:
        caloria_logger.error("Health summary failed", e)
        return {
            'overall_status': 'unknown',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        } 