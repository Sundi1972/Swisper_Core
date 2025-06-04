import pytest
from unittest.mock import patch, MagicMock
from contract_engine.unified_session_store import UnifiedSessionStore
from contract_engine.contract_engine import ContractStateMachine
from contract_engine.context import SwisperContext

def test_atomic_state_save_with_rollback():
    """Test atomic state saving with rollback on failure"""
    store = UnifiedSessionStore()
    fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
    fsm.context = SwisperContext(session_id="test", current_state="refine_constraints")
    
    with patch.object(store, '_save_to_postgres_atomic') as mock_save:
        mock_save.return_value = False  # Simulate failure
        
        result = store.save_fsm_state("test_session", fsm)
        assert result is False
        mock_save.assert_called_once()

def test_search_to_refine_constraints_persistence():
    """Specifically test the problematic state transition"""
    store = UnifiedSessionStore()
    fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
    fsm.context = SwisperContext(session_id="test", current_state="search")
    
    fsm.context.update_state("refine_constraints")
    
    with patch.object(store, '_save_to_postgres_atomic') as mock_save, \
         patch.object(store, '_load_from_postgres_atomic') as mock_get:
        
        mock_save.return_value = True
        mock_get.return_value = fsm.context.to_dict()
        
        assert store.save_fsm_state("test_session", fsm)
        
        loaded_fsm = store.load_fsm_state("test_session")
        assert loaded_fsm.context.current_state == "refine_constraints"

def test_state_load_validation():
    """Test state loading with integrity validation"""
    store = UnifiedSessionStore()
    
    with patch.object(store, '_load_from_postgres_atomic') as mock_get:
        mock_get.return_value = {"session_id": None, "current_state": "invalid"}
        
        loaded_fsm = store.load_fsm_state("test_session")
        assert loaded_fsm is None

def test_concurrent_state_access():
    """Test thread-safe state access"""
    store = UnifiedSessionStore()
    
    test_context = {"session_id": "test", "current_state": "search"}
    store._cache_state("test_session", test_context)
    
    cached = store._get_cached_state("test_session")
    assert cached == test_context

def test_performance_metrics():
    """Test performance metrics collection"""
    store = UnifiedSessionStore()
    
    metrics = store.get_performance_metrics()
    assert "cache_size" in metrics
    assert "cache_hit_rate" in metrics

def test_fsm_state_validation():
    """Test FSM state validation"""
    store = UnifiedSessionStore()
    
    fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
    fsm.context = SwisperContext(session_id="test", current_state="search")
    assert store._validate_fsm_state(fsm) is True
    
    fsm.context = None
    assert store._validate_fsm_state(fsm) is False
    
    fsm.context = SwisperContext(session_id="test", current_state="")
    assert store._validate_fsm_state(fsm) is False

def test_context_dict_validation():
    """Test context dictionary validation"""
    store = UnifiedSessionStore()
    
    valid_context = {"session_id": "test", "current_state": "search"}
    assert store._validate_context_dict(valid_context) is True
    
    invalid_context = {"current_state": "search"}
    assert store._validate_context_dict(invalid_context) is False
    
    invalid_context = {"session_id": "test"}
    assert store._validate_context_dict(invalid_context) is False

def test_cache_ttl_expiration():
    """Test cache TTL expiration"""
    store = UnifiedSessionStore()
    store._cache_ttl = 0.1  # 100ms for testing
    
    test_context = {"session_id": "test", "current_state": "search"}
    store._cache_state("test_session", test_context)
    
    cached = store._get_cached_state("test_session")
    assert cached == test_context
    
    import time
    time.sleep(0.2)
    
    cached = store._get_cached_state("test_session")
    assert cached is None

def test_cache_size_limit():
    """Test cache size limiting"""
    store = UnifiedSessionStore()
    
    for i in range(1100):  # Exceeds 1000 limit
        test_context = {"session_id": f"test_{i}", "current_state": "search"}
        store._cache_state(f"test_session_{i}", test_context)
    
    assert len(store._cache) <= 1000
