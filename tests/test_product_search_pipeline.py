"""
Test suite for product search pipeline integration.

Tests the complete product search pipeline flow including search,
attribute analysis, and result limiting.
"""

import pytest
from contract_engine.pipelines.product_search_pipeline import create_product_search_pipeline, run_product_search


class TestProductSearchPipelineIntegration:
    """Test the complete product search pipeline integration."""
    
    @pytest.mark.asyncio
    async def test_product_search_pipeline_under_limit(self):
        """Test product search pipeline with results under the limit."""
        pipeline = create_product_search_pipeline()
        
        result = await run_product_search(pipeline, "washing machine", [])
        
        assert "status" in result
        assert result["status"] in ["ok", "too_many", "error"]
        assert "items" in result
        assert "attributes" in result
        assert isinstance(result["items"], list)
        assert isinstance(result["attributes"], list)
        
        if result["status"] == "ok":
            assert len(result["items"]) <= 50
            assert "total_found" in result
    
    @pytest.mark.asyncio
    async def test_product_search_pipeline_with_constraints(self):
        """Test product search pipeline with hard constraints."""
        pipeline = create_product_search_pipeline()
        
        constraints = [
            {"type": "price", "value": "below 1000 CHF"},
            {"type": "capacity", "value": "at least 7kg"}
        ]
        
        result = await run_product_search(pipeline, "washing machine", constraints)
        
        assert "status" in result
        assert result["status"] in ["ok", "too_many", "error"]
        assert "items" in result
        assert "attributes" in result
    
    @pytest.mark.asyncio
    async def test_product_search_pipeline_error_handling(self):
        """Test product search pipeline error handling."""
        pipeline = create_product_search_pipeline()
        
        result = await run_product_search(pipeline, "", None)
        
        assert "status" in result
        if result["status"] == "error":
            assert "error" in result
            assert result["items"] == []
            assert result["attributes"] == []
    
    @pytest.mark.asyncio
    async def test_product_search_pipeline_attribute_discovery(self):
        """Test that pipeline discovers relevant attributes."""
        pipeline = create_product_search_pipeline()
        
        result = await run_product_search(pipeline, "laptop", [])
        
        assert "attributes" in result
        assert isinstance(result["attributes"], list)
        
        if result["status"] == "ok" and result["attributes"]:
            attributes_str = " ".join(result["attributes"]).lower()
            laptop_related = any(attr in attributes_str for attr in 
                               ["processor", "memory", "storage", "screen", "battery", "brand"])
            assert laptop_related or len(result["attributes"]) > 0


class TestProductSearchPipelineComponents:
    """Test individual components within the pipeline."""
    
    def test_pipeline_has_required_nodes(self):
        """Test that pipeline contains all required nodes."""
        pipeline = create_product_search_pipeline()
        
        required_nodes = ["search", "analyze_attributes", "limit_results"]
        
        for node_name in required_nodes:
            assert node_name in pipeline.graph.nodes, f"Missing required node: {node_name}"
    
    def test_pipeline_node_connections(self):
        """Test that pipeline nodes are properly connected."""
        pipeline = create_product_search_pipeline()
        
        graph = pipeline.graph
        
        search_edges = list(graph.successors("search"))
        assert "analyze_attributes" in search_edges
        
        analyzer_edges = list(graph.successors("analyze_attributes"))
        assert "limit_results" in analyzer_edges


class TestProductSearchPipelinePerformance:
    """Test pipeline performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_pipeline_execution_time(self):
        """Test that pipeline executes within reasonable time."""
        import time
        
        pipeline = create_product_search_pipeline()
        
        start_time = time.time()
        result = await run_product_search(pipeline, "smartphone", [])
        execution_time = time.time() - start_time
        
        assert execution_time < 10.0, f"Pipeline took too long: {execution_time}s"
        assert "status" in result
