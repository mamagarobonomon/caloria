"""
Custom Exception Classes for Caloria Application
Provides structured error handling with specific exception types
"""

class CaloriaException(Exception):
    """Base exception for Caloria application"""
    
    def __init__(self, message, error_code=None, details=None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self):
        """Convert exception to dictionary for API responses"""
        return {
            'error': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details
        }

class ValidationException(CaloriaException):
    """Raised when input validation fails"""
    
    def __init__(self, field, message, value=None):
        self.field = field
        self.value = value
        super().__init__(f"Validation error for {field}: {message}", 
                        error_code="VALIDATION_ERROR",
                        details={'field': field, 'value': value})

class FoodAnalysisException(CaloriaException):
    """Raised when food analysis fails"""
    
    def __init__(self, message, analysis_method=None, confidence_score=None):
        self.analysis_method = analysis_method
        self.confidence_score = confidence_score
        super().__init__(message, 
                        error_code="FOOD_ANALYSIS_ERROR",
                        details={
                            'analysis_method': analysis_method,
                            'confidence_score': confidence_score
                        })

class WebhookValidationException(CaloriaException):
    """Raised when webhook data is invalid"""
    
    def __init__(self, message, webhook_type=None, missing_fields=None):
        self.webhook_type = webhook_type
        self.missing_fields = missing_fields or []
        super().__init__(message,
                        error_code="WEBHOOK_VALIDATION_ERROR", 
                        details={
                            'webhook_type': webhook_type,
                            'missing_fields': missing_fields
                        })

class SubscriptionException(CaloriaException):
    """Raised when subscription operations fail"""
    
    def __init__(self, message, user_id=None, subscription_id=None, operation=None):
        self.user_id = user_id
        self.subscription_id = subscription_id
        self.operation = operation
        super().__init__(message,
                        error_code="SUBSCRIPTION_ERROR",
                        details={
                            'user_id': user_id,
                            'subscription_id': subscription_id,
                            'operation': operation
                        })

class APIException(CaloriaException):
    """Raised when external API calls fail"""
    
    def __init__(self, message, api_service=None, status_code=None, response_data=None):
        self.api_service = api_service
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(message,
                        error_code="API_ERROR",
                        details={
                            'api_service': api_service,
                            'status_code': status_code,
                            'response_data': response_data
                        })

class DatabaseException(CaloriaException):
    """Raised when database operations fail"""
    
    def __init__(self, message, operation=None, table=None):
        self.operation = operation
        self.table = table
        super().__init__(message,
                        error_code="DATABASE_ERROR",
                        details={
                            'operation': operation,
                            'table': table
                        })

class AuthenticationException(CaloriaException):
    """Raised when authentication fails"""
    
    def __init__(self, message, user_id=None, auth_method=None):
        self.user_id = user_id
        self.auth_method = auth_method
        super().__init__(message,
                        error_code="AUTHENTICATION_ERROR",
                        details={
                            'user_id': user_id,
                            'auth_method': auth_method
                        })

class RateLimitException(CaloriaException):
    """Raised when rate limits are exceeded"""
    
    def __init__(self, message, limit_type=None, reset_time=None):
        self.limit_type = limit_type
        self.reset_time = reset_time
        super().__init__(message,
                        error_code="RATE_LIMIT_ERROR",
                        details={
                            'limit_type': limit_type,
                            'reset_time': reset_time
                        })

class FileProcessingException(CaloriaException):
    """Raised when file processing fails"""
    
    def __init__(self, message, file_type=None, file_size=None, filename=None):
        self.file_type = file_type
        self.file_size = file_size
        self.filename = filename
        super().__init__(message,
                        error_code="FILE_PROCESSING_ERROR",
                        details={
                            'file_type': file_type,
                            'file_size': file_size,
                            'filename': filename
                        })

# Exception handler decorators
def handle_exceptions(exception_types=None, default_response=None):
    """Decorator to handle specific exception types in routes"""
    if exception_types is None:
        exception_types = (CaloriaException,)
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                if hasattr(e, 'to_dict'):
                    error_dict = e.to_dict()
                    status_code = getattr(e, 'status_code', 400)
                    return {'error': error_dict}, status_code
                else:
                    return default_response or {'error': str(e)}, 500
            except Exception as e:
                return {'error': f'Unexpected error: {str(e)}'}, 500
        return wrapper
    return decorator 