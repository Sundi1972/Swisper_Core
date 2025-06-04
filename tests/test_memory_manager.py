import pytest
from unittest.mock import patch, MagicMock
from contract_engine.memory.memory_manager import MemoryManager
from contract_engine.context import SwisperContext

@patch('contract_engine.memory.memory_manager.BufferStore')
@patch('contract_engine.memory.memory_manager.SummaryStore')
def test_memory_manager_initialization(mock_summary_store, mock_buffer_store):
    """Test memory manager initialization"""
    memory_manager = MemoryManager(
        summary_trigger_tokens=2500,
        max_buffer_tokens=3500,
        max_buffer_messages=25
    )
    
    assert memory_manager.summary_trigger_tokens == 2500
    mock_buffer_store.assert_called_with(max_messages=25, max_tokens=3500)

@patch('contract_engine.memory.memory_manager.BufferStore')
@patch('contract_engine.memory.memory_manager.SummaryStore')
def test_memory_manager_add_message(mock_summary_store, mock_buffer_store):
    """Test adding message through memory manager"""
    mock_buffer_instance = MagicMock()
    mock_buffer_store.return_value = mock_buffer_instance
    mock_buffer_instance.add_message.return_value = True
    mock_buffer_instance.should_trigger_summary.return_value = False
    
    memory_manager = MemoryManager()
    message = {"role": "user", "content": "Hello"}
    
    result = memory_manager.add_message("test_session", message)
    
    assert result is True
    mock_buffer_instance.add_message.assert_called_with("test_session", message)

@patch('contract_engine.memory.memory_manager.BufferStore')
@patch('contract_engine.memory.memory_manager.SummaryStore')
def test_memory_manager_get_context(mock_summary_store, mock_buffer_store):
    """Test getting memory context"""
    mock_buffer_instance = MagicMock()
    mock_summary_instance = MagicMock()
    mock_buffer_store.return_value = mock_buffer_instance
    mock_summary_store.return_value = mock_summary_instance
    
    mock_buffer_instance.get_messages.return_value = [{"content": "test"}]
    mock_summary_instance.get_current_summary.return_value = "Current summary"
    mock_buffer_instance.get_buffer_info.return_value = {"total_tokens": 100, "message_count": 5}
    
    memory_manager = MemoryManager()
    context = memory_manager.get_context("test_session")
    
    assert context["buffer_messages"] == [{"content": "test"}]
    assert context["current_summary"] == "Current summary"
    assert context["total_tokens"] == 100
    assert context["message_count"] == 5

@patch('contract_engine.memory.memory_manager.BufferStore')
@patch('contract_engine.memory.memory_manager.SummaryStore')
def test_memory_manager_save_context(mock_summary_store, mock_buffer_store):
    """Test saving SwisperContext through memory manager"""
    mock_buffer_instance = MagicMock()
    mock_buffer_store.return_value = mock_buffer_instance
    mock_buffer_instance.add_message.return_value = True
    mock_buffer_instance.should_trigger_summary.return_value = False
    
    memory_manager = MemoryManager()
    context = SwisperContext(session_id="test", current_state="search")
    
    result = memory_manager.save_context("test_session", context)
    
    assert result is True
    mock_buffer_instance.add_message.assert_called()

@patch('contract_engine.memory.memory_manager.BufferStore')
@patch('contract_engine.memory.memory_manager.SummaryStore')
def test_memory_manager_summarization_trigger(mock_summary_store, mock_buffer_store):
    """Test automatic summarization triggering"""
    mock_buffer_instance = MagicMock()
    mock_summary_instance = MagicMock()
    mock_buffer_store.return_value = mock_buffer_instance
    mock_summary_store.return_value = mock_summary_instance
    
    mock_buffer_instance.add_message.return_value = True
    mock_buffer_instance.should_trigger_summary.return_value = True
    mock_buffer_instance.get_messages.return_value = [{"content": f"Message {i}"} for i in range(15)]
    
    memory_manager = MemoryManager()
    
    with patch.object(memory_manager, '_create_summary') as mock_create_summary:
        mock_create_summary.return_value = "Generated summary"
        
        with patch('contract_engine.memory.memory_manager.redis_client') as mock_redis_client:
            mock_client = MagicMock()
            mock_redis_client.get_client.return_value = mock_client
            
            memory_manager.add_message("test_session", {"content": "trigger message"})
            
            mock_summary_instance.add_summary.assert_called_with("test_session", "Generated summary")
            assert mock_client.lpop.call_count == 10

