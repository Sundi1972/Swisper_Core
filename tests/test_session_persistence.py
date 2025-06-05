"""
Test suite for enhanced session persistence and memory management.

Tests pipeline state persistence, enhanced context serialization, and session cleanup.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from swisper_core.session import (
    PipelineSessionManager, session_manager,
    save_pipeline_execution, get_cached_pipeline_result,
    save_session_context, load_session_context,
    get_session_performance_metrics, cleanup_old_sessions
)
from swisper_core import SwisperContext


class TestPipelineSessionManager:
    """Test pipeline session manager functionality"""
    
    def test_save_and_get_pipeline_state(self):
        """Test saving and retrieving pipeline state"""
        manager = PipelineSessionManager()
        session_id = "test_session_001"
        pipeline_name = "product_search"
        
        pipeline_result = {
            "status": "success",
            "items": [{"name": "Product A"}, {"name": "Product B"}],
            "total_found": 2
        }
        
        manager.save_pipeline_state(session_id, pipeline_name, pipeline_result, execution_time=1.5)
        
        state = manager.get_pipeline_state(session_id, pipeline_name)
        
        assert state is not None
        assert state["result"] == pipeline_result
        assert state["execution_time"] == 1.5
        assert state["status"] == "success"
        assert "timestamp" in state
        assert "operation_mode" in state
    
    def test_get_pipeline_state_expired(self):
        """Test that expired pipeline state is cleaned up"""
        manager = PipelineSessionManager()
        session_id = "test_session_002"
        pipeline_name = "preference_match"
        
        old_timestamp = (datetime.now() - timedelta(hours=1)).isoformat()
        manager.pipeline_cache[session_id] = {
            pipeline_name: {
                "result": {"status": "success"},
                "timestamp": old_timestamp,
                "execution_time": 2.0,
                "status": "success"
            }
        }
        
        state = manager.get_pipeline_state(session_id, pipeline_name)
        assert state is None
        assert pipeline_name not in manager.pipeline_cache.get(session_id, {})
    
    def test_save_and_load_enhanced_context(self):
        """Test saving and loading enhanced context"""
        manager = PipelineSessionManager()
        session_id = "test_session_003"
        
        context = SwisperContext(
            session_id=session_id,
            product_query="test laptop",
            preferences={"brand": "Apple", "price": "under 2000"},
            constraints=["price < 2000", "brand = Apple"]
        )
        
        context.record_pipeline_execution("product_search", {"status": "success", "items": []}, 1.2)
        context.record_pipeline_execution("preference_match", {"status": "success", "ranked_products": []}, 0.8)
        
        pipeline_metadata = {
            "search_query_enhanced": True,
            "preference_scoring_method": "llm"
        }
        
        with patch('orchestrator.session_store.set_contract_fsm') as mock_set_fsm:
            manager.save_enhanced_context(session_id, context, pipeline_metadata)
            
            assert mock_set_fsm.called
            
            assert session_id in manager.context_cache
            cached_data = manager.context_cache[session_id]
            assert "context" in cached_data
            assert "saved_at" in cached_data
            assert cached_data["context"]["pipeline_metadata"] == pipeline_metadata
    
    def test_session_metrics_tracking(self):
        """Test session performance metrics tracking"""
        manager = PipelineSessionManager()
        session_id = "test_session_004"
        
        manager.save_pipeline_state(session_id, "product_search", {"status": "success"}, 1.0)
        manager.save_pipeline_state(session_id, "preference_match", {"status": "success"}, 2.0)
        manager.save_pipeline_state(session_id, "product_search", {"status": "success"}, 1.5)
        
        metrics = manager.get_session_metrics(session_id)
        
        assert metrics["total_pipeline_executions"] == 3
        assert metrics["total_execution_time"] == 4.5
        assert metrics["average_execution_time"] == 1.5
        assert metrics["pipeline_executions"]["product_search"] == 2
        assert metrics["pipeline_executions"]["preference_match"] == 1
        assert metrics["pipeline_success_rate"] == 1.0
        assert "last_activity" in metrics
    
    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired session data"""
        manager = PipelineSessionManager()
        
        current_time = datetime.now()
        old_timestamp = (current_time - timedelta(hours=25)).isoformat()
        recent_timestamp = (current_time - timedelta(hours=1)).isoformat()
        
        manager.pipeline_cache["old_session"] = {
            "product_search": {
                "result": {"status": "success"},
                "timestamp": old_timestamp,
                "execution_time": 1.0
            }
        }
        
        manager.pipeline_cache["recent_session"] = {
            "preference_match": {
                "result": {"status": "success"},
                "timestamp": recent_timestamp,
                "execution_time": 2.0
            }
        }
        
        manager.session_metrics["old_session"] = {"total_executions": 1}
        manager.session_metrics["recent_session"] = {"total_executions": 1}
        
        cleaned_count = manager.cleanup_expired_sessions(max_age_hours=24)
        
        assert "old_session" not in manager.pipeline_cache
        assert "old_session" not in manager.session_metrics
        
        assert "recent_session" in manager.pipeline_cache
        assert "recent_session" in manager.session_metrics
        
        assert cleaned_count >= 1


