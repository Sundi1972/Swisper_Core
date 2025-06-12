"""
Redis client utilities for Swisper Core
"""

import os
from typing import Optional
from ..logging import get_logger

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    
    class MockRedis:
        def ConnectionPool(self, **kwargs):
            return None
        def Redis(self, **kwargs):
            return None
    
    redis = MockRedis()

logger = get_logger(__name__)

class RedisClient:
    """Redis client with connection pooling and circuit breaker"""
    
    def __init__(self):
        self.host = os.getenv('REDIS_HOST', 'localhost')
        self.port = int(os.getenv('REDIS_PORT', 6379))
        self.db = int(os.getenv('REDIS_DB', 0))
        self.password = os.getenv('REDIS_PASSWORD')
        self.pool: Optional[object] = None
        self.redis: Optional[object] = None
        
        if not REDIS_AVAILABLE:
            logger.warning("Redis module not available - RedisClient will not function")
            return
        
        try:
            self.pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                max_connections=20
            )
            
            self.redis = redis.Redis(connection_pool=self.pool)
            self.redis.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None
    
    def get_client(self):
        """Get Redis client instance"""
        if not REDIS_AVAILABLE or not self.redis:
            raise Exception("Redis client not available")
        return self.redis
    
    def health_check(self) -> bool:
        """Check Redis connection health"""
        if not REDIS_AVAILABLE or not self.redis:
            return False
        try:
            self.redis.ping()
            return True
        except Exception:
            return False
