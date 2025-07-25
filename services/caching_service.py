"""
Caching Service for Caloria Application
Provides intelligent caching for API responses and computed results
"""

import hashlib
import json
import pickle
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union, Callable
from functools import wraps
from config.constants import AppConstants
from services.logging_service import caloria_logger

class CacheService:
    """In-memory caching service with TTL support"""
    
    def __init__(self):
        self._cache = {}
        self._expiry = {}
        self.logger = caloria_logger
        self.hit_count = 0
        self.miss_count = 0
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else {}
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired"""
        if key not in self._expiry:
            return True
        return datetime.utcnow() > self._expiry[key]
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set cache value with TTL"""
        try:
            self._cache[key] = value
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
            self.logger.info(f"Cache set: {key[:20]}... (TTL: {ttl_seconds}s)")
        except Exception as e:
            self.logger.warning(f"Cache set failed: {str(e)}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get cache value if not expired"""
        try:
            if key in self._cache and not self._is_expired(key):
                self.hit_count += 1
                self.logger.info(f"Cache hit: {key[:20]}...")
                return self._cache[key]
            
            # Clean up expired entry
            if key in self._cache:
                del self._cache[key]
                del self._expiry[key]
            
            self.miss_count += 1
            self.logger.info(f"Cache miss: {key[:20]}...")
            return None
            
        except Exception as e:
            self.logger.warning(f"Cache get failed: {str(e)}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete cache entry"""
        try:
            if key in self._cache:
                del self._cache[key]
                del self._expiry[key]
                self.logger.info(f"Cache deleted: {key[:20]}...")
                return True
            return False
        except Exception as e:
            self.logger.warning(f"Cache delete failed: {str(e)}")
            return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        try:
            count = len(self._cache)
            self._cache.clear()
            self._expiry.clear()
            self.hit_count = 0
            self.miss_count = 0
            self.logger.info(f"Cache cleared: {count} entries")
        except Exception as e:
            self.logger.warning(f"Cache clear failed: {str(e)}")
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count"""
        try:
            expired_keys = [
                key for key in self._cache 
                if self._is_expired(key)
            ]
            
            for key in expired_keys:
                del self._cache[key]
                del self._expiry[key]
            
            if expired_keys:
                self.logger.info(f"Cache cleanup: removed {len(expired_keys)} expired entries")
            
            return len(expired_keys)
        except Exception as e:
            self.logger.warning(f"Cache cleanup failed: {str(e)}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            total_requests = self.hit_count + self.miss_count
            hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
            
            # Count valid (non-expired) entries
            valid_entries = sum(
                1 for key in self._cache 
                if not self._is_expired(key)
            )
            
            return {
                'total_entries': len(self._cache),
                'valid_entries': valid_entries,
                'expired_entries': len(self._cache) - valid_entries,
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_rate_percent': round(hit_rate, 2),
                'memory_usage_estimate': len(str(self._cache))  # Rough estimate
            }
        except Exception as e:
            self.logger.warning(f"Cache stats failed: {str(e)}")
            return {}

# Global cache instance
cache = CacheService()

class FoodAnalysisCache:
    """Specialized caching for food analysis results"""
    
    @staticmethod
    def get_cache_key(food_description: str, analysis_method: str = "text") -> str:
        """Generate cache key for food analysis"""
        # Normalize food description
        normalized = food_description.lower().strip()
        # Remove common variations that shouldn't affect caching
        normalized = normalized.replace("1 ", "").replace("one ", "")
        
        key_data = f"{analysis_method}:{normalized}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @staticmethod
    def cache_food_analysis(food_description: str, analysis_result: Dict[str, Any], 
                           analysis_method: str = "text", ttl_hours: int = 24) -> None:
        """Cache food analysis result"""
        key = FoodAnalysisCache.get_cache_key(food_description, analysis_method)
        
        # Add metadata to cached result
        cached_result = {
            'result': analysis_result,
            'original_description': food_description,
            'analysis_method': analysis_method,
            'cached_at': datetime.utcnow().isoformat()
        }
        
        cache.set(key, cached_result, ttl_hours * 3600)
        caloria_logger.info(
            f"Cached food analysis: {food_description[:30]}...",
            {'cache_key': key, 'method': analysis_method}
        )
    
    @staticmethod
    def get_cached_food_analysis(food_description: str, 
                                analysis_method: str = "text") -> Optional[Dict[str, Any]]:
        """Get cached food analysis result"""
        key = FoodAnalysisCache.get_cache_key(food_description, analysis_method)
        cached_data = cache.get(key)
        
        if cached_data:
            caloria_logger.info(
                f"Cache hit for food analysis: {food_description[:30]}...",
                {'cache_key': key, 'method': analysis_method}
            )
            return cached_data['result']
        
        return None

class APIResponseCache:
    """Specialized caching for external API responses"""
    
    # Spoonacular API caching methods removed - now using Gemini Vision AI only
    
    @staticmethod
    def cache_google_cloud_response(service: str, params: Dict[str, Any], 
                                   response_data: Dict[str, Any], ttl_hours: int = 12) -> None:
        """Cache Google Cloud API response"""
        key = f"google_cloud:{service}:{APIResponseCache._hash_params(params)}"
        
        cached_response = {
            'data': response_data,
            'service': service,
            'params': params,
            'cached_at': datetime.utcnow().isoformat()
        }
        
        cache.set(key, cached_response, ttl_hours * 3600)
    
    @staticmethod
    def get_cached_google_cloud_response(service: str, 
                                        params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached Google Cloud API response"""
        key = f"google_cloud:{service}:{APIResponseCache._hash_params(params)}"
        cached_data = cache.get(key)
        
        if cached_data:
            return cached_data['data']
        
        return None
    
    @staticmethod
    def _hash_params(params: Dict[str, Any]) -> str:
        """Hash parameters for cache key"""
        return hashlib.md5(
            json.dumps(params, sort_keys=True, default=str).encode()
        ).hexdigest()

class DatabaseCache:
    """Specialized caching for database queries"""
    
    @staticmethod
    def cache_user_stats(user_id: int, stats_data: Dict[str, Any], 
                        ttl_minutes: int = 30) -> None:
        """Cache user statistics"""
        key = f"user_stats:{user_id}"
        cache.set(key, stats_data, ttl_minutes * 60)
    
    @staticmethod
    def get_cached_user_stats(user_id: int) -> Optional[Dict[str, Any]]:
        """Get cached user statistics"""
        key = f"user_stats:{user_id}"
        return cache.get(key)
    
    @staticmethod
    def cache_analytics_data(analytics_data: Dict[str, Any], 
                           ttl_minutes: int = 15) -> None:
        """Cache analytics dashboard data"""
        key = "analytics_dashboard"
        cache.set(key, analytics_data, ttl_minutes * 60)
    
    @staticmethod
    def get_cached_analytics_data() -> Optional[Dict[str, Any]]:
        """Get cached analytics data"""
        key = "analytics_dashboard"
        return cache.get(key)
    
    @staticmethod
    def invalidate_user_cache(user_id: int) -> None:
        """Invalidate all cache entries for a user"""
        keys_to_delete = [
            f"user_stats:{user_id}",
            f"daily_stats:{user_id}",
        ]
        
        for key in keys_to_delete:
            cache.delete(key)

# Decorator for caching function results
def cached(ttl_seconds: int = 3600, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}{func.__name__}:{cache._generate_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            try:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, ttl_seconds)
                return result
            except Exception as e:
                caloria_logger.error(f"Cached function error: {func.__name__}", e)
                raise
        
        # Add cache management methods to function
        wrapper.cache_clear = lambda: cache.delete(
            f"{key_prefix}{func.__name__}:{cache._generate_key()}"
        )
        wrapper.cache_info = lambda: cache.get_stats()
        
        return wrapper
    return decorator

# Cache warming functions
def warm_cache():
    """Warm up cache with commonly accessed data"""
    try:
        caloria_logger.info("Starting cache warm-up")
        
        # Warm up common food analysis results
        common_foods = [
            "apple", "banana", "chicken breast", "rice", "bread",
            "salad", "pasta", "pizza slice", "water", "coffee"
        ]
        
        # This would typically make actual API calls to warm the cache
        # For now, we'll just log the intention
        for food in common_foods:
            caloria_logger.info(f"Would warm cache for: {food}")
        
        caloria_logger.info("Cache warm-up completed")
        
    except Exception as e:
        caloria_logger.error("Cache warm-up failed", e)

# Background cache maintenance
def maintain_cache():
    """Perform cache maintenance tasks"""
    try:
        # Clean up expired entries
        expired_count = cache.cleanup_expired()
        
        # Log cache statistics
        stats = cache.get_stats()
        caloria_logger.log_performance_metric(
            "cache_hit_rate", 
            stats.get('hit_rate_percent', 0),
            '%',
            stats
        )
        
        # If hit rate is too low, consider warming cache
        if stats.get('hit_rate_percent', 0) < 30:
            caloria_logger.warning("Low cache hit rate detected", stats)
        
        return {
            'expired_cleaned': expired_count,
            'stats': stats
        }
        
    except Exception as e:
        caloria_logger.error("Cache maintenance failed", e)
        return {}

# Cache invalidation helpers
def invalidate_user_related_cache(user_id: int):
    """Invalidate all cache entries related to a user"""
    DatabaseCache.invalidate_user_cache(user_id)
    
    # Also invalidate analytics cache since user data changed
    cache.delete("analytics_dashboard")
    
    caloria_logger.info(f"Invalidated cache for user {user_id}")

def invalidate_food_analysis_cache(food_description: str):
    """Invalidate cached food analysis for specific food"""
    for method in ['text', 'image', 'voice']:
        key = FoodAnalysisCache.get_cache_key(food_description, method)
        cache.delete(key)
    
    caloria_logger.info(f"Invalidated food analysis cache for: {food_description}")

# Cache configuration for different environments
CACHE_CONFIG = {
    'development': {
        'default_ttl': 300,  # 5 minutes
        'food_analysis_ttl': 3600,  # 1 hour
        'api_response_ttl': 1800,  # 30 minutes
        'database_ttl': 300  # 5 minutes
    },
    'production': {
        'default_ttl': 3600,  # 1 hour
        'food_analysis_ttl': 86400,  # 24 hours
        'api_response_ttl': 21600,  # 6 hours
        'database_ttl': 1800  # 30 minutes
    }
} 