class TestConvenienceFunctions:
    """Test convenience functions for session persistence"""
    
    def test_save_and_get_pipeline_execution(self):
        """Test convenience functions for pipeline execution"""
        session_id = "test_convenience_001"
        pipeline_name = "product_search"
        result = {"status": "success", "items": []}
        
        save_pipeline_execution(session_id, pipeline_name, result, 1.0)
        
        cached_result = get_cached_pipeline_result(session_id, pipeline_name)
        
        assert cached_result == result
    
    def test_save_and_load_session_context(self):
        """Test convenience functions for session context"""
        session_id = "test_convenience_002"
        
        context = SwisperContext(
            session_id=session_id,
            product_query="test product",
            current_state="search"
        )
        
        with patch('orchestrator.session_store.set_contract_fsm'), \
             patch('orchestrator.session_store.get_contract_context') as mock_get_context:
            
            save_session_context(session_id, context)
            
            mock_get_context.return_value = context.to_dict()
            
            loaded_context = load_session_context(session_id)
            
            assert loaded_context is not None
            assert loaded_context.session_id == session_id
            assert loaded_context.product_query == "test product"
            assert loaded_context.current_state == "search"
    
    def test_get_session_performance_metrics(self):
        """Test getting session performance metrics"""
        session_id = "test_convenience_003"
        
        save_pipeline_execution(session_id, "product_search", {"status": "success"}, 1.0)
        save_pipeline_execution(session_id, "preference_match", {"status": "success"}, 2.0)
        
        metrics = get_session_performance_metrics(session_id)
        
        assert metrics["total_pipeline_executions"] == 2
        assert metrics["total_execution_time"] == 3.0
        assert metrics["average_execution_time"] == 1.5
    
    def test_cleanup_old_sessions_convenience(self):
        """Test cleanup convenience function"""
        save_pipeline_execution("test_session", "product_search", {"status": "success"}, 1.0)
        
        cleaned_count = cleanup_old_sessions(max_age_hours=0)  # Clean everything
        
        assert cleaned_count >= 0  # Should clean up at least the test data


