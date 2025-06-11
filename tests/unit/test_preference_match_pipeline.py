"""
Test suite for preference match pipeline integration.

Tests the complete preference match pipeline flow including spec scraping,
compatibility checking, and preference ranking.
"""

import pytest
from contract_engine.pipelines.preference_match_pipeline import (
    create_preference_match_pipeline, 
    run_preference_match,
    get_pipeline_info,
    _fallback_preference_match
)


class TestPreferenceMatchPipelineIntegration:
    """Test the complete preference match pipeline integration."""
    
    @pytest.mark.asyncio
    async def test_preference_match_pipeline_complete_flow(self):
        """Test complete preference match pipeline flow."""
        pipeline = create_preference_match_pipeline(top_k=3)
        
        products = [
            {
                "name": "Samsung Washing Machine WW70T4020EE",
                "price": "599 CHF",
                "description": "7kg capacity front-loading washing machine",
                "rating": 4.5
            },
            {
                "name": "Bosch Serie 6 WAT28400",
                "price": "749 CHF", 
                "description": "8kg capacity washing machine with EcoSilence",
                "rating": 4.7
            },
            {
                "name": "LG F4WV710P2T",
                "price": "899 CHF",
                "description": "10kg capacity washing machine with AI DD",
                "rating": 4.3
            }
        ]
        
        preferences = {
            "capacity": "at least 7kg",
            "energy_efficiency": "high",
            "price": "below 800 CHF"
        }
        
        constraints = {
            "capacity": "minimum 7kg"
        }
        
        result = await run_preference_match(
            pipeline, products, preferences, constraints, "washing machine"
        )
        
        assert "status" in result
        assert result["status"] in ["success", "fallback"]
        assert "ranked_products" in result
        assert "scores" in result
        assert "ranking_method" in result
        
        assert len(result["ranked_products"]) <= 3
        assert len(result["scores"]) == len(result["ranked_products"])
        
        for score in result["scores"]:
            assert 0.0 <= score <= 1.0
        
        assert "total_processed" in result
        assert result["total_processed"] == len(products)
    
    @pytest.mark.asyncio
    async def test_preference_match_pipeline_no_preferences(self):
        """Test preference match pipeline with no preferences (fallback ranking)."""
        pipeline = create_preference_match_pipeline(top_k=2)
        
        products = [
            {"name": "Product A", "price": "300 CHF", "rating": 4.5},
            {"name": "Product B", "price": "200 CHF", "rating": 4.8},
            {"name": "Product C", "price": "400 CHF", "rating": 4.2}
        ]
        
        result = await run_preference_match(pipeline, products, {})
        
        assert result["status"] in ["success", "fallback"]
        assert "ranked_products" in result
        assert len(result["ranked_products"]) <= 2 or result["status"] == "fallback"
        assert "preferences_applied" in result
    
    @pytest.mark.asyncio
    async def test_preference_match_pipeline_empty_products(self):
        """Test preference match pipeline with empty product list."""
        pipeline = create_preference_match_pipeline()
        
        result = await run_preference_match(pipeline, [], {"price": "affordable"})
        
        assert result["status"] == "no_products"
        assert result["ranked_products"] == []
        assert result["scores"] == []
        assert "message" in result
    
    @pytest.mark.asyncio
    async def test_preference_match_pipeline_too_many_products(self):
        """Test preference match pipeline with too many products (>50)."""
        pipeline = create_preference_match_pipeline()
        
        products = [
            {"name": f"Product {i}", "price": f"{i*10} CHF", "rating": 4.0}
            for i in range(60)
        ]
        
        preferences = {"price": "affordable"}
        
        result = await run_preference_match(pipeline, products, preferences)
        
        assert "status" in result
        assert "total_processed" in result
        assert result["total_processed"] == 50  # Should be truncated
    
    @pytest.mark.asyncio
    async def test_preference_match_pipeline_with_constraints(self):
        """Test preference match pipeline with hard constraints."""
        pipeline = create_preference_match_pipeline()
        
        products = [
            {"name": "Laptop A", "price": "800 CHF", "processor": "Intel i5"},
            {"name": "Laptop B", "price": "1200 CHF", "processor": "Intel i7"},
            {"name": "Laptop C", "price": "1500 CHF", "processor": "Intel i9"}
        ]
        
        preferences = {"performance": "high"}
        constraints = {"processor": "Intel i7 or better"}
        
        result = await run_preference_match(
            pipeline, products, preferences, constraints, "laptop"
        )
        
        assert "status" in result
        assert "ranked_products" in result
    
    @pytest.mark.asyncio
    async def test_preference_match_pipeline_error_handling(self):
        """Test preference match pipeline error handling."""
        pipeline = create_preference_match_pipeline()
        
        result = await run_preference_match(pipeline, None, {})
        
        assert result["status"] == "no_products"
        assert result["ranked_products"] == []


