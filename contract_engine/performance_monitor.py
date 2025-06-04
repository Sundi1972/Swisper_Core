"""
Performance monitoring and optimization utilities for Swisper Core pipelines.

Provides caching, timing, and performance tracking capabilities for pipeline components.
"""
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from functools import wraps
import hashlib
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PerformanceCache:
    """Thread-safe cache with TTL support for pipeline results."""
    
    def __init__(self, default_ttl_minutes: int = 30):
        self._cache = {}
        self._timestamps = {}
        self.default_ttl = timedelta(minutes=default_ttl_minutes)
    
    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        if key not in self._timestamps:
            return True
        return datetime.now() - self._timestamps[key] > self.default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache and not self._is_expired(key):
            logger.debug(f"Cache hit for key: {key[:50]}...")
            return self._cache[key]
        elif key in self._cache:
            del self._cache[key]
            del self._timestamps[key]
            logger.debug(f"Cache expired for key: {key[:50]}...")
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set cached value with timestamp."""
        self._cache[key] = value
        self._timestamps[key] = datetime.now()
        logger.debug(f"Cache set for key: {key[:50]}...")
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._timestamps.clear()
        logger.info("Performance cache cleared")
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)


class PipelineTimer:
    """Context manager for timing pipeline operations."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.debug(f"Starting timer for: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        logger.info(f"Operation '{self.operation_name}' completed in {duration:.3f}s")
        
        PerformanceMonitor.record_operation(self.operation_name, duration)
    
    @property
    def duration(self) -> float:
        """Get operation duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0


class PerformanceMonitor:
    """Global performance monitoring and metrics collection."""
    
    _metrics = {}
    _operation_counts = {}
    
    @classmethod
    def record_operation(cls, operation_name: str, duration: float) -> None:
        """Record operation timing metrics."""
        if operation_name not in cls._metrics:
            cls._metrics[operation_name] = []
            cls._operation_counts[operation_name] = 0
        
        cls._metrics[operation_name].append(duration)
        cls._operation_counts[operation_name] += 1
        
        if len(cls._metrics[operation_name]) > 100:
            cls._metrics[operation_name] = cls._metrics[operation_name][-100:]
    
    @classmethod
    def get_stats(cls, operation_name: str) -> Dict[str, float]:
        """Get performance statistics for an operation."""
        if operation_name not in cls._metrics or not cls._metrics[operation_name]:
            return {}
        
        durations = cls._metrics[operation_name]
        return {
            "count": len(durations),
            "total_count": cls._operation_counts.get(operation_name, 0),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "total_duration": sum(durations)
        }
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, float]]:
        """Get performance statistics for all operations."""
        return {op: cls.get_stats(op) for op in cls._metrics.keys()}
    
    @classmethod
    def clear_metrics(cls) -> None:
        """Clear all performance metrics."""
        cls._metrics.clear()
        cls._operation_counts.clear()
        logger.info("Performance metrics cleared")


def create_cache_key(*args, **kwargs) -> str:
    """Create a consistent cache key from arguments."""
    key_data = {
        "args": [str(arg) for arg in args],
        "kwargs": {k: str(v) for k, v in sorted(kwargs.items())}
    }
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_string.encode()).hexdigest()


def timed_operation(operation_name: str):
    """Decorator to automatically time function execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with PipelineTimer(operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def cached_operation(cache: PerformanceCache, key_func=None):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = create_cache_key(*args, **kwargs)
            
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        return wrapper
    return decorator


attribute_cache = PerformanceCache(default_ttl_minutes=60)  # Longer TTL for attributes
pipeline_cache = PerformanceCache(default_ttl_minutes=30)   # Standard TTL for pipeline results