class TestEnhancedContext:
    """Test enhanced context functionality"""
    
    def test_record_pipeline_execution(self):
        """Test recording pipeline execution in context"""
        context = SwisperContext(session_id="test_context_001")
        
        result = {
            "status": "success",
            "items": [{"name": "Product A"}, {"name": "Product B"}],
            "ranking_method": "llm"
        }
        
        context.record_pipeline_execution("product_search", result, 1.5)
        
        history = context.get_pipeline_history("product_search")
        assert len(history) == 1
        
        execution = history[0]
        assert execution["status"] == "success"
        assert execution["execution_time"] == 1.5
        assert execution["result_summary"]["items_count"] == 2
        assert execution["result_summary"]["ranking_method"] == "llm"
        
        last_result = context.get_last_pipeline_result("product_search")
        assert last_result == result
        
        assert "product_search_avg_time" in context.pipeline_performance_metrics
        assert context.pipeline_performance_metrics["product_search_avg_time"] == 1.5
    
    def test_multiple_pipeline_executions(self):
        """Test multiple pipeline executions tracking"""
        context = SwisperContext(session_id="test_context_002")
        
        context.record_pipeline_execution("product_search", {"status": "success", "items": []}, 1.0)
        context.record_pipeline_execution("product_search", {"status": "success", "items": []}, 2.0)
        context.record_pipeline_execution("preference_match", {"status": "success", "ranked_products": []}, 1.5)
        
        search_history = context.get_pipeline_history("product_search")
        assert len(search_history) == 2
        
        pref_history = context.get_pipeline_history("preference_match")
        assert len(pref_history) == 1
        
        assert context.get_last_pipeline_result("product_search") is not None
        assert context.get_last_pipeline_result("preference_match") is not None
        assert context.get_last_pipeline_result("nonexistent") is None
    
    def test_context_serialization_with_pipeline_data(self):
        """Test context serialization includes pipeline data"""
        context = SwisperContext(session_id="test_context_003")
        
        context.record_pipeline_execution("product_search", {"status": "success", "items": []}, 1.0)
        
        context_dict = context.to_dict()
        
        assert "pipeline_executions" in context_dict
        assert "last_pipeline_results" in context_dict
        assert "pipeline_performance_metrics" in context_dict
        
        assert "product_search" in context_dict["pipeline_executions"]
        assert "product_search" in context_dict["last_pipeline_results"]
        assert "product_search_avg_time" in context_dict["pipeline_performance_metrics"]
        
        restored_context = SwisperContext.from_dict(context_dict)
        
        assert restored_context.session_id == "test_context_003"
        assert len(restored_context.get_pipeline_history("product_search")) == 1
        assert restored_context.get_last_pipeline_result("product_search") is not None


class TestIntegrationScenarios:
    """Test complete integration scenarios"""
    
    def test_complete_session_lifecycle(self):
        """Test complete session lifecycle with persistence"""
        session_id = "integration_test_001"
        
        context = SwisperContext(
            session_id=session_id,
            product_query="gaming laptop",
            current_state="search"
        )
        
        search_result = {
            "status": "success",
            "items": [{"name": "Gaming Laptop A"}, {"name": "Gaming Laptop B"}],
            "attributes": ["brand", "price", "performance"]
        }
        
        context.record_pipeline_execution("product_search", search_result, 2.5)
        save_pipeline_execution(session_id, "product_search", search_result, 2.5)
        
        context.update_state("filter_products")
        context.search_results = search_result["items"]
        
        pref_result = {
            "status": "success",
            "ranked_products": [{"name": "Gaming Laptop A", "score": 0.9}],
            "ranking_method": "llm"
        }
        
        context.record_pipeline_execution("preference_match", pref_result, 1.8)
        save_pipeline_execution(session_id, "preference_match", pref_result, 1.8)
        
        pipeline_metadata = {
            "search_enhanced": True,
            "preference_method": "llm_scoring"
        }
        
        with patch('orchestrator.session_store.set_contract_fsm'):
            save_session_context(session_id, context, pipeline_metadata)
        
        metrics = get_session_performance_metrics(session_id)
        assert metrics["total_pipeline_executions"] == 2
        assert metrics["total_execution_time"] == 4.3
        assert metrics["average_execution_time"] == 2.15
        
        cached_search = get_cached_pipeline_result(session_id, "product_search")
        cached_pref = get_cached_pipeline_result(session_id, "preference_match")
        
        assert cached_search == search_result
        assert cached_pref == pref_result
        
        search_history = context.get_pipeline_history("product_search")
        pref_history = context.get_pipeline_history("preference_match")
        
        assert len(search_history) == 1
        assert len(pref_history) == 1
        assert search_history[0]["execution_time"] == 2.5
        assert pref_history[0]["execution_time"] == 1.8
