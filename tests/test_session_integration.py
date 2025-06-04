"""
Integration tests for enhanced session management with FSM and pipelines.

Tests the complete session lifecycle including FSM creation, pipeline execution,
context saving, and session recovery.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from contract_engine.contract_engine import ContractStateMachine
from contract_engine.context import SwisperContext
from contract_engine.session_persistence import session_manager, save_session_context, load_session_context
from orchestrator import core as orchestrator_core


class TestSessionIntegration:
    """Test integration between FSM, pipelines, and session persistence"""
    
    def test_fsm_session_persistence_lifecycle(self):
        """Test complete FSM session with pipeline persistence"""
        session_id = "integration_fsm_001"
        
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.context = SwisperContext(
            session_id=session_id,
            product_query="gaming laptop",
            current_state="search",
            preferences={"brand": "ASUS", "price": "under 2000"}
        )
        
        search_result = {
            "status": "success",
            "items": [{"name": "ASUS Gaming Laptop", "price": "1800 CHF"}],
            "attributes": ["brand", "price"]
        }
        
        preference_result = {
            "status": "success",
            "ranked_products": [{"name": "ASUS Gaming Laptop", "score": 0.95}],
            "ranking_method": "llm"
        }
        
        fsm.context.record_pipeline_execution("product_search", search_result, 2.5)
        fsm.context.record_pipeline_execution("preference_match", preference_result, 1.8)
        
        save_session_context(session_id, fsm.context)
        
        assert session_id in session_manager.context_cache
        cached_data = session_manager.context_cache[session_id]
        assert "context" in cached_data
        
        search_history = fsm.context.get_pipeline_history("product_search")
        pref_history = fsm.context.get_pipeline_history("preference_match")
        
        assert len(search_history) == 1
        assert len(pref_history) == 1
        assert search_history[0]["execution_time"] == 2.5
        assert pref_history[0]["execution_time"] == 1.8
        
        assert fsm.context.get_last_pipeline_result("product_search") == search_result
        assert fsm.context.get_last_pipeline_result("preference_match") == preference_result
    
    def test_orchestrator_enhanced_session_loading(self):
        """Test enhanced session context loading functionality"""
        session_id = "integration_orch_001"
        
        test_context = SwisperContext(
            session_id=session_id,
            product_query="test product",
            current_state="search",
            preferences={"brand": "Apple"}
        )
        
        test_context.record_pipeline_execution(
            "product_search", 
            {"status": "success", "items": []}, 
            1.5
        )
        
        save_session_context(session_id, test_context)
        loaded_context = load_session_context(session_id)
        
        assert loaded_context is not None
        assert loaded_context.session_id == session_id
        assert loaded_context.product_query == "test product"
        assert loaded_context.preferences == {"brand": "Apple"}
        
        pipeline_history = loaded_context.get_pipeline_history("product_search")
        assert len(pipeline_history) == 1
        assert pipeline_history[0]["execution_time"] == 1.5
    
    def test_session_cleanup_functionality(self):
        """Test session cleanup functionality"""
        from contract_engine.session_persistence import cleanup_old_sessions
        
        result = cleanup_old_sessions(max_age_hours=24)
        assert isinstance(result, int)
        assert result >= 0
    
    def test_fsm_state_transition_saves_context(self):
        """Test that FSM state transitions save enhanced context"""
        session_id = "integration_fsm_002"
        
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        fsm.context = SwisperContext(
            session_id=session_id,
            product_query="test laptop",
            current_state="start"
        )
        
        from contract_engine.state_transitions import StateTransition
        
        with patch.object(fsm, 'handle_start_state') as mock_handler, \
             patch('contract_engine.contract_engine.save_session_context') as mock_save_context:
            
            mock_handler.return_value = StateTransition(
                next_state="search",
                user_message="Starting search"
            )
            
            result = fsm.next("test input")
            
            mock_save_context.assert_called_once_with(session_id, fsm.context)
            
            assert result["status"] == "success"
    
    def test_pipeline_execution_timing_recorded(self):
        """Test that pipeline execution timing is properly recorded"""
        session_id = "integration_timing_001"
        
        context = SwisperContext(session_id=session_id)
        
        result = {"status": "success", "items": []}
        execution_time = 2.5
        
        context.record_pipeline_execution("product_search", result, execution_time)
        
        history = context.get_pipeline_history("product_search")
        assert len(history) == 1
        assert history[0]["execution_time"] == execution_time
        
        assert "product_search_avg_time" in context.pipeline_performance_metrics
        assert context.pipeline_performance_metrics["product_search_avg_time"] == execution_time
    
    def test_session_recovery_with_pipeline_cache(self):
        """Test session recovery using cached pipeline results"""
        session_id = "integration_cache_001"
        
        cached_result = {
            "status": "success",
            "items": [{"name": "Cached Product"}],
            "attributes": ["brand", "price"]
        }
        
        session_manager.save_pipeline_state(
            session_id, 
            "product_search", 
            cached_result, 
            execution_time=1.0
        )
        
        cached_state = session_manager.get_pipeline_state(session_id, "product_search")
        
        assert cached_state is not None
        assert cached_state["result"] == cached_result
        assert cached_state["execution_time"] == 1.0
        assert cached_state["status"] == "success"
        
        metrics = session_manager.get_session_metrics(session_id)
        assert metrics["total_pipeline_executions"] == 1
        assert metrics["total_execution_time"] == 1.0
    
    def test_context_serialization_with_pipeline_metadata(self):
        """Test that context serialization includes all pipeline metadata"""
        session_id = "integration_serial_001"
        
        context = SwisperContext(
            session_id=session_id,
            product_query="test product",
            preferences={"brand": "Apple"}
        )
        
        context.record_pipeline_execution("product_search", {"status": "success", "items": []}, 1.0)
        context.record_pipeline_execution("preference_match", {"status": "success", "ranked_products": []}, 2.0)
        context.record_pipeline_execution("product_search", {"status": "success", "items": []}, 1.5)
        
        context_dict = context.to_dict()
        
        assert "pipeline_executions" in context_dict
        assert "last_pipeline_results" in context_dict
        assert "pipeline_performance_metrics" in context_dict
        
        assert "product_search" in context_dict["pipeline_executions"]
        assert "preference_match" in context_dict["pipeline_executions"]
        assert len(context_dict["pipeline_executions"]["product_search"]) == 2
        assert len(context_dict["pipeline_executions"]["preference_match"]) == 1
        
        assert "product_search" in context_dict["last_pipeline_results"]
        assert "preference_match" in context_dict["last_pipeline_results"]
        
        assert "product_search_avg_time" in context_dict["pipeline_performance_metrics"]
        assert "preference_match_avg_time" in context_dict["pipeline_performance_metrics"]
        
        restored_context = SwisperContext.from_dict(context_dict)
        
        assert len(restored_context.get_pipeline_history("product_search")) == 2
        assert len(restored_context.get_pipeline_history("preference_match")) == 1
        assert restored_context.get_last_pipeline_result("product_search") is not None
        assert restored_context.get_last_pipeline_result("preference_match") is not None
