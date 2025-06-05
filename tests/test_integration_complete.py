"""
Comprehensive integration tests for the complete Swisper Core refactored architecture.

Tests the full purchase item contract flow from intent detection through order completion,
verifying the clean separation between FSM (control plane) and Pipelines (data plane).
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from contract_engine.contract_engine import ContractStateMachine
from swisper_core import SwisperContext
from contract_engine.pipelines.product_search_pipeline import create_product_search_pipeline
from contract_engine.pipelines.preference_match_pipeline import create_preference_match_pipeline
from orchestrator.core import handle


class TestCompleteIntegration:
    """Test complete purchase item contract flow with new architecture"""
    
    @pytest.fixture
    def mock_search_pipeline(self):
        """Mock product search pipeline with realistic responses"""
        pipeline = MagicMock()
        pipeline.run = AsyncMock()
        
        pipeline.run.side_effect = [
            {
                "status": "too_many_results",
                "items": [],
                "attributes": ["brand", "price", "screen_size", "processor"],
                "execution_time": 2.1
            },
            {
                "status": "success", 
                "items": [
                    {"name": "ASUS Gaming Laptop", "price": "1800 CHF", "brand": "ASUS"},
                    {"name": "Dell XPS 15", "price": "2200 CHF", "brand": "Dell"},
                    {"name": "MacBook Pro", "price": "2500 CHF", "brand": "Apple"}
                ],
                "attributes": ["brand", "price", "screen_size"],
                "execution_time": 1.8
            }
        ]
        return pipeline
    
    @pytest.fixture
    def mock_preference_pipeline(self):
        """Mock preference match pipeline with realistic responses"""
        pipeline = MagicMock()
        pipeline.run = AsyncMock(return_value={
            "status": "success",
            "ranked_products": [
                {"name": "ASUS Gaming Laptop", "score": 0.95, "price": "1800 CHF"},
                {"name": "Dell XPS 15", "score": 0.85, "price": "2200 CHF"},
                {"name": "MacBook Pro", "score": 0.75, "price": "2500 CHF"}
            ],
            "ranking_method": "llm",
            "execution_time": 3.2
        })
        return pipeline
    
    def test_complete_purchase_flow_with_constraint_refinement(self, mock_search_pipeline, mock_preference_pipeline):
        """Test complete purchase flow including constraint refinement loop"""
        session_id = "integration_complete_001"
        
        import os
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "contract_templates", "purchase_item.yaml"))
        fsm.product_search_pipeline = mock_search_pipeline
        fsm.preference_match_pipeline = mock_preference_pipeline
        
        fsm.context = SwisperContext(
            session_id=session_id,
            product_query="gaming laptop",
            current_state="start"
        )
        
        result = fsm.next("I want to buy a gaming laptop")
        assert result["status"] == "success"
        assert fsm.context.current_state == "search"
        
        result = fsm.next("continue")
        assert result["status"] == "success"
        assert "too many results" in result["user_message"].lower()
        assert fsm.context.current_state == "analyze_attributes"
        
        result = fsm.next("I want ASUS brand under 2000 CHF")
        assert result["status"] == "success"
        assert fsm.context.current_state == "search"
        
        result = fsm.next("continue")
        assert result["status"] == "success"
        assert fsm.context.current_state == "wait_for_preferences"
        
        result = fsm.next("I prefer good performance and 15 inch screen")
        assert result["status"] == "success"
        assert fsm.context.current_state == "filter_products"
        
        result = fsm.next("continue")
        assert result["status"] == "success"
        assert fsm.context.current_state == "rank_and_select"
        
        result = fsm.next("continue")
        assert result["status"] == "success"
        assert "ASUS Gaming Laptop" in result["user_message"]
        assert fsm.context.current_state == "confirm_selection"
        
        assert mock_search_pipeline.run.call_count == 2
        assert mock_preference_pipeline.run.call_count == 1
        
        assert len(fsm.context.search_results) == 3
        assert fsm.context.preferences is not None
        assert fsm.context.constraints is not None
    
    @pytest.mark.asyncio
    async def test_orchestrator_integration_with_new_architecture(self):
        """Test orchestrator integration with new FSM and pipeline architecture"""
        from orchestrator.core import Message
        
        with patch('contract_engine.contract_engine.ContractStateMachine') as mock_fsm_class:
            
            mock_fsm = MagicMock()
            mock_fsm.next.return_value = {
                "ask_user": "Starting product search...",
                "status": "success"
            }
            mock_fsm.context = MagicMock()
            mock_fsm.context.current_state = "search"
            mock_fsm_class.return_value = mock_fsm
            
            
            messages = [Message(role="user", content="I want to buy a laptop")]
            response = await handle(messages, "orch_integration_001")
            
            assert "reply" in response
            assert "session_id" in response
            assert response["session_id"] == "orch_integration_001"
    
    def test_session_persistence_throughout_flow(self):
        """Test session persistence and recovery throughout complete flow"""
        from swisper_core.session import save_session_context, load_session_context
        
        session_id = "integration_persistence_001"
        
        context = SwisperContext(
            session_id=session_id,
            product_query="gaming laptop",
            current_state="search",
            preferences={"brand": "ASUS", "performance": "high"},
            constraints=["price < 2000 CHF"]
        )
        
        search_result = {
            "status": "success",
            "items": [{"name": "ASUS Gaming Laptop"}],
            "attributes": ["brand", "price"]
        }
        
        preference_result = {
            "status": "success", 
            "ranked_products": [{"name": "ASUS Gaming Laptop", "score": 0.95}],
            "ranking_method": "llm"
        }
        
        context.record_pipeline_execution("product_search", search_result, 2.1)
        context.record_pipeline_execution("preference_match", preference_result, 1.8)
        
        save_session_context(session_id, context)
        loaded_context = load_session_context(session_id)
        
        assert loaded_context.session_id == session_id
        assert loaded_context.product_query == "gaming laptop"
        assert loaded_context.preferences == {"brand": "ASUS", "performance": "high"}
        assert loaded_context.constraints == ["price < 2000 CHF"]
        
        search_history = loaded_context.get_pipeline_history("product_search")
        pref_history = loaded_context.get_pipeline_history("preference_match")
        
        assert len(search_history) == 1
        assert len(pref_history) == 1
        assert search_history[0]["execution_time"] == 2.1
        assert pref_history[0]["execution_time"] == 1.8
        
        assert "product_search_avg_time" in loaded_context.pipeline_performance_metrics
        assert "preference_match_avg_time" in loaded_context.pipeline_performance_metrics
    
    def test_error_handling_throughout_flow(self):
        """Test error handling and fallback mechanisms throughout complete flow"""
        from swisper_core.errors import OperationMode
        from swisper_core.monitoring import health_monitor
        
        session_id = "integration_error_001"
        
        health_monitor.record_service_failure("openai_api", "API timeout")
        
        import os
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "contract_templates", "purchase_item.yaml"))
        fsm.context = SwisperContext(
            session_id=session_id,
            product_query="laptop",
            current_state="start"
        )
        
        with patch.object(fsm, 'product_search_pipeline') as mock_search, \
             patch.object(fsm, 'preference_match_pipeline') as mock_pref:
            
            mock_search.run = AsyncMock(return_value={
                "status": "fallback",
                "items": [{"name": "Generic Laptop", "price": "1500 CHF"}],
                "attributes": ["brand", "price"],
                "execution_time": 1.0
            })
            
            mock_pref.run = AsyncMock(return_value={
                "status": "fallback",
                "ranked_products": [{"name": "Generic Laptop", "score": 0.5}],
                "ranking_method": "fallback",
                "execution_time": 0.5
            })
            
            result = fsm.next("I want to buy a laptop")
            assert result["status"] == "success"
            
            result = fsm.next("continue")
            assert result["status"] == "success"
            
            assert "limited" in result["user_message"].lower() or "basic" in result["user_message"].lower()
    
    def test_performance_monitoring_integration(self):
        """Test performance monitoring throughout complete flow"""
        from swisper_core.monitoring import PerformanceMonitor
        
        PerformanceMonitor.clear_metrics()
        
        session_id = "integration_perf_001"
        
        import os
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "contract_templates", "purchase_item.yaml"))
        fsm.context = SwisperContext(
            session_id=session_id,
            product_query="laptop",
            current_state="start"
        )
        
        with patch.object(fsm, 'product_search_pipeline') as mock_search, \
             patch.object(fsm, 'preference_match_pipeline') as mock_pref:
            
            mock_search.run = AsyncMock(return_value={
                "status": "success",
                "items": [{"name": "Test Laptop"}],
                "attributes": ["brand"],
                "execution_time": 2.5
            })
            
            mock_pref.run = AsyncMock(return_value={
                "status": "success",
                "ranked_products": [{"name": "Test Laptop", "score": 0.9}],
                "ranking_method": "llm",
                "execution_time": 1.8
            })
            
            fsm.next("I want to buy a laptop")
            fsm.next("continue")  # Search
            fsm.next("I prefer good performance")  # Preferences
            fsm.next("continue")  # Filter
            fsm.next("continue")  # Rank
            
            search_stats = PerformanceMonitor.get_stats("product_search")
            pref_stats = PerformanceMonitor.get_stats("preference_match")
            
            assert search_stats.get("total_operations", 0) >= 1
            assert pref_stats.get("total_operations", 0) >= 1
            assert search_stats.get("avg_duration", 0) > 0
            assert pref_stats.get("avg_duration", 0) > 0
    
    def test_pipeline_caching_effectiveness(self):
        """Test that pipeline caching improves performance on repeated operations"""
        from swisper_core.monitoring import attribute_cache, pipeline_cache
        
        attribute_cache.clear()
        pipeline_cache.clear()
        
        products = [
            {"name": "Gaming Laptop", "description": "High performance gaming laptop"},
            {"name": "Business Laptop", "description": "Professional business laptop"}
        ]
        
        from contract_engine.haystack_components import AttributeAnalyzerComponent
        
        analyzer = AttributeAnalyzerComponent()
        
        import time
        start_time = time.time()
        result1 = analyzer.run(products=products)
        first_duration = time.time() - start_time
        
        start_time = time.time()
        result2 = analyzer.run(products=products)
        second_duration = time.time() - start_time
        
        assert result1["attributes"] == result2["attributes"]
        assert second_duration < first_duration * 0.5  # At least 50% faster
        assert attribute_cache.size() > 0
    
    def test_complete_flow_with_real_pipelines(self):
        """Test complete flow using real pipeline implementations (not mocked)"""
        session_id = "integration_real_001"
        
        search_pipeline = create_product_search_pipeline()
        preference_pipeline = create_preference_match_pipeline()
        
        import os
        fsm = ContractStateMachine(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "contract_templates", "purchase_item.yaml"))
        fsm.product_search_pipeline = search_pipeline
        fsm.preference_match_pipeline = preference_pipeline
        
        fsm.context = SwisperContext(
            session_id=session_id,
            product_query="laptop",
            current_state="start",
            constraints=["price < 3000 CHF"],
            preferences={"brand": "Apple", "screen_size": "13 inch"}
        )
        
        result = fsm.next("I want to buy a laptop under 3000 CHF")
        assert result["status"] == "success"
        
        result = fsm.next("continue")
        assert result["status"] == "success"
        
        if "too many" in result.get("user_message", "").lower():
            result = fsm.next("I prefer Apple brand with 13 inch screen")
            assert result["status"] == "success"
            
            result = fsm.next("continue")
            assert result["status"] == "success"
        
        assert fsm.context.product_query == "laptop"
        assert len(fsm.context.constraints) > 0
        
        search_history = fsm.context.get_pipeline_history("product_search")
        assert len(search_history) >= 1
        
        for execution in search_history:
            assert execution["execution_time"] > 0
            assert "result" in execution
            assert execution["result"]["status"] in ["success", "too_many_results", "fallback"]
