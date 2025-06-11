"""
Test suite for pipeline infrastructure components.

Tests the base pipeline creation and ResultLimiterComponent functionality.
"""

import pytest
from contract_engine.haystack_components import ResultLimiterComponent
from contract_engine.pipelines import create_product_search_pipeline, create_preference_match_pipeline


class TestResultLimiterComponent:
    """Test the ResultLimiterComponent functionality."""
    
    def test_result_limiter_under_limit(self):
        """Test result limiter with products under the limit."""
        component = ResultLimiterComponent(max_results=50)
        
        products = [{"name": f"Product {i}", "price": i * 10} for i in range(30)]
        attributes = ["price", "brand", "capacity"]
        
        result, edge = component.run(products, attributes)
        
        assert result["status"] == "ok"
        assert len(result["items"]) == 30
        assert result["total_found"] == 30
        assert result["attributes"] == attributes
        assert edge == "output_1"
    
    def test_result_limiter_over_limit(self):
        """Test result limiter with products over the limit."""
        component = ResultLimiterComponent(max_results=50)
        
        products = [{"name": f"Product {i}", "price": i * 10} for i in range(75)]
        attributes = ["price", "brand", "capacity"]
        
        result, edge = component.run(products, attributes)
        
        assert result["status"] == "too_many"
        assert len(result["items"]) == 0
        assert result["total_found"] == 75
        assert result["max_allowed"] == 50
        assert result["attributes"] == attributes
        assert edge == "output_1"
    
    def test_result_limiter_exactly_at_limit(self):
        """Test result limiter with products exactly at the limit."""
        component = ResultLimiterComponent(max_results=50)
        
        products = [{"name": f"Product {i}", "price": i * 10} for i in range(50)]
        
        result, edge = component.run(products)
        
        assert result["status"] == "ok"
        assert len(result["items"]) == 50
        assert result["total_found"] == 50
    
    def test_result_limiter_empty_products(self):
        """Test result limiter with empty product list."""
        component = ResultLimiterComponent(max_results=50)
        
        result, edge = component.run([])
        
        assert result["status"] == "ok"
        assert len(result["items"]) == 0
        assert result["total_found"] == 0
    
    def test_result_limiter_batch_processing(self):
        """Test result limiter batch processing."""
        component = ResultLimiterComponent(max_results=50)
        
        products_batch = [
            [{"name": f"Product {i}", "price": i * 10} for i in range(30)],  # Under limit
            [{"name": f"Product {i}", "price": i * 10} for i in range(75)]   # Over limit
        ]
        
        results = component.run_batch(products_batch)
        
        assert len(results) == 2
        assert results[0][0]["status"] == "ok"
        assert results[1][0]["status"] == "too_many"


class TestPipelineCreation:
    """Test pipeline creation functions."""
    
    def test_create_product_search_pipeline(self):
        """Test that product search pipeline can be created."""
        pipeline = create_product_search_pipeline()
        
        assert pipeline is not None
        assert "search" in pipeline.graph.nodes
        assert "analyze_attributes" in pipeline.graph.nodes
        assert "limit_results" in pipeline.graph.nodes
    
    def test_create_preference_match_pipeline(self):
        """Test that preference match pipeline can be created."""
        pipeline = create_preference_match_pipeline()
        
        assert pipeline is not None


class TestPipelineIntegration:
    """Test basic pipeline integration."""
    
    @pytest.mark.asyncio
    async def test_product_search_pipeline_basic_flow(self):
        """Test basic product search pipeline execution."""
        from contract_engine.pipelines.product_search_pipeline import run_product_search
        
        pipeline = create_product_search_pipeline()
        
        result = await run_product_search(pipeline, "washing machine", [])
        
        assert "status" in result
        assert result["status"] in ["ok", "too_many", "error"]
        assert "items" in result
        assert "attributes" in result
        assert isinstance(result["items"], list)
        assert isinstance(result["attributes"], list)
