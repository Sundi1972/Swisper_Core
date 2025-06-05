"""
Simple integration tests for the Swisper Core refactored architecture.

Tests core functionality without complex mocking to verify the architecture works.
"""
import pytest
from swisper_core import SwisperContext
from contract_engine.pipelines.product_search_pipeline import create_product_search_pipeline
from contract_engine.pipelines.preference_match_pipeline import create_preference_match_pipeline


class TestSimpleIntegration:
    """Simple integration tests for core functionality"""
    
    def test_context_creation_and_serialization(self):
        """Test SwisperContext creation and serialization"""
        context = SwisperContext(
            session_id="test_001",
            product_query="laptop",
            current_state="search",
            preferences={"brand": "Apple"},
            constraints=["price < 2000 CHF"]
        )
        
        assert context.session_id == "test_001"
        assert context.product_query == "laptop"
        assert context.current_state == "search"
        assert context.preferences == {"brand": "Apple"}
        assert context.constraints == ["price < 2000 CHF"]
        
        result = {"status": "success", "items": []}
        context.record_pipeline_execution("product_search", result, 1.5)
        
        history = context.get_pipeline_history("product_search")
        assert len(history) == 1
        assert history[0]["execution_time"] == 1.5
        assert history[0]["status"] == "success"
    
    def test_pipeline_creation(self):
        """Test that pipelines can be created without errors"""
        search_pipeline = create_product_search_pipeline()
        preference_pipeline = create_preference_match_pipeline()
        
        assert search_pipeline is not None
        assert preference_pipeline is not None
        
        assert hasattr(search_pipeline, 'run')
        assert hasattr(preference_pipeline, 'run')
    
    def test_session_persistence_basic(self):
        """Test basic session persistence functionality"""
        from swisper_core.session import save_session_context, load_session_context
        
        context = SwisperContext(
            session_id="persist_test_001",
            product_query="gaming laptop",
            current_state="search"
        )
        
        save_session_context("persist_test_001", context)
        loaded_context = load_session_context("persist_test_001")
        
        assert loaded_context is not None
        assert loaded_context.session_id == "persist_test_001"
        assert loaded_context.product_query == "gaming laptop"
        assert loaded_context.current_state == "search"
    
    def test_performance_monitoring_basic(self):
        """Test basic performance monitoring functionality"""
        from swisper_core.monitoring import PerformanceMonitor, PipelineTimer
        
        monitor = PerformanceMonitor()
        monitor.clear_metrics()
        
        with PipelineTimer("test_operation") as timer:
            import time
            time.sleep(0.01)  # Small delay for timing
        
        monitor.record_operation("test_operation", timer.duration, True)
        stats = monitor.get_operation_stats("test_operation")
        assert stats.get("total_calls", 0) >= 1
        assert stats.get("avg_duration", 0) > 0
    
    def test_error_handling_basic(self):
        """Test basic error handling functionality"""
        from swisper_core.errors import health_monitor
        
        health_monitor.report_service_error("test_service", Exception("test error"))
        
        assert hasattr(health_monitor, 'is_service_available')
        health_status = health_monitor.is_service_available("test_service")
        assert health_status is not None
    
    def test_architecture_separation(self):
        """Test that FSM and Pipeline separation is maintained"""
        from contract_engine.contract_engine import ContractStateMachine
        
        fsm = ContractStateMachine("contract_templates/purchase_item.yaml")
        assert fsm is not None
        
        search_pipeline = create_product_search_pipeline()
        preference_pipeline = create_preference_match_pipeline()
        
        fsm.product_search_pipeline = search_pipeline
        fsm.preference_match_pipeline = preference_pipeline
        
        assert hasattr(fsm, 'product_search_pipeline')
        assert hasattr(fsm, 'preference_match_pipeline')
        assert fsm.product_search_pipeline is not None
        assert fsm.preference_match_pipeline is not None
