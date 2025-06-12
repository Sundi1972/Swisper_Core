import logging
from typing import Optional, Any
import os
from swisper_core import get_logger


try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    
    class MockRedis:
        def __init__(self, *args, **kwargs): pass
        def ping(self): pass
        def info(self): return {}
    
    class MockConnectionPool:
        def __init__(self, *args, **kwargs): pass
    
    class MockRedisModule:
        Redis = MockRedis
        ConnectionPool = MockConnectionPool
    
    redis = MockRedisModule()

try:
    from .circuit_breaker import redis_circuit_breaker
except ImportError:
    def redis_circuit_breaker(func):
        return func

class RedisClient:
    """Redis client with connection pooling and circuit breaker"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._pool = None
        self._client = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize Redis connection with pooling"""
        if not REDIS_AVAILABLE:
            self.logger.warning("Redis not available, using fallback mode")
            self._client = None
            return
            
        try:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_db = int(os.getenv("REDIS_DB", "0"))
            
            self._pool = redis.ConnectionPool(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                max_connections=20,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            self._client = redis.Redis(connection_pool=self._pool)
            
            self._client.ping()
            self.logger.info(f"Redis client initialized: {redis_host}:{redis_port}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Redis client: {e}")
            self._client = None
    
    @redis_circuit_breaker
    def get_client(self):
        """Get Redis client with circuit breaker protection"""
        if self._client is None:
            self._initialize_connection()
        
        if self._client is None:
            raise Exception("Redis client not available")
        
        return self._client
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        try:
            client = self.get_client()
            client.ping()
            return True
        except:
            return False
    
    def get_info(self):
        """Get Redis server info for monitoring"""
        try:
            client = self.get_client()
            return client.info()
        except Exception as e:
            self.logger.error(f"Failed to get Redis info: {e}")
            return {}
    
    def get_memory_usage(self) -> dict:
        """Get Redis memory usage metrics"""
        try:
            info = self.get_info()
            return {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "maxmemory": info.get("maxmemory", 0),
                "maxmemory_human": info.get("maxmemory_human", "0B"),
                "evicted_keys": info.get("evicted_keys", 0),
                "expired_keys": info.get("expired_keys", 0)
            }
        except Exception as e:
            self.logger.error(f"Failed to get Redis memory usage: {e}")
            return {}

redis_client = RedisClient()
