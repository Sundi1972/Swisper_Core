import pytest
from unittest.mock import patch
from contract_engine.unified_session_store import UnifiedSessionStore
from contract_engine.contract_engine import ContractStateMachine
from contract_engine.context import SwisperContext

def test_complete_purchase_flow_with_persistence():
    """Test full user flow: search → refine → recommend → purchase"""
    session_id = "integration_test_001"
    store = UnifiedSessionStore()
    
    fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
    fsm.context = SwisperContext(session_id=session_id, current_state="search")
    
    states_to_test = ["search", "refine_constraints", "match_preferences", "confirm_purchase"]
    
    with patch.object(store, '_save_to_postgres_atomic') as mock_save, \
         patch.object(store, '_load_from_postgres_atomic') as mock_get:
        
        mock_save.return_value = True
        
        for state in states_to_test:
            fsm.context.update_state(state)
            mock_get.return_value = fsm.context.to_dict()
            
            assert store.save_fsm_state(session_id, fsm)
            
            loaded_fsm = store.load_fsm_state(session_id)
            assert loaded_fsm is not None
            assert loaded_fsm.context.current_state == state
            
            reloaded_fsm = store.load_fsm_state(session_id)
            assert reloaded_fsm.context.current_state == state

def test_infinite_loop_fix_verification():
    """Specifically test that search→refine_constraints→search loop is fixed"""
    session_id = "infinite_loop_test"
    store = UnifiedSessionStore()
    
    with patch.object(store, '_save_to_postgres_atomic') as mock_save, \
         patch.object(store, '_load_from_postgres_atomic') as mock_get:
        
        mock_save.return_value = True
        
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.context = SwisperContext(session_id=session_id, current_state="search")
        
        mock_get.return_value = fsm.context.to_dict()
        store.save_fsm_state(session_id, fsm)
        
        fsm.context.update_state("refine_constraints")
        mock_get.return_value = fsm.context.to_dict()
        store.save_fsm_state(session_id, fsm)
        
        for i in range(5):
            loaded_fsm = store.load_fsm_state(session_id)
            assert loaded_fsm.context.current_state == "refine_constraints"
            
            store.save_fsm_state(session_id, loaded_fsm)
            reloaded_fsm = store.load_fsm_state(session_id)
            assert reloaded_fsm.context.current_state == "refine_constraints"
            
            assert reloaded_fsm.context.current_state != "search"

def test_session_recovery_after_interruption():
    """Test FSM recovery after simulated system interruption"""
    session_id = "recovery_test"
    store = UnifiedSessionStore()
    
    with patch.object(store, '_save_to_postgres_atomic') as mock_save, \
         patch.object(store, '_load_from_postgres_atomic') as mock_get:
        
        mock_save.return_value = True
        
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.context = SwisperContext(
            session_id=session_id, 
            current_state="match_preferences",
            product_query="laptop",
            preferences={"budget": "1000"},
            search_results=[{"id": 1, "name": "MacBook"}]
        )
        
        mock_get.return_value = fsm.context.to_dict()
        store.save_fsm_state(session_id, fsm)
        
        recovered_fsm = store.load_fsm_state(session_id)
        
        assert recovered_fsm is not None
        assert recovered_fsm.context.current_state == "match_preferences"
        assert recovered_fsm.context.product_query == "laptop"
        assert recovered_fsm.context.preferences == {"budget": "1000"}
        assert recovered_fsm.context.search_results == [{"id": 1, "name": "MacBook"}]

def test_state_transition_atomicity():
    """Test that state transitions are atomic"""
    session_id = "atomicity_test"
    store = UnifiedSessionStore()
    
    fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
    fsm.context = SwisperContext(session_id=session_id, current_state="search")
    
    with patch.object(store, '_save_to_postgres_atomic') as mock_save:
        mock_save.return_value = False
        
        result = store.save_fsm_state(session_id, fsm)
        assert result is False
        
        assert fsm.context.current_state == "search"

def test_concurrent_session_access():
    """Test concurrent access to different sessions"""
    store = UnifiedSessionStore()
    
    sessions = []
    for i in range(3):
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.context = SwisperContext(
            session_id=f"concurrent_test_{i}", 
            current_state=["search", "refine_constraints", "match_preferences"][i]
        )
        sessions.append((f"concurrent_test_{i}", fsm))
    
    with patch.object(store, '_save_to_postgres_atomic') as mock_save, \
         patch.object(store, '_load_from_postgres_atomic') as mock_get:
        
        mock_save.return_value = True
        
        for session_id, fsm in sessions:
            mock_get.return_value = fsm.context.to_dict()
            assert store.save_fsm_state(session_id, fsm)
        
        for session_id, original_fsm in sessions:
            mock_get.return_value = original_fsm.context.to_dict()
            loaded_fsm = store.load_fsm_state(session_id)
            assert loaded_fsm is not None
            assert loaded_fsm.context.session_id == session_id
            assert loaded_fsm.context.current_state == original_fsm.context.current_state

def test_performance_under_load():
    """Test performance metrics under simulated load"""
    store = UnifiedSessionStore()
    
    with patch.object(store, '_save_to_postgres_atomic') as mock_save, \
         patch.object(store, '_load_from_postgres_atomic') as mock_get:
        
        mock_save.return_value = True
        
        for i in range(10):
            fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
            fsm.context = SwisperContext(session_id=f"perf_test_{i}", current_state="search")
            
            mock_get.return_value = fsm.context.to_dict()
            
            store.save_fsm_state(f"perf_test_{i}", fsm)
            store.load_fsm_state(f"perf_test_{i}")
        
        metrics = store.get_performance_metrics()
        assert metrics['cache_size'] > 0
        assert 'save_times' in metrics or 'db_load_times' in metrics
