"""
Metrics Service for Caloria Application
Provides comprehensive performance monitoring and metrics collection
"""

import time
from datetime import datetime, timedelta
from collections import defaultdict, deque
from typing import Dict, List, Any, Optional
from services.logging_service import caloria_logger, LogTimer
from config.constants import AppConstants
import threading

class MetricsService:
    """Service for collecting and analyzing application metrics"""
    
    def __init__(self):
        self.logger = caloria_logger
        
        # Counters for various events
        self.counters = defaultdict(int)
        
        # Timing data (store last N measurements)
        self.timings = defaultdict(lambda: deque(maxlen=1000))
        
        # Error tracking
        self.errors = defaultdict(int)
        self.error_details = defaultdict(list)
        
        # Custom metrics
        self.custom_metrics = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Startup time
        self.startup_time = datetime.utcnow()
    
    def increment(self, metric_name: str, value: int = 1, labels: Dict[str, str] = None) -> None:
        """Increment a counter metric"""
        with self._lock:
            key = self._build_metric_key(metric_name, labels)
            self.counters[key] += value
            
            # Log significant events
            if value > 1 or metric_name in ['webhook_received', 'food_analysis_completed']:
                self.logger.log_performance_metric(metric_name, value, 'count')
    
    def record_timing(self, metric_name: str, duration_ms: float, 
                     labels: Dict[str, str] = None) -> None:
        """Record timing measurement"""
        with self._lock:
            key = self._build_metric_key(metric_name, labels)
            self.timings[key].append({
                'duration_ms': duration_ms,
                'timestamp': datetime.utcnow()
            })
            
            # Log slow operations
            if duration_ms > 5000:  # 5 seconds
                self.logger.warning(
                    f"Slow operation detected: {metric_name}",
                    {'duration_ms': duration_ms, 'labels': labels}
                )
    
    def record_error(self, error_type: str, error_message: str, 
                    labels: Dict[str, str] = None) -> None:
        """Record error occurrence"""
        with self._lock:
            key = self._build_metric_key(error_type, labels)
            self.errors[key] += 1
            
            # Store error details (keep last 100)
            if len(self.error_details[key]) >= 100:
                self.error_details[key].pop(0)
            
            self.error_details[key].append({
                'message': error_message,
                'timestamp': datetime.utcnow(),
                'labels': labels or {}
            })
    
    def set_gauge(self, metric_name: str, value: float, 
                 labels: Dict[str, str] = None) -> None:
        """Set gauge metric value"""
        with self._lock:
            key = self._build_metric_key(metric_name, labels)
            self.custom_metrics[key] = {
                'value': value,
                'type': 'gauge',
                'timestamp': datetime.utcnow(),
                'labels': labels or {}
            }
    
    def _build_metric_key(self, metric_name: str, labels: Dict[str, str] = None) -> str:
        """Build metric key with labels"""
        if not labels:
            return metric_name
        
        label_str = ','.join([f"{k}={v}" for k, v in sorted(labels.items())])
        return f"{metric_name}{{{label_str}}}"
    
    def get_counter_value(self, metric_name: str, labels: Dict[str, str] = None) -> int:
        """Get current counter value"""
        key = self._build_metric_key(metric_name, labels)
        return self.counters.get(key, 0)
    
    def get_timing_stats(self, metric_name: str, labels: Dict[str, str] = None) -> Dict[str, float]:
        """Get timing statistics for a metric"""
        key = self._build_metric_key(metric_name, labels)
        timings = self.timings.get(key, [])
        
        if not timings:
            return {}
        
        durations = [t['duration_ms'] for t in timings]
        durations.sort()
        
        count = len(durations)
        return {
            'count': count,
            'min_ms': min(durations),
            'max_ms': max(durations),
            'avg_ms': sum(durations) / count,
            'p50_ms': durations[count // 2],
            'p95_ms': durations[int(count * 0.95)] if count > 20 else durations[-1],
            'p99_ms': durations[int(count * 0.99)] if count > 100 else durations[-1]
        }
    
    def get_error_rate(self, error_type: str, time_window_minutes: int = 60,
                      labels: Dict[str, str] = None) -> float:
        """Get error rate for time window"""
        key = self._build_metric_key(error_type, labels)
        error_details = self.error_details.get(key, [])
        
        if not error_details:
            return 0.0
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        recent_errors = [
            e for e in error_details 
            if e['timestamp'] > cutoff_time
        ]
        
        # Calculate rate as errors per minute
        return len(recent_errors) / time_window_minutes
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics data"""
        with self._lock:
            # Calculate uptime
            uptime_seconds = (datetime.utcnow() - self.startup_time).total_seconds()
            
            # Get recent performance data
            webhook_stats = self.get_timing_stats('webhook_processing')
            db_stats = self.get_timing_stats('database_query')
            api_stats = self.get_timing_stats('api_request')
            
            return {
                'system': {
                    'uptime_seconds': uptime_seconds,
                    'startup_time': self.startup_time.isoformat()
                },
                'counters': dict(self.counters),
                'performance': {
                    'webhook_processing': webhook_stats,
                    'database_queries': db_stats,
                    'api_requests': api_stats
                },
                'errors': {
                    'total_errors': dict(self.errors),
                    'error_rates': {
                        error_type: self.get_error_rate(error_type.split('{')[0])
                        for error_type in self.errors.keys()
                    }
                },
                'custom_metrics': self.custom_metrics,
                'collection_time': datetime.utcnow().isoformat()
            }
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get health-focused metrics"""
        # Check recent error rates
        recent_webhook_errors = self.get_error_rate('webhook_error', 15)  # Last 15 minutes
        recent_db_errors = self.get_error_rate('database_error', 15)
        recent_api_errors = self.get_error_rate('api_error', 15)
        
        # Check recent response times
        webhook_stats = self.get_timing_stats('webhook_processing')
        db_stats = self.get_timing_stats('database_query')
        
        # Determine health status
        health_status = 'healthy'
        issues = []
        
        # Check error rates
        if recent_webhook_errors > 1:  # More than 1 error per minute
            health_status = 'degraded'
            issues.append(f"High webhook error rate: {recent_webhook_errors:.2f}/min")
        
        if recent_db_errors > 0.5:
            health_status = 'degraded'
            issues.append(f"Database errors detected: {recent_db_errors:.2f}/min")
        
        # Check response times
        if webhook_stats.get('p95_ms', 0) > 10000:  # 10 seconds
            health_status = 'degraded'
            issues.append(f"Slow webhook processing: {webhook_stats['p95_ms']:.0f}ms p95")
        
        if db_stats.get('p95_ms', 0) > 2000:  # 2 seconds
            health_status = 'degraded'
            issues.append(f"Slow database queries: {db_stats['p95_ms']:.0f}ms p95")
        
        if recent_webhook_errors > 5 or recent_db_errors > 2:
            health_status = 'unhealthy'
        
        return {
            'status': health_status,
            'issues': issues,
            'metrics': {
                'error_rates': {
                    'webhook_errors_per_min': recent_webhook_errors,
                    'database_errors_per_min': recent_db_errors,
                    'api_errors_per_min': recent_api_errors
                },
                'response_times': {
                    'webhook_p95_ms': webhook_stats.get('p95_ms', 0),
                    'database_p95_ms': db_stats.get('p95_ms', 0)
                },
                'throughput': {
                    'webhooks_per_min': self.get_rate('webhook_received', 5),
                    'food_analyses_per_min': self.get_rate('food_analysis_completed', 5)
                }
            }
        }
    
    def get_rate(self, metric_name: str, time_window_minutes: int = 5) -> float:
        """Calculate rate for a counter metric"""
        # This is simplified - in production you'd track timestamps
        current_value = self.get_counter_value(metric_name)
        return current_value / time_window_minutes  # Rough estimate
    
    def reset_metrics(self) -> None:
        """Reset all metrics (use carefully)"""
        with self._lock:
            self.counters.clear()
            self.timings.clear()
            self.errors.clear()
            self.error_details.clear()
            self.custom_metrics.clear()
            self.startup_time = datetime.utcnow()
            
        self.logger.info("All metrics reset")

# Global metrics instance
metrics = MetricsService()

# Decorator for automatic timing
def timed_operation(metric_name: str, labels: Dict[str, str] = None):
    """Decorator to automatically time function execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                metrics.record_timing(metric_name, duration_ms, labels)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                metrics.record_timing(metric_name, duration_ms, labels)
                metrics.record_error(f"{metric_name}_error", str(e), labels)
                raise
        return wrapper
    return decorator

# Specialized metric collectors
class WebhookMetrics:
    """Specialized metrics for webhook operations"""
    
    @staticmethod
    def record_webhook_received(webhook_type: str, user_id: str = None):
        """Record webhook reception"""
        labels = {'type': webhook_type}
        if user_id:
            labels['user_type'] = 'registered' if user_id != 'unknown' else 'anonymous'
        
        metrics.increment('webhook_received', labels=labels)
    
    @staticmethod
    def record_webhook_processed(webhook_type: str, success: bool, 
                               processing_time_ms: float, user_id: str = None):
        """Record webhook processing completion"""
        labels = {
            'type': webhook_type,
            'status': 'success' if success else 'error'
        }
        
        metrics.increment('webhook_processed', labels=labels)
        metrics.record_timing('webhook_processing', processing_time_ms, labels)
        
        if not success:
            metrics.increment('webhook_errors', labels={'type': webhook_type})

class FoodAnalysisMetrics:
    """Specialized metrics for food analysis operations"""
    
    @staticmethod
    def record_analysis_started(method: str, user_id: str = None):
        """Record food analysis start"""
        labels = {'method': method}
        metrics.increment('food_analysis_started', labels=labels)
    
    @staticmethod
    def record_analysis_completed(method: str, confidence_score: float,
                                processing_time_ms: float, success: bool = True):
        """Record food analysis completion"""
        labels = {
            'method': method,
            'confidence_tier': FoodAnalysisMetrics._get_confidence_tier(confidence_score),
            'status': 'success' if success else 'error'
        }
        
        metrics.increment('food_analysis_completed', labels=labels)
        metrics.record_timing('food_analysis_processing', processing_time_ms, labels)
        metrics.set_gauge('food_analysis_confidence', confidence_score, labels)
        
        if not success:
            metrics.increment('food_analysis_errors', labels={'method': method})
    
    @staticmethod
    def _get_confidence_tier(confidence: float) -> str:
        """Categorize confidence score"""
        if confidence >= 0.8:
            return 'high'
        elif confidence >= 0.5:
            return 'medium'
        else:
            return 'low'

class DatabaseMetrics:
    """Specialized metrics for database operations"""
    
    @staticmethod
    def record_query(operation: str, table: str, execution_time_ms: float, 
                    success: bool = True):
        """Record database query"""
        labels = {
            'operation': operation,
            'table': table,
            'status': 'success' if success else 'error'
        }
        
        metrics.increment('database_queries', labels=labels)
        metrics.record_timing('database_query', execution_time_ms, labels)
        
        if not success:
            metrics.increment('database_errors', labels=labels)
    
    @staticmethod
    def record_connection_event(event_type: str):
        """Record database connection events"""
        metrics.increment('database_connections', labels={'event': event_type})

class APIMetrics:
    """Specialized metrics for external API calls"""
    
    @staticmethod
    def record_api_call(service: str, endpoint: str, method: str,
                       response_time_ms: float, status_code: int):
        """Record external API call"""
        labels = {
            'service': service,
            'endpoint': endpoint,
            'method': method,
            'status_category': APIMetrics._get_status_category(status_code)
        }
        
        metrics.increment('api_calls', labels=labels)
        metrics.record_timing('api_request', response_time_ms, labels)
        
        if status_code >= 400:
            metrics.increment('api_errors', labels=labels)
    
    @staticmethod
    def _get_status_category(status_code: int) -> str:
        """Categorize HTTP status code"""
        if 200 <= status_code < 300:
            return '2xx'
        elif 300 <= status_code < 400:
            return '3xx'
        elif 400 <= status_code < 500:
            return '4xx'
        elif 500 <= status_code < 600:
            return '5xx'
        else:
            return 'unknown'

class SubscriptionMetrics:
    """Specialized metrics for subscription operations"""
    
    @staticmethod
    def record_subscription_event(event_type: str, user_id: str = None):
        """Record subscription-related events"""
        labels = {'event_type': event_type}
        metrics.increment('subscription_events', labels=labels)
    
    @staticmethod
    def record_trial_conversion(success: bool, trial_duration_hours: float):
        """Record trial to paid conversion"""
        labels = {'converted': 'yes' if success else 'no'}
        metrics.increment('trial_conversions', labels=labels)
        metrics.set_gauge('trial_duration_hours', trial_duration_hours)

# Background metrics collection
def collect_system_metrics():
    """Collect system-level metrics"""
    try:
        import psutil
        
        # CPU and memory usage
        metrics.set_gauge('system_cpu_percent', psutil.cpu_percent())
        metrics.set_gauge('system_memory_percent', psutil.virtual_memory().percent)
        
        # Disk usage
        disk_usage = psutil.disk_usage('/')
        metrics.set_gauge('system_disk_percent', 
                         (disk_usage.used / disk_usage.total) * 100)
        
    except ImportError:
        # psutil not available, skip system metrics
        pass
    except Exception as e:
        caloria_logger.warning(f"System metrics collection failed: {str(e)}")

def generate_metrics_report() -> Dict[str, Any]:
    """Generate comprehensive metrics report"""
    all_metrics = metrics.get_all_metrics()
    health_metrics = metrics.get_health_metrics()
    
    # Calculate additional insights
    uptime_hours = all_metrics['system']['uptime_seconds'] / 3600
    
    report = {
        'summary': {
            'health_status': health_metrics['status'],
            'uptime_hours': round(uptime_hours, 2),
            'total_webhooks': metrics.get_counter_value('webhook_received'),
            'total_food_analyses': metrics.get_counter_value('food_analysis_completed'),
            'total_errors': sum(metrics.errors.values())
        },
        'performance': all_metrics['performance'],
        'health': health_metrics,
        'detailed_metrics': all_metrics,
        'report_generated_at': datetime.utcnow().isoformat()
    }
    
    return report 