import pytest
from unittest.mock import patch, MagicMock
import os
from swisper_core.clients import RedisClient

@patch('swisper_core.clients.redis.redis')
def test_redis_client_initialization(mock_redis):
    """Test Redis client initialization"""
    mock_pool = MagicMock()
    mock_client = MagicMock()
    mock_redis.ConnectionPool.return_value = mock_pool
    mock_redis.Redis.return_value = mock_client
    
    with patch.dict(os.environ, {
        'REDIS_HOST': 'test-host',
        'REDIS_PORT': '6380',
        'REDIS_DB': '1'
    }):
        redis_client = RedisClient()
        
        mock_redis.ConnectionPool.assert_called_with(
            host='test-host',
            port=6380,
            db=1,
            max_connections=20,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        mock_client.ping.assert_called_once()

@patch('swisper_core.clients.redis.redis')
def test_redis_client_get_client_success(mock_redis):
    """Test successful Redis client retrieval"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    
    redis_client = RedisClient()
    client = redis_client.get_client()
    
    assert client == mock_client

@patch('swisper_core.clients.redis.redis')
def test_redis_client_connection_failure(mock_redis):
    """Test Redis client connection failure handling"""
    mock_redis.Redis.side_effect = Exception("Connection failed")
    
    redis_client = RedisClient()
    
    with pytest.raises(Exception, match="Redis client not available"):
        redis_client.get_client()

@patch('swisper_core.clients.redis.redis')
def test_redis_client_availability_check(mock_redis):
    """Test Redis availability checking"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    
    redis_client = RedisClient()
    
    mock_client.ping.return_value = True
    assert redis_client.is_available() is True
    
    mock_client.ping.side_effect = Exception("Ping failed")
    assert redis_client.is_available() is False

@patch('swisper_core.clients.redis.redis')
def test_redis_client_get_info(mock_redis):
    """Test Redis info retrieval"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    mock_client.info.return_value = {
        "redis_version": "7.0.0",
        "used_memory": 1024,
        "connected_clients": 5
    }
    
    redis_client = RedisClient()
    info = redis_client.get_info()
    
    assert info["redis_version"] == "7.0.0"
    assert info["used_memory"] == 1024
    assert info["connected_clients"] == 5

@patch('swisper_core.clients.redis.redis')
def test_redis_client_memory_usage(mock_redis):
    """Test Redis memory usage metrics"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    mock_client.info.return_value = {
        "used_memory": 2048,
        "used_memory_human": "2K",
        "maxmemory": 4294967296,
        "maxmemory_human": "4G",
        "evicted_keys": 10,
        "expired_keys": 25
    }
    
    redis_client = RedisClient()
    memory_usage = redis_client.get_memory_usage()
    
    assert memory_usage["used_memory"] == 2048
    assert memory_usage["used_memory_human"] == "2K"
    assert memory_usage["maxmemory"] == 4294967296
    assert memory_usage["evicted_keys"] == 10

@patch('swisper_core.clients.redis.redis')
def test_redis_client_circuit_breaker_integration(mock_redis):
    """Test Redis client circuit breaker integration"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    
    redis_client = RedisClient()
    
    client = redis_client.get_client()
    assert client == mock_client

@patch('swisper_core.clients.redis.redis')
def test_redis_client_error_handling(mock_redis):
    """Test Redis client error handling"""
    mock_redis.Redis.side_effect = Exception("Redis connection error")
    
    redis_client = RedisClient()
    
    info = redis_client.get_info()
    assert info == {}
    
    memory_usage = redis_client.get_memory_usage()
    expected_keys = ['used_memory', 'maxmemory', 'evicted_keys', 'expired_keys']
    for key in expected_keys:
        assert key in memory_usage

@patch('swisper_core.clients.redis.redis')
def test_redis_client_default_environment_values(mock_redis):
    """Test Redis client with default environment values"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    
    with patch.dict(os.environ, {}, clear=True):
        redis_client = RedisClient()
        
        mock_redis.ConnectionPool.assert_called_with(
            host='localhost',
            port=6379,
            db=0,
            max_connections=20,
            retry_on_timeout=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
