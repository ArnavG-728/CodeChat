# cache_manager.py - In-Memory Caching for Performance Optimization
"""
Simple in-memory cache to reduce database queries and improve response times.
Uses TTL (Time To Live) to ensure data freshness.
"""

import time
from typing import Any, Optional, Dict
from functools import wraps
import hashlib
import json
from .logger_config import setup_logger

logger = setup_logger(__name__)


class CacheManager:
    """Thread-safe in-memory cache with TTL support."""
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize cache manager.
        
        Args:
            default_ttl: Default time-to-live in seconds (5 minutes)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        logger.info(f"🚀 CacheManager initialized with TTL={default_ttl}s")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate a unique cache key from arguments."""
        key_data = {
            'args': args,
            'kwargs': kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if expired/not found
        """
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        if time.time() > entry['expires_at']:
            # Expired, remove from cache
            del self.cache[key]
            logger.debug(f"❌ Cache expired: {key[:16]}...")
            return None
        
        logger.debug(f"✅ Cache hit: {key[:16]}...")
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        ttl = ttl or self.default_ttl
        self.cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl,
            'created_at': time.time()
        }
        logger.debug(f"💾 Cached: {key[:16]}... (TTL={ttl}s)")
    
    def invalidate(self, key: str) -> None:
        """Remove specific key from cache."""
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"🗑️ Cache invalidated: {key[:16]}...")
    
    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys containing pattern.
        
        Args:
            pattern: String pattern to match
        
        Returns:
            Number of keys invalidated
        """
        keys_to_delete = [k for k in self.cache.keys() if pattern in k]
        for key in keys_to_delete:
            del self.cache[key]
        
        if keys_to_delete:
            logger.info(f"🗑️ Invalidated {len(keys_to_delete)} cache entries matching '{pattern}'")
        return len(keys_to_delete)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"🗑️ Cache cleared ({count} entries)")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = time.time()
        active_entries = sum(1 for entry in self.cache.values() if entry['expires_at'] > now)
        expired_entries = len(self.cache) - active_entries
        
        return {
            'total_entries': len(self.cache),
            'active_entries': active_entries,
            'expired_entries': expired_entries,
            'size_bytes': len(str(self.cache))
        }


# Global cache instance
_cache = CacheManager(default_ttl=300)  # 5 minutes default


def get_cache() -> CacheManager:
    """Get the global cache instance."""
    return _cache


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds (uses cache default if None)
        key_prefix: Prefix for cache key
    
    Usage:
        @cached(ttl=60, key_prefix="repo_stats")
        def get_repository_stats(repo_name):
            # Expensive operation
            return stats
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{cache._generate_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
