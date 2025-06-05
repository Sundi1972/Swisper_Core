import pytest
from unittest.mock import patch, MagicMock
import time
from contract_engine.memory import MemoryManager, BufferStore, SummaryStore
from swisper_core import SwisperContext

@patch('contract_engine.memory.redis_client.redis')
def test_memory_integration_full_flow(mock_redis):
    """Test complete memory management flow integration"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    mock_client.llen.return_value = 5
    mock_client.lrange.return_value = []
    mock_client.hgetall.return_value = {}
    mock_client.ttl.return_value = 3600
    
    memory_manager = MemoryManager(summary_trigger_tokens=100)
    
    messages = [
        {"role": "user", "content": "I want to buy a laptop"},
        {"role": "assistant", "content": "I can help you find a laptop"},
        {"role": "user", "content": "I need it for programming"}
    ]
    
    for message in messages:
        result = memory_manager.add_message("test_session", message)
        assert result is True
    
    context = memory_manager.get_context("test_session")
    assert "buffer_messages" in context
    assert "current_summary" in context

@patch('contract_engine.memory.redis_client.redis')
def test_memory_integration_summarization_flow(mock_redis):
    """Test automatic summarization integration"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    mock_client.llen.return_value = 15
    
    long_messages = [{"content": "Long message " * 20} for _ in range(15)]
    mock_client.lrange.return_value = [
        f'{{"version": "1.0", "timestamp": "2023-01-01T00:00:00", "data": {{"content": "Long message {i}"}}}}'.encode()
        for i in range(15)
    ]
    
    memory_manager = MemoryManager(summary_trigger_tokens=50)
    
    with patch.object(memory_manager.token_counter, 'should_trigger_summary') as mock_trigger:
        mock_trigger.return_value = True
        
        result = memory_manager.add_message("test_session", {"content": "trigger message"})
        assert result is True

@patch('contract_engine.memory.redis_client.redis')
@patch('contract_engine.memory.summary_store.postgres_session_store')
def test_memory_integration_persistence_fallback(mock_postgres_store, mock_redis):
    """Test Redis→PostgreSQL persistence fallback"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    mock_client.get.return_value = None
    mock_client.lrange.return_value = []
    mock_client.hgetall.return_value = {}
    mock_client.ttl.return_value = 3600
    
    with patch('contract_engine.memory.summary_store.redis_client') as mock_summary_redis:
        mock_summary_redis.get_client.return_value = mock_client
        
        mock_postgres_store.db_manager = MagicMock()
        mock_context_manager = MagicMock()
        mock_postgres_store.db_manager.get_session.return_value = mock_context_manager
        mock_session = MagicMock()
        mock_context_manager.__enter__.return_value = mock_session
        mock_query_result = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_query_result
        mock_query_result.short_summary = "Fallback summary"
        
        memory_manager = MemoryManager()
        context = memory_manager.get_context("test_session")
        
        assert context["current_summary"] == "Fallback summary"

@patch('contract_engine.memory.redis_client.redis')
def test_memory_integration_session_config(mock_redis):
    """Test per-session configuration integration"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    mock_client.llen.return_value = 5
    
    memory_manager = MemoryManager()
    
    session_config = {
        "summary_trigger_tokens": 2500,
        "max_buffer_tokens": 3500
    }
    
    memory_manager.set_session_config("test_session", session_config)
    
    with patch.object(memory_manager.buffer_store, 'should_trigger_summary') as mock_trigger:
        mock_trigger.return_value = False
        memory_manager._check_and_trigger_summary("test_session")
        mock_trigger.assert_called_with("test_session", 2500)

@patch('contract_engine.memory.redis_client.redis')
def test_memory_integration_error_resilience(mock_redis):
    """Test memory system error resilience"""
    mock_redis.Redis.side_effect = Exception("Redis unavailable")

    with patch('contract_engine.memory.buffer_store.redis_client') as mock_buffer_redis:
        mock_buffer_redis.get_client.side_effect = Exception("Redis unavailable")
        
        with patch('contract_engine.memory.summary_store.redis_client') as mock_summary_redis:
            mock_summary_redis.get_client.side_effect = Exception("Redis unavailable")
            
            memory_manager = MemoryManager()
            
            result = memory_manager.add_message("test_session", {"content": "test"})
            assert result is False
        
            context = memory_manager.get_context("test_session")
            assert context["buffer_messages"] == []
            assert context["current_summary"] is None

