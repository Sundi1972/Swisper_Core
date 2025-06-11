import pytest
import time
from unittest.mock import patch, MagicMock
from contract_engine.memory import MemoryManager, BufferStore, TokenCounter

@patch('contract_engine.memory.buffer_store.redis_client')
def test_buffer_store_read_latency_sla(mock_redis_client):
    """Test BufferStore read operations meet <5ms SLA"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    mock_client.lrange.return_value = [
        b'{"version": "1.0", "timestamp": "2023-01-01T00:00:00", "data": {"content": "test"}}'
    ]
    mock_client.llen.return_value = 1
    mock_client.hgetall.return_value = {}
    mock_client.ttl.return_value = 3600

    buffer_store = BufferStore()

    start_time = time.time()
    messages = buffer_store.get_messages("test_session")
    end_time = time.time()

    latency_ms = (end_time - start_time) * 1000
    assert latency_ms < 5.0, f"Read latency {latency_ms}ms exceeds 5ms SLA"
    assert len(messages) == 1

@patch('contract_engine.memory.redis_client.redis')
def test_buffer_store_write_latency_sla(mock_redis):
    """Test BufferStore write operations meet <10ms SLA"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    mock_client.llen.return_value = 5
    
    buffer_store = BufferStore()
    message = {"role": "user", "content": "test message"}
    
    start_time = time.time()
    result = buffer_store.add_message("test_session", message)
    end_time = time.time()
    
    latency_ms = (end_time - start_time) * 1000
    assert latency_ms < 10.0, f"Write latency {latency_ms}ms exceeds 10ms SLA"
    assert result is True

def test_token_counter_performance():
    """Test TokenCounter performance for batch operations"""
    counter = TokenCounter()
    
    large_batch = [
        {"content": "This is a test message for performance testing " * 10}
        for _ in range(100)
    ]
    
    start_time = time.time()
    total_tokens = counter.count_batch_tokens(large_batch)
    end_time = time.time()
    
    latency_ms = (end_time - start_time) * 1000
    assert latency_ms < 50.0, f"Token counting latency {latency_ms}ms too high"
    assert total_tokens > 0

@patch('contract_engine.memory.redis_client.redis')
def test_memory_manager_context_packaging_sla(mock_redis):
    """Test MemoryManager context packaging meets <50ms SLA"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    mock_client.lrange.return_value = [
        f'{{"version": "1.0", "timestamp": "2023-01-01T00:00:00", "data": {{"content": "Message {i}"}}}}'.encode()
        for i in range(30)
    ]
    mock_client.get.return_value = b"Current summary text"
    mock_client.llen.return_value = 30
    mock_client.hgetall.return_value = {b"last_updated": b"1234567890"}
    mock_client.ttl.return_value = 3600
    
    memory_manager = MemoryManager()
    
    start_time = time.time()
    context = memory_manager.get_context("test_session")
    end_time = time.time()
    
    latency_ms = (end_time - start_time) * 1000
    assert latency_ms < 50.0, f"Context packaging latency {latency_ms}ms exceeds 50ms SLA"
    assert "buffer_messages" in context

@patch('contract_engine.memory.redis_client.redis')
def test_summarization_performance_sla(mock_redis):
    """Test summarization performance meets <200ms SLA"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    mock_client.llen.return_value = 15
    mock_client.lrange.return_value = [
        f'{{"version": "1.0", "timestamp": "2023-01-01T00:00:00", "data": {{"content": "Message {i}"}}}}'.encode()
        for i in range(15)
    ]
    
    memory_manager = MemoryManager()
    
    start_time = time.time()
    memory_manager._trigger_summarization("test_session")
    end_time = time.time()
    
    latency_ms = (end_time - start_time) * 1000
    assert latency_ms < 200.0, f"Summarization latency {latency_ms}ms exceeds 200ms SLA"

def test_memory_manager_concurrent_operations():
    """Test memory manager performance under concurrent load"""
    memory_manager = MemoryManager()
    
    with patch.object(memory_manager.buffer_store, 'add_message') as mock_add:
        mock_add.return_value = True
        
        with patch.object(memory_manager.buffer_store, 'should_trigger_summary') as mock_trigger:
            mock_trigger.return_value = False
            
            start_time = time.time()
            
            for i in range(100):
                result = memory_manager.add_message(f"session_{i % 10}", {"content": f"Message {i}"})
                assert result is True
            
            end_time = time.time()
            
            total_latency_ms = (end_time - start_time) * 1000
            avg_latency_ms = total_latency_ms / 100
            
            assert avg_latency_ms < 5.0, f"Average operation latency {avg_latency_ms}ms too high"

@patch('contract_engine.memory.redis_client.redis')
def test_buffer_overflow_performance(mock_redis):
    """Test buffer overflow handling performance"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    mock_client.llen.return_value = 35
    
    buffer_store = BufferStore(max_messages=30)
    
    start_time = time.time()
    buffer_store._enforce_limits("test_session")
    end_time = time.time()
    
    latency_ms = (end_time - start_time) * 1000
    assert latency_ms < 10.0, f"Buffer overflow handling latency {latency_ms}ms too high"

def test_serialization_performance():
    """Test message serialization performance"""
    from contract_engine.memory.message_serializer import MessageSerializer
    
    serializer = MessageSerializer()
    
    large_message = {
        "role": "user",
        "content": "Large message content " * 100,
        "metadata": {"key": "value"} 
    }
    
    start_time = time.time()
    for _ in range(100):
        serialized = serializer.serialize_message(large_message)
        deserialized = serializer.deserialize_message(serialized)
        assert deserialized["content"] == large_message["content"]
    end_time = time.time()
    
    total_latency_ms = (end_time - start_time) * 1000
    avg_latency_ms = total_latency_ms / 100
    
    assert avg_latency_ms < 1.0, f"Serialization latency {avg_latency_ms}ms too high"

@patch('contract_engine.memory.redis_client.redis')
def test_memory_stats_collection_performance(mock_redis):
    """Test memory statistics collection performance"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    mock_client.llen.return_value = 10
    mock_client.hgetall.return_value = {}
    mock_client.ttl.return_value = 3600
    mock_client.info.return_value = {"used_memory": 1024}
    
    memory_manager = MemoryManager()
    
    start_time = time.time()
    stats = memory_manager.get_memory_stats("test_session")
    end_time = time.time()
    
    latency_ms = (end_time - start_time) * 1000
    assert latency_ms < 15.0, f"Stats collection latency {latency_ms}ms too high"
    assert "buffer" in stats