@patch('contract_engine.memory.memory_manager.BufferStore')
@patch('contract_engine.memory.memory_manager.SummaryStore')
def test_memory_manager_session_config(mock_summary_store, mock_buffer_store):
    """Test per-session configuration"""
    memory_manager = MemoryManager()
    
    config = {
        "summary_trigger_tokens": 2500,
        "max_buffer_tokens": 3500
    }
    
    memory_manager.set_session_config("test_session", config)
    
    retrieved_config = memory_manager._get_session_config("test_session")
    assert retrieved_config == config

@patch('contract_engine.memory.memory_manager.BufferStore')
@patch('contract_engine.memory.memory_manager.SummaryStore')
@patch('contract_engine.memory.memory_manager.redis_client')
def test_memory_manager_stats(mock_redis_client, mock_summary_store, mock_buffer_store):
    """Test memory statistics retrieval"""
    mock_buffer_instance = MagicMock()
    mock_summary_instance = MagicMock()
    mock_buffer_store.return_value = mock_buffer_instance
    mock_summary_store.return_value = mock_summary_instance
    
    mock_buffer_instance.get_buffer_info.return_value = {"message_count": 10}
    mock_summary_instance.get_summary_stats.return_value = {"summary_count": 3}
    mock_redis_client.get_memory_usage.return_value = {"used_memory": 1024}
    mock_redis_client.is_available.return_value = True
    
    memory_manager = MemoryManager()
    memory_manager.set_session_config("test_session", {"test": "config"})
    
    stats = memory_manager.get_memory_stats("test_session")
    
    assert "buffer" in stats
    assert "summary" in stats
    assert "redis_memory" in stats
    assert "session_config" in stats
    assert stats["is_redis_available"] is True

@patch('contract_engine.memory.memory_manager.BufferStore')
@patch('contract_engine.memory.memory_manager.SummaryStore')
def test_memory_manager_clear_session(mock_summary_store, mock_buffer_store):
    """Test clearing session memory"""
    mock_buffer_instance = MagicMock()
    mock_summary_instance = MagicMock()
    mock_buffer_store.return_value = mock_buffer_instance
    mock_summary_store.return_value = mock_summary_instance
    
    mock_buffer_instance.clear_buffer.return_value = True
    mock_summary_instance.clear_summaries.return_value = True
    
    memory_manager = MemoryManager()
    memory_manager.set_session_config("test_session", {"test": "config"})
    
    result = memory_manager.clear_session_memory("test_session")
    
    assert result is True
    mock_buffer_instance.clear_buffer.assert_called_with("test_session")
    mock_summary_instance.clear_summaries.assert_called_with("test_session")
    assert "test_session" not in memory_manager._session_configs

@patch('contract_engine.memory.memory_manager.redis_client')
def test_memory_manager_availability_check(mock_redis_client):
    """Test memory manager availability checking"""
    mock_redis_client.is_available.return_value = True
    
    memory_manager = MemoryManager()
    assert memory_manager.is_available() is True
    
    mock_redis_client.is_available.return_value = False
    assert memory_manager.is_available() is False

def test_memory_manager_summary_creation():
    """Test summary creation logic"""
    memory_manager = MemoryManager()
    
    messages = [
        {"content": "Hello world"},
        {"content": "How are you?"},
        {"content": "I'm looking for a laptop"}
    ]
    
    summary = memory_manager._create_summary(messages)
    assert "Hello world How are you? I'm looking for a laptop" in summary
    
    long_messages = [{"content": "Very long message " * 50}]
    long_summary = memory_manager._create_summary(long_messages)
    assert len(long_summary) <= 203
    assert long_summary.endswith("...")

@patch('contract_engine.memory.memory_manager.BufferStore')
@patch('contract_engine.memory.memory_manager.SummaryStore')
def test_memory_manager_error_handling(mock_summary_store, mock_buffer_store):
    """Test memory manager error handling"""
    mock_buffer_instance = MagicMock()
    mock_buffer_store.return_value = mock_buffer_instance
    mock_buffer_instance.add_message.side_effect = Exception("Buffer error")
    
    memory_manager = MemoryManager()
    
    result = memory_manager.add_message("test_session", {"content": "test"})
    assert result is False
    
    mock_buffer_instance.get_messages.side_effect = Exception("Get error")
    context = memory_manager.get_context("test_session")
    
    assert context["buffer_messages"] == []
    assert context["total_tokens"] == 0
