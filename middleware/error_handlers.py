"""
Error Handling Middleware for Caloria Application
Provides comprehensive error handling, structured logging, and user-friendly responses
"""

import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from flask import request, jsonify, g
from werkzeug.exceptions import HTTPException

from config.constants import StatusCodes, Messages
from services.logging_service import caloria_logger, LogLevels
from services.metrics_service import metrics
from exceptions import (
    CaloriaException, ValidationException, FoodAnalysisException,
    WebhookValidationException, APIException, DatabaseException,
    AuthenticationException, RateLimitException, FileProcessingException
)

class ErrorHandler:
    """Centralized error handler for the application"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = caloria_logger
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize error handlers for Flask app"""
        
        # Register custom exception handlers
        app.register_error_handler(CaloriaException, self.handle_caloria_exception)
        app.register_error_handler(ValidationException, self.handle_validation_exception)
        app.register_error_handler(FoodAnalysisException, self.handle_food_analysis_exception)
        app.register_error_handler(WebhookValidationException, self.handle_webhook_exception)
        app.register_error_handler(APIException, self.handle_api_exception)
        app.register_error_handler(DatabaseException, self.handle_database_exception)
        app.register_error_handler(AuthenticationException, self.handle_auth_exception)
        app.register_error_handler(RateLimitException, self.handle_rate_limit_exception)
        app.register_error_handler(FileProcessingException, self.handle_file_exception)
        
        # Register HTTP error handlers
        app.register_error_handler(400, self.handle_bad_request)
        app.register_error_handler(401, self.handle_unauthorized)
        app.register_error_handler(403, self.handle_forbidden)
        app.register_error_handler(404, self.handle_not_found)
        app.register_error_handler(405, self.handle_method_not_allowed)
        app.register_error_handler(429, self.handle_rate_limit)
        app.register_error_handler(500, self.handle_internal_error)
        app.register_error_handler(502, self.handle_bad_gateway)
        app.register_error_handler(503, self.handle_service_unavailable)
        
        # Register generic exception handler
        app.register_error_handler(Exception, self.handle_generic_exception)
        
        # Add before/after request handlers for request tracking
        app.before_request(self.before_request)
        app.after_request(self.after_request)
    
    def before_request(self):
        """Track request start time and basic info"""
        g.request_start_time = datetime.utcnow()
        g.request_id = self._generate_request_id()
        
        # Log incoming request (excluding health checks)
        if not request.path.startswith('/health'):
            self.logger.info(
                f"Request started: {request.method} {request.path}",
                {
                    'request_id': g.request_id,
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.environ.get('HTTP_X_FORWARDED_FOR', 
                                                     request.environ.get('REMOTE_ADDR')),
                    'user_agent': request.headers.get('User-Agent', '')[:200]
                },
                category=LogLevels.API
            )
    
    def after_request(self, response):
        """Log request completion and performance metrics"""
        if hasattr(g, 'request_start_time'):
            duration = (datetime.utcnow() - g.request_start_time).total_seconds() * 1000
            
            # Don't log health check requests
            if not request.path.startswith('/health'):
                self.logger.info(
                    f"Request completed: {request.method} {request.path} - {response.status_code}",
                    {
                        'request_id': getattr(g, 'request_id', 'unknown'),
                        'status_code': response.status_code,
                        'duration_ms': round(duration, 2),
                        'response_size': len(response.get_data()) if response.get_data() else 0
                    },
                    category=LogLevels.API
                )
                
                # Record performance metrics
                metrics.record_timing('http_request', duration, {
                    'method': request.method,
                    'endpoint': request.endpoint,
                    'status_code': str(response.status_code)
                })
        
        return response
    
    def handle_caloria_exception(self, e: CaloriaException) -> Tuple[Dict[str, Any], int]:
        """Handle custom Caloria exceptions"""
        self._log_exception(e, LogLevels.WARNING)
        
        return jsonify({
            'error': e.error_code or 'CALORIA_ERROR',
            'message': e.message,
            'details': e.details,
            'request_id': getattr(g, 'request_id', None),
            'timestamp': datetime.utcnow().isoformat()
        }), getattr(e, 'status_code', StatusCodes.BAD_REQUEST)
    
    def handle_validation_exception(self, e: ValidationException) -> Tuple[Dict[str, Any], int]:
        """Handle validation errors"""
        self._log_exception(e, LogLevels.WARNING)
        
        metrics.record_error('validation_error', str(e), {
            'field': e.field,
            'value': str(e.value) if e.value else None
        })
        
        return jsonify({
            'error': 'VALIDATION_ERROR',
            'message': 'Datos de entrada inválidos',
            'field': e.field,
            'details': e.details,
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.BAD_REQUEST
    
    def handle_food_analysis_exception(self, e: FoodAnalysisException) -> Tuple[Dict[str, Any], int]:
        """Handle food analysis errors"""
        self._log_exception(e, LogLevels.ERROR)
        
        metrics.record_error('food_analysis_error', str(e), {
            'analysis_method': e.analysis_method,
            'confidence_score': e.confidence_score
        })
        
        # Provide user-friendly message based on analysis method
        if e.analysis_method == 'image':
            user_message = Messages.INVALID_IMAGE
        elif e.analysis_method == 'audio':
            user_message = Messages.INVALID_AUDIO
        else:
            user_message = Messages.INVALID_TEXT
        
        return jsonify({
            'error': 'FOOD_ANALYSIS_ERROR',
            'message': user_message,
            'analysis_method': e.analysis_method,
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.INTERNAL_ERROR
    
    def handle_webhook_exception(self, e: WebhookValidationException) -> Tuple[Dict[str, Any], int]:
        """Handle webhook validation errors"""
        self._log_exception(e, LogLevels.WARNING)
        
        metrics.record_error('webhook_validation_error', str(e), {
            'webhook_type': e.webhook_type,
            'missing_fields': e.missing_fields
        })
        
        return jsonify({
            'error': 'WEBHOOK_VALIDATION_ERROR',
            'message': 'Webhook data is invalid',
            'webhook_type': e.webhook_type,
            'missing_fields': e.missing_fields,
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.BAD_REQUEST
    
    def handle_api_exception(self, e: APIException) -> Tuple[Dict[str, Any], int]:
        """Handle external API errors"""
        self._log_exception(e, LogLevels.ERROR)
        
        metrics.record_error('api_error', str(e), {
            'api_service': e.api_service,
            'status_code': e.status_code
        })
        
        return jsonify({
            'error': 'EXTERNAL_API_ERROR',
            'message': Messages.SYSTEM_ERROR,
            'service': e.api_service,
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.INTERNAL_ERROR
    
    def handle_database_exception(self, e: DatabaseException) -> Tuple[Dict[str, Any], int]:
        """Handle database errors"""
        self._log_exception(e, LogLevels.ERROR)
        
        metrics.record_error('database_error', str(e), {
            'operation': e.operation,
            'table': e.table
        })
        
        return jsonify({
            'error': 'DATABASE_ERROR',
            'message': Messages.SYSTEM_ERROR,
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.INTERNAL_ERROR
    
    def handle_auth_exception(self, e: AuthenticationException) -> Tuple[Dict[str, Any], int]:
        """Handle authentication errors"""
        self._log_exception(e, LogLevels.WARNING)
        
        metrics.record_error('authentication_error', str(e), {
            'auth_method': e.auth_method,
            'user_id': e.user_id
        })
        
        return jsonify({
            'error': 'AUTHENTICATION_ERROR',
            'message': 'Authentication failed',
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.UNAUTHORIZED
    
    def handle_rate_limit_exception(self, e: RateLimitException) -> Tuple[Dict[str, Any], int]:
        """Handle rate limit errors"""
        self._log_exception(e, LogLevels.WARNING)
        
        return jsonify({
            'error': 'RATE_LIMIT_EXCEEDED',
            'message': Messages.RATE_LIMIT_EXCEEDED,
            'limit_type': e.limit_type,
            'reset_time': e.reset_time,
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.RATE_LIMITED
    
    def handle_file_exception(self, e: FileProcessingException) -> Tuple[Dict[str, Any], int]:
        """Handle file processing errors"""
        self._log_exception(e, LogLevels.WARNING)
        
        metrics.record_error('file_processing_error', str(e), {
            'file_type': e.file_type,
            'file_size': e.file_size
        })
        
        # Choose appropriate user message
        if e.file_type == 'image':
            user_message = Messages.INVALID_IMAGE
        elif e.file_type == 'audio':
            user_message = Messages.INVALID_AUDIO
        else:
            user_message = 'Error procesando archivo'
        
        return jsonify({
            'error': 'FILE_PROCESSING_ERROR',
            'message': user_message,
            'file_type': e.file_type,
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.BAD_REQUEST
    
    def handle_bad_request(self, e: HTTPException) -> Tuple[Dict[str, Any], int]:
        """Handle 400 Bad Request errors"""
        self._log_http_exception(e, LogLevels.WARNING)
        
        return jsonify({
            'error': 'BAD_REQUEST',
            'message': 'Solicitud inválida',
            'details': str(e.description) if e.description else None,
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.BAD_REQUEST
    
    def handle_unauthorized(self, e: HTTPException) -> Tuple[Dict[str, Any], int]:
        """Handle 401 Unauthorized errors"""
        self._log_http_exception(e, LogLevels.WARNING)
        
        return jsonify({
            'error': 'UNAUTHORIZED',
            'message': 'Acceso no autorizado',
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.UNAUTHORIZED
    
    def handle_forbidden(self, e: HTTPException) -> Tuple[Dict[str, Any], int]:
        """Handle 403 Forbidden errors"""
        self._log_http_exception(e, LogLevels.WARNING)
        
        return jsonify({
            'error': 'FORBIDDEN',
            'message': 'Acceso denegado',
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.FORBIDDEN
    
    def handle_not_found(self, e: HTTPException) -> Tuple[Dict[str, Any], int]:
        """Handle 404 Not Found errors"""
        self._log_http_exception(e, LogLevels.INFO)
        
        return jsonify({
            'error': 'NOT_FOUND',
            'message': 'Recurso no encontrado',
            'path': request.path,
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.NOT_FOUND
    
    def handle_method_not_allowed(self, e: HTTPException) -> Tuple[Dict[str, Any], int]:
        """Handle 405 Method Not Allowed errors"""
        self._log_http_exception(e, LogLevels.WARNING)
        
        return jsonify({
            'error': 'METHOD_NOT_ALLOWED',
            'message': f'Método {request.method} no permitido para {request.path}',
            'allowed_methods': e.description,
            'request_id': getattr(g, 'request_id', None)
        }), 405
    
    def handle_rate_limit(self, e: HTTPException) -> Tuple[Dict[str, Any], int]:
        """Handle 429 Rate Limit errors"""
        self._log_http_exception(e, LogLevels.WARNING)
        
        return jsonify({
            'error': 'RATE_LIMIT_EXCEEDED',
            'message': Messages.RATE_LIMIT_EXCEEDED,
            'retry_after': getattr(e, 'retry_after', 60),
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.RATE_LIMITED
    
    def handle_internal_error(self, e: HTTPException) -> Tuple[Dict[str, Any], int]:
        """Handle 500 Internal Server Error"""
        self._log_http_exception(e, LogLevels.ERROR)
        
        return jsonify({
            'error': 'INTERNAL_SERVER_ERROR',
            'message': Messages.SYSTEM_ERROR,
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.INTERNAL_ERROR
    
    def handle_bad_gateway(self, e: HTTPException) -> Tuple[Dict[str, Any], int]:
        """Handle 502 Bad Gateway errors"""
        self._log_http_exception(e, LogLevels.ERROR)
        
        return jsonify({
            'error': 'BAD_GATEWAY',
            'message': 'Error del servidor externo',
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.BAD_GATEWAY
    
    def handle_service_unavailable(self, e: HTTPException) -> Tuple[Dict[str, Any], int]:
        """Handle 503 Service Unavailable errors"""
        self._log_http_exception(e, LogLevels.ERROR)
        
        return jsonify({
            'error': 'SERVICE_UNAVAILABLE',
            'message': 'Servicio temporalmente no disponible',
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.SERVICE_UNAVAILABLE
    
    def handle_generic_exception(self, e: Exception) -> Tuple[Dict[str, Any], int]:
        """Handle any unhandled exceptions"""
        self._log_exception(e, LogLevels.CRITICAL)
        
        metrics.record_error('unhandled_exception', str(e), {
            'exception_type': type(e).__name__
        })
        
        return jsonify({
            'error': 'UNHANDLED_EXCEPTION',
            'message': Messages.SYSTEM_ERROR,
            'exception_type': type(e).__name__,
            'request_id': getattr(g, 'request_id', None)
        }), StatusCodes.INTERNAL_ERROR
    
    def _log_exception(self, e: Exception, level: str):
        """Log exception with full context"""
        error_details = {
            'exception_type': type(e).__name__,
            'exception_message': str(e),
            'request_id': getattr(g, 'request_id', None),
            'request_path': request.path if request else None,
            'request_method': request.method if request else None,
            'stack_trace': traceback.format_exc()
        }
        
        # Add custom exception details if available
        if hasattr(e, 'details'):
            error_details['custom_details'] = e.details
        
        if level == LogLevels.CRITICAL:
            self.logger.critical(f"Unhandled exception: {str(e)}", e, error_details)
        elif level == LogLevels.ERROR:
            self.logger.error(f"Application error: {str(e)}", e, error_details)
        elif level == LogLevels.WARNING:
            self.logger.warning(f"Application warning: {str(e)}", error_details)
        else:
            self.logger.info(f"Application info: {str(e)}", error_details)
    
    def _log_http_exception(self, e: HTTPException, level: str):
        """Log HTTP exception"""
        error_details = {
            'status_code': e.code,
            'description': e.description,
            'request_id': getattr(g, 'request_id', None),
            'request_path': request.path if request else None,
            'request_method': request.method if request else None
        }
        
        if level == LogLevels.ERROR:
            self.logger.error(f"HTTP {e.code}: {e.name}", error_details)
        elif level == LogLevels.WARNING:
            self.logger.warning(f"HTTP {e.code}: {e.name}", error_details)
        else:
            self.logger.info(f"HTTP {e.code}: {e.name}", error_details)
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        import uuid
        return str(uuid.uuid4())[:8]

# Context managers for error handling
class ErrorContext:
    """Context manager for handling specific operations with error logging"""
    
    def __init__(self, operation_name: str, logger=None, 
                 user_id: Optional[str] = None, reraise: bool = True):
        self.operation_name = operation_name
        self.logger = logger or caloria_logger
        self.user_id = user_id
        self.reraise = reraise
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        
        if exc_type is None:
            # Operation succeeded
            self.logger.info(
                f"Operation completed: {self.operation_name}",
                {
                    'duration_ms': round(duration, 2),
                    'user_id': self.user_id,
                    'success': True
                }
            )
        else:
            # Operation failed
            self.logger.error(
                f"Operation failed: {self.operation_name}",
                exc_val,
                {
                    'duration_ms': round(duration, 2),
                    'user_id': self.user_id,
                    'exception_type': exc_type.__name__,
                    'success': False
                },
                user_id=self.user_id
            )
            
            # Record error metrics
            metrics.record_error(
                f"{self.operation_name}_error",
                str(exc_val),
                {'user_id': self.user_id}
            )
            
            if not self.reraise:
                return True  # Suppress exception
        
        return False

# Decorator for automatic error handling
def handle_errors(operation_name: str = None, user_friendly_message: str = None):
    """Decorator for automatic error handling and logging"""
    def decorator(func):
        op_name = operation_name or func.__name__
        
        def wrapper(*args, **kwargs):
            try:
                with ErrorContext(op_name, reraise=True):
                    return func(*args, **kwargs)
            except CaloriaException:
                # Let custom exceptions bubble up to be handled by error handlers
                raise
            except Exception as e:
                # Convert unexpected exceptions to CaloriaException
                caloria_logger.error(
                    f"Unexpected error in {op_name}: {str(e)}",
                    e,
                    {'function': func.__name__, 'args': str(args)[:200]}
                )
                
                message = user_friendly_message or Messages.SYSTEM_ERROR
                raise CaloriaException(message, error_code="UNEXPECTED_ERROR") from e
        
        return wrapper
    return decorator

# Global error handler instance
error_handler = ErrorHandler() 