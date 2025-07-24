"""
Logging Service for Caloria Application
Provides structured logging with different categories and levels
"""

import logging
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from config.constants import LogLevels
from flask import request, g
import os

class CaloriaLogger:
    """Enhanced logging service for Caloria application"""
    
    def __init__(self, name: str = 'caloria'):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with proper formatting and handlers"""
        if self.logger.handlers:
            return  # Already configured
        
        # Set level based on environment
        level = logging.DEBUG if os.getenv('FLASK_ENV') == 'development' else logging.INFO
        self.logger.setLevel(level)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler for production
        if os.getenv('FLASK_ENV') == 'production':
            try:
                os.makedirs('logs', exist_ok=True)
                file_handler = logging.FileHandler('logs/caloria.log')
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception:
                pass  # Fallback to console only
    
    def _get_request_context(self) -> Dict[str, Any]:
        """Get current request context for logging"""
        context = {}
        try:
            if request:
                context.update({
                    'method': request.method,
                    'endpoint': request.endpoint,
                    'path': request.path,
                    'remote_addr': request.environ.get('HTTP_X_FORWARDED_FOR', 
                                                     request.environ.get('REMOTE_ADDR')),
                    'user_agent': request.headers.get('User-Agent', '')[:200],  # Truncate
                    'content_type': request.content_type
                })
        except:
            pass
        return context
    
    def _format_log_entry(self, level: str, category: str, message: str, 
                         details: Dict[str, Any] = None, 
                         user_id: Optional[str] = None,
                         error: Optional[Exception] = None) -> str:
        """Format log entry as structured JSON"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'category': category,
            'message': message,
            'request_context': self._get_request_context()
        }
        
        if user_id:
            log_entry['user_id'] = user_id
        
        if details:
            log_entry['details'] = details
        
        if error:
            log_entry['error'] = {
                'type': error.__class__.__name__,
                'message': str(error),
                'traceback': traceback.format_exc()
            }
        
        return json.dumps(log_entry, ensure_ascii=False)
    
    # Webhook logging methods
    def log_webhook_received(self, webhook_type: str, data_size: int, user_id: str = None):
        """Log webhook reception"""
        details = {
            'webhook_type': webhook_type,
            'data_size': data_size
        }
        message = f"Webhook received: {webhook_type}"
        log_entry = self._format_log_entry(LogLevels.INFO, LogLevels.WEBHOOK, 
                                         message, details, user_id)
        self.logger.info(log_entry)
    
    def log_webhook_processed(self, webhook_type: str, processing_time: float, 
                            success: bool, user_id: str = None):
        """Log webhook processing completion"""
        details = {
            'webhook_type': webhook_type,
            'processing_time_ms': round(processing_time * 1000, 2),
            'success': success
        }
        level = LogLevels.INFO if success else LogLevels.ERROR
        message = f"Webhook processed: {webhook_type} ({'success' if success else 'failed'})"
        log_entry = self._format_log_entry(level, LogLevels.WEBHOOK, 
                                         message, details, user_id)
        if success:
            self.logger.info(log_entry)
        else:
            self.logger.error(log_entry)
    
    def log_webhook_error(self, webhook_type: str, error: Exception, 
                         request_data: str = None, user_id: str = None):
        """Log webhook processing errors"""
        details = {
            'webhook_type': webhook_type,
            'request_data_preview': request_data[:500] if request_data else None
        }
        message = f"Webhook error: {webhook_type}"
        log_entry = self._format_log_entry(LogLevels.ERROR, LogLevels.WEBHOOK, 
                                         message, details, user_id, error)
        self.logger.error(log_entry)
    
    # API logging methods
    def log_api_request(self, service: str, method: str, url: str, 
                       user_id: str = None):
        """Log external API request"""
        details = {
            'service': service,
            'method': method,
            'url': url
        }
        message = f"API request: {service} {method}"
        log_entry = self._format_log_entry(LogLevels.INFO, LogLevels.API, 
                                         message, details, user_id)
        self.logger.info(log_entry)
    
    def log_api_response(self, service: str, method: str, status_code: int, 
                        response_time: float, user_id: str = None):
        """Log external API response"""
        details = {
            'service': service,
            'method': method,
            'status_code': status_code,
            'response_time_ms': round(response_time * 1000, 2)
        }
        level = LogLevels.INFO if 200 <= status_code < 300 else LogLevels.WARNING
        message = f"API response: {service} {status_code}"
        log_entry = self._format_log_entry(level, LogLevels.API, 
                                         message, details, user_id)
        if level == LogLevels.INFO:
            self.logger.info(log_entry)
        else:
            self.logger.warning(log_entry)
    
    def log_api_error(self, service: str, method: str, error: Exception, 
                     user_id: str = None):
        """Log external API errors"""
        details = {
            'service': service,
            'method': method
        }
        message = f"API error: {service} {method}"
        log_entry = self._format_log_entry(LogLevels.ERROR, LogLevels.API, 
                                         message, details, user_id, error)
        self.logger.error(log_entry)
    
    # Database logging methods
    def log_database_query(self, operation: str, table: str, 
                          execution_time: float, user_id: str = None):
        """Log database query performance"""
        details = {
            'operation': operation,
            'table': table,
            'execution_time_ms': round(execution_time * 1000, 2)
        }
        level = LogLevels.WARNING if execution_time > 1.0 else LogLevels.DEBUG
        message = f"Database query: {operation} on {table}"
        log_entry = self._format_log_entry(level, LogLevels.DATABASE, 
                                         message, details, user_id)
        if level == LogLevels.WARNING:
            self.logger.warning(log_entry)
        else:
            self.logger.debug(log_entry)
    
    def log_database_error(self, operation: str, table: str, error: Exception, 
                          user_id: str = None):
        """Log database errors"""
        details = {
            'operation': operation,
            'table': table
        }
        message = f"Database error: {operation} on {table}"
        log_entry = self._format_log_entry(LogLevels.ERROR, LogLevels.DATABASE, 
                                         message, details, user_id, error)
        self.logger.error(log_entry)
    
    # Security logging methods
    def log_security_event(self, event_type: str, severity: str, 
                          details: Dict[str, Any] = None, user_id: str = None):
        """Log security events"""
        message = f"Security event: {event_type}"
        log_entry = self._format_log_entry(severity, LogLevels.SECURITY, 
                                         message, details, user_id)
        if severity == LogLevels.CRITICAL:
            self.logger.critical(log_entry)
        elif severity == LogLevels.ERROR:
            self.logger.error(log_entry)
        elif severity == LogLevels.WARNING:
            self.logger.warning(log_entry)
        else:
            self.logger.info(log_entry)
    
    def log_rate_limit_exceeded(self, rate_type: str, key: str, 
                               limit: str, user_id: str = None):
        """Log rate limit violations"""
        details = {
            'rate_type': rate_type,
            'key': key,
            'limit': limit
        }
        message = f"Rate limit exceeded: {rate_type}"
        log_entry = self._format_log_entry(LogLevels.WARNING, LogLevels.SECURITY, 
                                         message, details, user_id)
        self.logger.warning(log_entry)
    
    def log_authentication_failure(self, auth_type: str, username: str = None, 
                                  reason: str = None):
        """Log authentication failures"""
        details = {
            'auth_type': auth_type,
            'username': username,
            'reason': reason
        }
        message = f"Authentication failure: {auth_type}"
        log_entry = self._format_log_entry(LogLevels.WARNING, LogLevels.SECURITY, 
                                         message, details)
        self.logger.warning(log_entry)
    
    # User action logging methods
    def log_user_action(self, action: str, details: Dict[str, Any] = None, 
                       user_id: str = None):
        """Log user actions for analytics"""
        message = f"User action: {action}"
        log_entry = self._format_log_entry(LogLevels.INFO, LogLevels.USER_ACTION, 
                                         message, details, user_id)
        self.logger.info(log_entry)
    
    def log_food_analysis(self, analysis_method: str, confidence_score: float, 
                         processing_time: float, user_id: str = None):
        """Log food analysis operations"""
        details = {
            'analysis_method': analysis_method,
            'confidence_score': confidence_score,
            'processing_time_ms': round(processing_time * 1000, 2)
        }
        message = f"Food analysis: {analysis_method}"
        log_entry = self._format_log_entry(LogLevels.INFO, LogLevels.USER_ACTION, 
                                         message, details, user_id)
        self.logger.info(log_entry)
    
    def log_subscription_event(self, event_type: str, subscription_id: str = None, 
                              details: Dict[str, Any] = None, user_id: str = None):
        """Log subscription-related events"""
        log_details = {'subscription_id': subscription_id}
        if details:
            log_details.update(details)
        
        message = f"Subscription event: {event_type}"
        log_entry = self._format_log_entry(LogLevels.INFO, LogLevels.USER_ACTION, 
                                         message, log_details, user_id)
        self.logger.info(log_entry)
    
    # Performance logging methods
    def log_performance_metric(self, metric_name: str, value: float, 
                              unit: str = 'ms', details: Dict[str, Any] = None):
        """Log performance metrics"""
        log_details = {
            'metric_name': metric_name,
            'value': value,
            'unit': unit
        }
        if details:
            log_details.update(details)
        
        level = LogLevels.WARNING if value > 5000 else LogLevels.INFO  # 5s threshold
        message = f"Performance metric: {metric_name}={value}{unit}"
        log_entry = self._format_log_entry(level, LogLevels.PERFORMANCE, 
                                         message, log_details)
        if level == LogLevels.WARNING:
            self.logger.warning(log_entry)
        else:
            self.logger.info(log_entry)
    
    # General logging methods
    def info(self, message: str, details: Dict[str, Any] = None, 
             category: str = LogLevels.INFO, user_id: str = None):
        """Log info message"""
        log_entry = self._format_log_entry(LogLevels.INFO, category, 
                                         message, details, user_id)
        self.logger.info(log_entry)
    
    def warning(self, message: str, details: Dict[str, Any] = None, 
               category: str = LogLevels.WARNING, user_id: str = None):
        """Log warning message"""
        log_entry = self._format_log_entry(LogLevels.WARNING, category, 
                                         message, details, user_id)
        self.logger.warning(log_entry)
    
    def error(self, message: str, error: Exception = None, 
             details: Dict[str, Any] = None, category: str = LogLevels.ERROR, 
             user_id: str = None):
        """Log error message"""
        log_entry = self._format_log_entry(LogLevels.ERROR, category, 
                                         message, details, user_id, error)
        self.logger.error(log_entry)
    
    def critical(self, message: str, error: Exception = None, 
                details: Dict[str, Any] = None, category: str = LogLevels.CRITICAL, 
                user_id: str = None):
        """Log critical message"""
        log_entry = self._format_log_entry(LogLevels.CRITICAL, category, 
                                         message, details, user_id, error)
        self.logger.critical(log_entry)

# Global logger instance
caloria_logger = CaloriaLogger()

# Context manager for timing operations
class LogTimer:
    """Context manager for timing and logging operations"""
    
    def __init__(self, operation_name: str, logger: CaloriaLogger = None, 
                 user_id: str = None):
        self.operation_name = operation_name
        self.logger = logger or caloria_logger
        self.user_id = user_id
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        
        if exc_type is None:
            # Operation completed successfully
            self.logger.log_performance_metric(
                self.operation_name, 
                duration * 1000,  # Convert to milliseconds
                'ms',
                {'user_id': self.user_id}
            )
        else:
            # Operation failed
            self.logger.error(
                f"Operation failed: {self.operation_name}",
                exc_val,
                {'duration_ms': duration * 1000},
                user_id=self.user_id
            ) 