class TestPreferenceMatchPipelineComponents:
    """Test individual aspects of the preference match pipeline."""
    
    def test_pipeline_creation_default_params(self):
        """Test pipeline creation with default parameters."""
        pipeline = create_preference_match_pipeline()
        
        info = get_pipeline_info(pipeline)
        
        assert "nodes" in info
        assert "edges" in info
        assert info["pipeline_type"] == "preference_match"
        
        required_nodes = ["scrape_specs", "check_compat", "rank_prefs"]
        for node in required_nodes:
            assert node in info["nodes"]
    
    def test_pipeline_creation_custom_top_k(self):
        """Test pipeline creation with custom top_k parameter."""
        pipeline = create_preference_match_pipeline(top_k=5)
        
        info = get_pipeline_info(pipeline)
        assert len(info["nodes"]) == 4  # Query + 3 component nodes
        assert "rank_prefs" in info["nodes"]
    
    def test_pipeline_node_connections(self):
        """Test that pipeline nodes are properly connected."""
        pipeline = create_preference_match_pipeline()
        
        graph = pipeline.graph
        
        scraper_edges = list(graph.successors("scrape_specs"))
        assert "check_compat" in scraper_edges
        
        checker_edges = list(graph.successors("check_compat"))
        assert "rank_prefs" in checker_edges
    
    def test_get_pipeline_info(self):
        """Test pipeline info extraction."""
        pipeline = create_preference_match_pipeline()
        
        info = get_pipeline_info(pipeline)
        
        assert info["node_count"] == 4  # Query + 3 component nodes
        assert info["pipeline_type"] == "preference_match"
        assert "components" in info
        
        expected_components = {
            "scrape_specs": "SpecScraperComponent",
            "check_compat": "CompatibilityCheckerComponent",
            "rank_prefs": "PreferenceRankerComponent"
        }
        
        for node, component in expected_components.items():
            assert info["components"][node] == component


class TestPreferenceMatchFallback:
    """Test fallback preference matching functionality."""
    
    def test_fallback_preference_match_basic(self):
        """Test basic fallback preference matching."""
        products = [
            {"name": "Product A", "price": "500 CHF", "rating": 4.5},
            {"name": "Product B", "price": "300 CHF", "rating": 4.8},
            {"name": "Product C", "price": "700 CHF", "rating": 4.2}
        ]
        
        result = _fallback_preference_match(products, {"price": "affordable"})
        
        assert result["status"] == "success"
        assert result["ranking_method"] == "fallback"
        assert len(result["ranked_products"]) <= 3
        assert len(result["scores"]) == len(result["ranked_products"])
        
        assert result["ranked_products"][0]["name"] == "Product B"
    
    def test_fallback_preference_match_with_error(self):
        """Test fallback preference matching with error message."""
        products = [{"name": "Product A", "price": "100 CHF", "rating": 4.0}]
        
        result = _fallback_preference_match(products, {}, error="Pipeline failed")
        
        assert result["status"] == "fallback"
        assert "error" in result
        assert result["error"] == "Pipeline failed"
        assert "message" in result
    
    def test_fallback_preference_match_empty_products(self):
        """Test fallback preference matching with empty products."""
        result = _fallback_preference_match([], {"price": "low"})
        
        assert result["status"] == "success"
        assert result["ranked_products"] == []
        assert result["scores"] == []
    
    def test_fallback_preference_match_invalid_data(self):
        """Test fallback preference matching with invalid product data."""
        products = [
            {"name": "Product A"},  # Missing price and rating
            {"name": "Product B", "price": "invalid", "rating": "bad"}
        ]
        
        result = _fallback_preference_match(products, {})
        
        assert result["status"] in ["success", "error"]  # May fail due to invalid data
        assert len(result["ranked_products"]) <= 3


class TestPreferenceMatchPipelinePerformance:
    """Test preference match pipeline performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_pipeline_execution_time(self):
        """Test that pipeline executes within reasonable time."""
        import time
        
        pipeline = create_preference_match_pipeline()
        
        products = [
            {"name": f"Product {i}", "price": f"{i*100} CHF", "rating": 4.0}
            for i in range(20)  # Moderate number of products
        ]
        
        preferences = {"price": "below 1000 CHF", "quality": "high"}
        
        start_time = time.time()
        result = await run_preference_match(pipeline, products, preferences)
        execution_time = time.time() - start_time
        
        assert execution_time < 15.0, f"Pipeline took too long: {execution_time}s"
        assert "status" in result
    
    @pytest.mark.asyncio
    async def test_pipeline_with_maximum_products(self):
        """Test pipeline performance with maximum number of products (50)."""
        pipeline = create_preference_match_pipeline()
        
        products = [
            {"name": f"Product {i}", "price": f"{i*50} CHF", "rating": 4.0 + (i % 10) * 0.1}
            for i in range(50)
        ]
        
        preferences = {"price": "affordable", "rating": "high"}
        
        result = await run_preference_match(pipeline, products, preferences)
        
        assert "status" in result
        assert result["total_processed"] == 50
        assert len(result["ranked_products"]) <= 3
