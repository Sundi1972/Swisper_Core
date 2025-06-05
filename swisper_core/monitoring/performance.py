"""
Performance monitoring utilities for Swisper Core
"""

import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta
from ..logging import get_logger

logger = get_logger(__name__)

class PerformanceCache:
    """Simple in-memory cache with TTL for performance optimization"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str, ttl_seconds: int = 3600) -> Optional[Any]:
        """Get cached value if not expired"""
        if key not in self._cache:
            return None
        
        if key in self._timestamps:
            age = time.time() - self._timestamps[key]
            if age > ttl_seconds:
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
                return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any):
        """Set cached value with current timestamp"""
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def clear(self):
        """Clear all cached values"""
        self._cache.clear()
        self._timestamps.clear()
    
    def size(self) -> int:
        """Get cache size"""
        return len(self._cache)

class PipelineTimer:
    """Context manager for timing pipeline operations"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.debug(f"Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - (self.start_time or 0)
        
        if exc_type is None:
            logger.info(f"Completed {self.operation_name} in {duration:.3f}s")
        else:
            logger.error(f"Failed {self.operation_name} after {duration:.3f}s: {exc_val}")
    
    @property
    def duration(self) -> float:
        """Get operation duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

class PerformanceMonitor:
    """Global performance monitoring and metrics collection"""
    
    def __init__(self):
        self.metrics = {}
        self.operation_counts = {}
        self.error_counts = {}
    
    def record_operation(self, operation: str, duration: float, success: bool = True):
        """Record operation timing and success/failure"""
        if operation not in self.metrics:
            self.metrics[operation] = []
        
        self.metrics[operation].append({
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "success": success
        })
        
        self.operation_counts[operation] = self.operation_counts.get(operation, 0) + 1
        
        if not success:
            self.error_counts[operation] = self.error_counts.get(operation, 0) + 1
        
        logger.debug(f"Recorded {operation}: {duration:.3f}s, success={success}")
    
    def get_operation_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for a specific operation"""
        if operation not in self.metrics:
            return {"error": "No data for operation"}
        
        durations = [m["duration"] for m in self.metrics[operation]]
        successes = [m["success"] for m in self.metrics[operation]]
        
        return {
            "operation": operation,
            "total_calls": len(durations),
            "success_rate": sum(successes) / len(successes) if successes else 0,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "error_count": self.error_counts.get(operation, 0)
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all operations"""
        return {op: self.get_operation_stats(op) for op in self.metrics.keys()}
    
    def clear_metrics(self):
        """Clear all collected metrics"""
        self.metrics.clear()
        self.operation_counts.clear()
        self.error_counts.clear()

performance_monitor = PerformanceMonitor()
attribute_cache = PerformanceCache()
pipeline_cache = PerformanceCache()

def create_cache_key(*args, **kwargs) -> str:
    """Create a cache key from arguments"""
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
    return "|".join(key_parts)

def timed_operation(operation_name: str):
    """Decorator to time and monitor operations"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with PipelineTimer(operation_name) as timer:
                try:
                    result = func(*args, **kwargs)
                    performance_monitor.record_operation(operation_name, timer.duration, True)
                    return result
                except Exception as e:
                    performance_monitor.record_operation(operation_name, timer.duration, False)
                    raise
        return wrapper
    return decorator

def cached_operation(cache: PerformanceCache, ttl_seconds: int = 3600):
    """Decorator to cache operation results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = create_cache_key(func.__name__, *args, **kwargs)
            
            cached_result = cache.get(cache_key, ttl_seconds)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            logger.debug(f"Cache miss for {func.__name__}")
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        return wrapper
    return decorator
