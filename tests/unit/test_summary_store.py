import pytest
from unittest.mock import patch, MagicMock
from contract_engine.memory.summary_store import SummaryStore

@patch('contract_engine.memory.summary_store.redis_client')
@patch('contract_engine.memory.summary_store.postgres_session_store')
def test_summary_store_add_summary(mock_postgres_store, mock_redis_client):
    """Test adding summary to summary store"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    
    mock_pipeline = MagicMock()
    mock_client.pipeline.return_value = mock_pipeline
    mock_pipeline.rpush.return_value = mock_pipeline
    mock_pipeline.expire.return_value = mock_pipeline
    mock_pipeline.set.return_value = mock_pipeline
    mock_pipeline.execute.return_value = [1, 1, 1, 1]
    
    mock_client.llen.return_value = 5
    
    summary_store = SummaryStore()
    result = summary_store.add_summary("test_session", "This is a summary")
    
    assert result is True
    mock_pipeline.rpush.assert_called()
    mock_pipeline.set.assert_called()
    mock_postgres_store.db_manager.get_session.assert_called()

@patch('contract_engine.memory.summary_store.redis_client')
def test_summary_store_get_current_summary(mock_redis_client):
    """Test retrieving current summary"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    mock_client.get.return_value = b"Current summary text"
    
    summary_store = SummaryStore()
    summary = summary_store.get_current_summary("test_session")
    
    assert summary == "Current summary text"

@patch('contract_engine.memory.summary_store.redis_client')
@patch('contract_engine.memory.summary_store.postgres_session_store')
def test_summary_store_postgres_fallback(mock_postgres_store, mock_redis_client):
    """Test PostgreSQL fallback when Redis unavailable"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    mock_client.get.return_value = None
    
    mock_postgres_store.db_manager = MagicMock()
    mock_context_manager = MagicMock()
    mock_postgres_store.db_manager.get_session.return_value = mock_context_manager
    mock_session = MagicMock()
    mock_context_manager.__enter__.return_value = mock_session
    mock_query_result = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_query_result
    mock_query_result.short_summary = "Fallback summary"
    
    summary_store = SummaryStore()
    summary = summary_store.get_current_summary("test_session")
    
    assert summary == "Fallback summary"
    mock_client.setex.assert_called()

@patch('contract_engine.memory.summary_store.redis_client')
def test_summary_store_get_history(mock_redis_client):
    """Test retrieving summary history"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    
    serialized_summaries = [
        b'{"version": "1.0", "timestamp": "2023-01-01T00:00:00", "data": {"text": "Summary 1", "timestamp": 1234567890}}',
        b'{"version": "1.0", "timestamp": "2023-01-01T00:01:00", "data": {"text": "Summary 2", "timestamp": 1234567891}}'
    ]
    mock_client.lrange.return_value = serialized_summaries
    
    summary_store = SummaryStore()
    history = summary_store.get_summary_history("test_session", limit=5)
    
    assert len(history) == 2
    assert history[0]["text"] == "Summary 1"
    assert history[1]["text"] == "Summary 2"

@patch('contract_engine.memory.summary_store.redis_client')
def test_summary_store_manage_count(mock_redis_client):
    """Test summary count management and merging"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    mock_client.llen.return_value = 10
    
    old_summaries = [
        b'{"version": "1.0", "timestamp": "2023-01-01T00:00:00", "data": {"text": "Old summary 1", "timestamp": 1234567890}}',
        b'{"version": "1.0", "timestamp": "2023-01-01T00:01:00", "data": {"text": "Old summary 2", "timestamp": 1234567891}}',
        b'{"version": "1.0", "timestamp": "2023-01-01T00:02:00", "data": {"text": "Old summary 3", "timestamp": 1234567892}}'
    ]
    mock_client.lpop.side_effect = old_summaries
    
    summary_store = SummaryStore()
    
    with patch.object(summary_store, 'add_summary') as mock_add_summary:
        summary_store._manage_summary_count("test_session", max_summaries=8)
        
        mock_add_summary.assert_called()
        merged_call = mock_add_summary.call_args
        assert "Old summary 1 Old summary 2 Old summary 3" in merged_call[0][1]

@patch('contract_engine.memory.summary_store.redis_client')
def test_summary_store_stats(mock_redis_client):
    """Test summary statistics retrieval"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    mock_client.llen.return_value = 5
    mock_client.ttl.return_value = 3600
    
    summary_store = SummaryStore()
    
    with patch.object(summary_store, 'get_current_summary') as mock_get_summary:
        mock_get_summary.return_value = "Current summary text"
        
        stats = summary_store.get_summary_stats("test_session")
        
        assert stats["summary_count"] == 5
        assert stats["current_summary_length"] == len("Current summary text")
        assert stats["redis_ttl"] == 3600

@patch('contract_engine.memory.summary_store.redis_client')
def test_summary_store_clear_summaries(mock_redis_client):
    """Test clearing all summaries"""
    mock_client = MagicMock()
    mock_redis_client.get_client.return_value = mock_client
    
    mock_pipeline = MagicMock()
    mock_client.pipeline.return_value = mock_pipeline
    mock_pipeline.delete.return_value = mock_pipeline
    mock_pipeline.execute.return_value = [1, 1]

    summary_store = SummaryStore()
    result = summary_store.clear_summaries("test_session")

    assert result is True
    mock_pipeline.delete.assert_called()

def test_summary_store_merge_logic():
    """Test summary merging logic"""
    summary_store = SummaryStore()
    
    summaries = ["Summary 1", "Summary 2", "Summary 3"]
    merged = summary_store._merge_summaries(summaries)
    
    assert merged == "Summary 1 Summary 2 Summary 3"
    
    long_summaries = ["Very long summary " * 50, "Another long summary " * 50]
    merged_long = summary_store._merge_summaries(long_summaries)
    
    assert len(merged_long) <= 503
    assert merged_long.endswith("...")

@patch('contract_engine.memory.summary_store.redis_client')
def test_summary_store_error_handling(mock_redis_client):
    """Test summary store error handling"""
    mock_redis_client.get_client.side_effect = Exception("Redis unavailable")
    
    summary_store = SummaryStore()
    
    result = summary_store.add_summary("test_session", "Test summary")
    assert result is False
    
    summary = summary_store.get_current_summary("test_session")
    assert summary is None
    
    history = summary_store.get_summary_history("test_session")
    assert history == []
    
    stats = summary_store.get_summary_stats("test_session")
    assert stats == {}
