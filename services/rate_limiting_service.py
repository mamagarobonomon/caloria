"""
Rate Limiting Service for Caloria Application
Provides rate limiting functionality to protect against abuse
"""

from flask import request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config.constants import AppConstants
from exceptions import RateLimitException
import time
from typing import Optional

class RateLimitingService:
    """Service for managing rate limits"""
    
    def __init__(self, app=None):
        self.limiter = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize rate limiting for Flask app"""
        self.limiter = Limiter(
            key_func=self._get_rate_limit_key,
            default_limits=[AppConstants.DEFAULT_RATE_LIMIT],
            storage_uri="memory://",  # Use Redis in production
            strategy="fixed-window"
        )
        self.limiter.init_app(app)
        
        # Custom error handler for rate limits
        @self.limiter.request_filter
        def exempt_admin():
            """Exempt admin routes from rate limiting"""
            return request.endpoint and request.endpoint.startswith('admin_')
        
        @app.errorhandler(429)
        def rate_limit_handler(e):
            """Handle rate limit exceeded errors"""
            return jsonify({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests. Please try again later.',
                'retry_after': getattr(e, 'retry_after', 60)
            }), 429
    
    def _get_rate_limit_key(self) -> str:
        """
        Determine rate limit key based on request context
        Uses IP address by default, but can use user ID for authenticated requests
        """
        # For webhook requests, try to get subscriber_id
        if request.endpoint in ['manychat_webhook', 'mercadopago_webhook']:
            try:
                data = request.get_json()
                if data:
                    subscriber_id = data.get('id', data.get('subscriber_id'))
                    if subscriber_id:
                        return f"webhook_{subscriber_id}"
            except:
                pass
        
        # For admin requests, use session-based limiting
        if request.endpoint and request.endpoint.startswith('admin_'):
            from flask import session
            admin_id = session.get('admin_id')
            if admin_id:
                return f"admin_{admin_id}"
        
        # Default to IP address
        return get_remote_address()
    
    def limit_webhook(self, rate_limit: str = AppConstants.WEBHOOK_RATE_LIMIT):
        """Decorator for webhook rate limiting"""
        return self.limiter.limit(rate_limit)
    
    def limit_api(self, rate_limit: str = AppConstants.API_RATE_LIMIT):
        """Decorator for API rate limiting"""
        return self.limiter.limit(rate_limit)
    
    def limit_admin(self, rate_limit: str = AppConstants.ADMIN_RATE_LIMIT):
        """Decorator for admin rate limiting"""
        return self.limiter.limit(rate_limit)
    
    def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """
        Check if rate limit is exceeded for a specific key
        Returns True if limit is exceeded
        """
        try:
            current_time = int(time.time())
            window_start = current_time - (current_time % window)
            
            # This is a simplified implementation
            # In production, use Redis with proper sliding window
            return False  # Placeholder
            
        except Exception:
            # If rate limiting fails, allow the request
            return False
    
    def get_rate_limit_status(self, key: str) -> dict:
        """Get current rate limit status for a key"""
        try:
            # This would integrate with the actual limiter storage
            return {
                'limit': 100,
                'remaining': 95,
                'reset_time': int(time.time()) + 3600
            }
        except Exception:
            return {
                'limit': 100,
                'remaining': 100,
                'reset_time': int(time.time()) + 3600
            }

# Global instance to be used in app.py
rate_limiter = RateLimitingService()

# Decorator functions for easy use
def limit_webhook(rate: str = AppConstants.WEBHOOK_RATE_LIMIT):
    """Decorator for webhook endpoints"""
    def decorator(func):
        return rate_limiter.limit_webhook(rate)(func)
    return decorator

def limit_api(rate: str = AppConstants.API_RATE_LIMIT):
    """Decorator for API endpoints"""
    def decorator(func):
        return rate_limiter.limit_api(rate)(func)
    return decorator

def limit_admin(rate: str = AppConstants.ADMIN_RATE_LIMIT):
    """Decorator for admin endpoints"""
    def decorator(func):
        return rate_limiter.limit_admin(rate)(func)
    return decorator 