@patch('contract_engine.memory.redis_client.redis')
def test_memory_integration_context_serialization(mock_redis):
    """Test SwisperContext integration with memory system"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    mock_client.llen.return_value = 5

    with patch('contract_engine.memory.buffer_store.redis_client') as mock_buffer_redis:
        mock_buffer_redis.get_client.return_value = mock_client
        
        memory_manager = MemoryManager()

        context = SwisperContext(
            session_id="test_session",
            current_state="search",
            product_query="laptop",
            preferences={"budget": "1000"}
        )

        result = memory_manager.save_context("test_session", context)
        assert result is True

        mock_client.rpush.assert_called_once()

def test_memory_integration_performance_monitoring():
    """Test memory system performance monitoring"""
    memory_manager = MemoryManager()
    
    with patch.object(memory_manager.buffer_store, 'get_buffer_info') as mock_buffer_info:
        mock_buffer_info.return_value = {"message_count": 10, "total_tokens": 500}
        
        with patch.object(memory_manager.summary_store, 'get_summary_stats') as mock_summary_stats:
            mock_summary_stats.return_value = {"summary_count": 3}
            
            with patch('contract_engine.memory.memory_manager.redis_client') as mock_redis_client:
                mock_redis_client.get_memory_usage.return_value = {"used_memory": 1024}
                mock_redis_client.is_available.return_value = True
                
                stats = memory_manager.get_memory_stats("test_session")
                
                assert "buffer" in stats
                assert "summary" in stats
                assert "redis_memory" in stats
                assert stats["is_redis_available"] is True

@patch('contract_engine.memory.redis_client.redis')
def test_memory_integration_cleanup(mock_redis):
    """Test memory cleanup integration"""
    mock_client = MagicMock()
    mock_redis.Redis.return_value = mock_client
    
    memory_manager = MemoryManager()
    memory_manager.set_session_config("test_session", {"test": "config"})
    
    with patch.object(memory_manager.buffer_store, 'clear_buffer') as mock_clear_buffer:
        mock_clear_buffer.return_value = True
        
        with patch.object(memory_manager.summary_store, 'clear_summaries') as mock_clear_summaries:
            mock_clear_summaries.return_value = True
            
            result = memory_manager.clear_session_memory("test_session")
            assert result is True
            assert "test_session" not in memory_manager._session_configs

@patch('contract_engine.memory.memory_manager.milvus_semantic_store')
def test_memory_integration_semantic_memory(mock_milvus_store):
    """Test semantic memory integration with Memory Manager"""
    mock_milvus_store.add_memory.return_value = True
    mock_milvus_store.search_memories.return_value = [
        {"content": "User prefers gaming laptops", "metadata": {"type": "preference"}, "similarity_score": 0.9}
    ]
    
    memory_manager = MemoryManager()
    
    result = memory_manager.add_semantic_memory("user123", "Prefers gaming laptops", "preference")
    assert result is True
    
    semantic_memories = memory_manager.get_semantic_context("user123", "laptop preferences")
    assert len(semantic_memories) == 1
    assert "gaming laptops" in semantic_memories[0]["content"]

@patch('contract_engine.memory.memory_manager.milvus_semantic_store')
def test_memory_integration_enhanced_context(mock_milvus_store):
    """Test enhanced context with semantic memories"""
    mock_milvus_store.search_memories.return_value = [
        {"content": "Budget under $1000", "metadata": {"type": "constraint"}, "similarity_score": 0.8}
    ]
    
    memory_manager = MemoryManager()
    
    with patch.object(memory_manager, 'get_context') as mock_get_context:
        mock_get_context.return_value = {
            "buffer_messages": [],
            "current_summary": "Previous conversation summary",
            "total_tokens": 100
        }
        
        enhanced_context = memory_manager.get_enhanced_context("session123", "user123", "laptop shopping")
        
        assert "semantic_memories" in enhanced_context
        assert len(enhanced_context["semantic_memories"]) == 1
        assert "Budget under $1000" in enhanced_context["semantic_memories"][0]["content"]

def test_t5_summarization_integration():
    """Test T5 summarization integration with Memory Manager"""
    memory_manager = MemoryManager()
    
    messages = [
        {"content": "I want to buy a laptop for programming"},
        {"content": "My budget is around 1000 dollars"},
        {"content": "I prefer something lightweight"}
    ]
    
    with patch('contract_engine.pipelines.rolling_summariser.summarize_messages') as mock_summarize:
        mock_summarize.return_value = "User seeks programming laptop under $1000, prefers lightweight"
        
        summary = memory_manager._create_summary(messages)
        
        assert "programming laptop" in summary
        assert "$1000" in summary
        assert "lightweight" in summary
        mock_summarize.assert_called_once_with(messages)

def test_t5_summarization_fallback():
    """Test T5 summarization fallback in Memory Manager"""
    memory_manager = MemoryManager()
    
    messages = [
        {"content": "Test message " * 50}
    ]
    
    with patch('contract_engine.pipelines.rolling_summariser.summarize_messages') as mock_summarize:
        mock_summarize.side_effect = Exception("T5 failed")
        
        summary = memory_manager._create_summary(messages)
        
        assert summary.endswith("...")
        assert len(summary) <= 203
