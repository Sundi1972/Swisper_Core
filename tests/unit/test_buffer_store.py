import pytest
from unittest.mock import patch, MagicMock
from contract_engine.memory.buffer_store import BufferStore

@patch('contract_engine.memory.buffer_store.redis_client')
def test_buffer_store_add_message(mock_redis_client):
    """Test adding messages to buffer store"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    mock_client.llen.return_value = 5
    
    buffer_store = BufferStore(max_messages=30, max_tokens=4000)
    
    message = {"role": "user", "content": "Hello world"}
    result = buffer_store.add_message("test_session", message)
    
    assert result is True
    mock_client.rpush.assert_called_once()
    mock_client.expire.assert_called()

@patch('contract_engine.memory.buffer_store.redis_client')
def test_buffer_store_get_messages(mock_redis_client):
    """Test retrieving messages from buffer store"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    
    serialized_messages = [
        b'{"version": "1.0", "timestamp": "2023-01-01T00:00:00", "data": {"role": "user", "content": "Hello"}}',
        b'{"version": "1.0", "timestamp": "2023-01-01T00:01:00", "data": {"role": "assistant", "content": "Hi"}}'
    ]
    mock_client.lrange.return_value = serialized_messages
    
    buffer_store = BufferStore()
    messages = buffer_store.get_messages("test_session")
    
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

@patch('contract_engine.memory.buffer_store.redis_client')
def test_buffer_store_message_limit_enforcement(mock_redis_client):
    """Test buffer store enforces message limits"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    mock_client.llen.return_value = 35
    
    buffer_store = BufferStore(max_messages=30)
    buffer_store.add_message("test_session", {"content": "test"})
    
    mock_client.lpop.assert_called()

@patch('contract_engine.memory.buffer_store.redis_client')
def test_buffer_store_token_limit_enforcement(mock_redis_client):
    """Test buffer store enforces token limits"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    mock_client.llen.return_value = 10
    
    buffer_store = BufferStore(max_tokens=100)
    
    with patch.object(buffer_store, 'get_messages') as mock_get_messages:
        mock_get_messages.return_value = [
            {"content": "Very long message " * 50}
        ]
        
        with patch.object(buffer_store.token_counter, 'get_overflow_messages') as mock_overflow:
            mock_overflow.return_value = [{"content": "overflow"}]
            
            buffer_store.add_message("test_session", {"content": "new message"})
            
            mock_client.lpop.assert_called()

@patch('contract_engine.memory.buffer_store.redis_client')
def test_buffer_store_ttl_handling(mock_redis_client):
    """Test buffer store TTL handling"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    mock_client.llen.return_value = 5
    
    buffer_store = BufferStore(ttl_seconds=3600)
    buffer_store.add_message("test_session", {"content": "test"})
    
    expire_calls = [call for call in mock_client.expire.call_args_list]
    assert len(expire_calls) >= 1
    assert expire_calls[0][0][1] == 3600

@patch('contract_engine.memory.buffer_store.redis_client')
def test_buffer_store_info_retrieval(mock_redis_client):
    """Test buffer store info retrieval"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    mock_client.llen.return_value = 10
    mock_client.hgetall.return_value = {b"last_updated": b"1234567890"}
    mock_client.ttl.return_value = 3600
    
    buffer_store = BufferStore()
    
    with patch.object(buffer_store, 'get_messages') as mock_get_messages:
        mock_get_messages.return_value = [{"content": "test"}]
        
        info = buffer_store.get_buffer_info("test_session")
        
        assert "message_count" in info
        assert "total_tokens" in info
        assert "ttl_remaining" in info

@patch('contract_engine.memory.buffer_store.redis_client')
def test_buffer_store_clear_buffer(mock_redis_client):
    """Test buffer store clear functionality"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    
    buffer_store = BufferStore()
    result = buffer_store.clear_buffer("test_session")
    
    assert result is True
    mock_client.delete.assert_called()

@patch('contract_engine.memory.buffer_store.redis_client')
def test_buffer_store_summary_trigger_check(mock_redis_client):
    """Test buffer store summary trigger checking"""
    buffer_store = BufferStore()
    
    with patch.object(buffer_store, 'get_messages') as mock_get_messages:
        mock_get_messages.return_value = [{"content": "short"}]
        
        with patch.object(buffer_store.token_counter, 'should_trigger_summary') as mock_trigger:
            mock_trigger.return_value = True
            
            result = buffer_store.should_trigger_summary("test_session", 3000)
            assert result is True
            mock_trigger.assert_called_with([{"content": "short"}], 3000)

@patch('contract_engine.memory.buffer_store.redis_client')
def test_buffer_store_error_handling(mock_redis_client):
    """Test buffer store error handling"""
    mock_redis_client.get_client.side_effect = Exception("Redis unavailable")
    
    buffer_store = BufferStore()
    
    result = buffer_store.add_message("test_session", {"content": "test"})
    assert result is False
    
    messages = buffer_store.get_messages("test_session")
    assert messages == []
    
    info = buffer_store.get_buffer_info("test_session")
    assert info == {}
