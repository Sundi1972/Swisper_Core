"""
Test suite for missing pipeline components.

Tests the SpecScraperComponent, CompatibilityCheckerComponent, and 
PreferenceRankerComponent functionality.
"""

import pytest
from contract_engine.haystack_components import (
    SpecScraperComponent, 
    CompatibilityCheckerComponent, 
    PreferenceRankerComponent
)


class TestSpecScraperComponent:
    """Test the SpecScraperComponent functionality."""
    
    def test_spec_scraper_washing_machine(self):
        """Test spec scraping for washing machine products."""
        component = SpecScraperComponent()
        
        products = [
            {
                "name": "Samsung Washing Machine WW70T4020EE",
                "price": "599 CHF",
                "description": "7kg capacity front-loading washing machine"
            }
        ]
        
        result, edge = component.run(products, "washing machine")
        
        assert edge == "output_1"
        assert "enhanced_products" in result
        assert len(result["enhanced_products"]) == 1
        
        enhanced_product = result["enhanced_products"][0]
        assert enhanced_product["spec_scraping_completed"] is True
        assert "detailed_specs" in enhanced_product
        assert "compatibility_features" in enhanced_product
        
        specs = enhanced_product["detailed_specs"]
        assert "capacity" in specs
        assert "energy_rating" in specs
        assert "spin_speed" in specs
    
    def test_spec_scraper_laptop(self):
        """Test spec scraping for laptop products."""
        component = SpecScraperComponent()
        
        products = [
            {
                "name": "MacBook Pro 15-inch",
                "price": "2499 CHF",
                "description": "Professional laptop with M2 chip"
            }
        ]
        
        result, edge = component.run(products, "laptop")
        
        enhanced_product = result["enhanced_products"][0]
        specs = enhanced_product["detailed_specs"]
        
        assert "processor" in specs
        assert "memory" in specs
        assert "storage" in specs
        assert "screen_size" in specs
    
    def test_spec_scraper_generic_product(self):
        """Test spec scraping for generic products."""
        component = SpecScraperComponent()
        
        products = [
            {
                "name": "Generic Product",
                "price": "100 CHF",
                "description": "Some product"
            }
        ]
        
        result, edge = component.run(products, "generic")
        
        enhanced_product = result["enhanced_products"][0]
        specs = enhanced_product["detailed_specs"]
        
        assert "brand" in specs
        assert "model" in specs
        assert "warranty" in specs
    
    def test_spec_scraper_caching(self):
        """Test that spec scraper uses caching."""
        component = SpecScraperComponent()
        
        products = [
            {
                "name": "Test Product",
                "price": "100 CHF"
            }
        ]
        
        result1, _ = component.run(products, "test")
        
        result2, _ = component.run(products, "test")
        
        assert result1["enhanced_products"][0]["spec_scraping_completed"] is True
        assert result2["enhanced_products"][0]["spec_scraping_completed"] is True
    
    def test_spec_scraper_empty_products(self):
        """Test spec scraper with empty product list."""
        component = SpecScraperComponent()
        
        result, edge = component.run([], "test")
        
        assert edge == "output_1"
        assert result["enhanced_products"] == []
    
    def test_spec_scraper_batch_processing(self):
        """Test spec scraper batch processing."""
        component = SpecScraperComponent()
        
        products_batch = [
            [{"name": "Product 1", "price": "100 CHF"}],
            [{"name": "Product 2", "price": "200 CHF"}]
        ]
        
        results = component.run_batch(products_batch, ["context1", "context2"])
        
        assert len(results) == 2
        assert all(edge == "output_1" for _, edge in results)


class TestCompatibilityCheckerComponent:
    """Test the CompatibilityCheckerComponent functionality."""
    
    def test_compatibility_checker_no_constraints(self):
        """Test compatibility checker with no constraints."""
        component = CompatibilityCheckerComponent()
        
        products = [
            {"name": "Product 1", "price": "100 CHF"},
            {"name": "Product 2", "price": "200 CHF"}
        ]
        
        result, edge = component.run(products, {}, "test query")
        
        assert edge == "output_1"
        assert "compatible_products" in result
        assert len(result["compatible_products"]) == 2
    
    def test_compatibility_checker_with_constraints(self):
        """Test compatibility checker with constraints."""
        component = CompatibilityCheckerComponent()
        
        products = [
            {"name": "Washing Machine A", "capacity": "7kg"},
            {"name": "Washing Machine B", "capacity": "8kg"}
        ]
        
        constraints = {"capacity": "at least 7kg", "energy_rating": "A++"}
        
        result, edge = component.run(products, constraints, "washing machine")
        
        assert edge == "output_1"
        assert "compatible_products" in result
        assert "compatibility_results" in result
    
    def test_compatibility_checker_error_handling(self):
        """Test compatibility checker error handling."""
        component = CompatibilityCheckerComponent()
        
        result, edge = component.run([], {}, "test")
        
        assert edge == "output_1"
        assert "compatible_products" in result
        assert result["compatible_products"] == []


class TestPreferenceRankerComponent:
    """Test the PreferenceRankerComponent functionality."""
    
    def test_preference_ranker_no_preferences(self):
        """Test preference ranker with no preferences (fallback ranking)."""
        component = PreferenceRankerComponent(top_k=3)
        
        products = [
            {"name": "Product A", "price": "300 CHF", "rating": 4.5},
            {"name": "Product B", "price": "200 CHF", "rating": 4.8},
            {"name": "Product C", "price": "400 CHF", "rating": 4.2}
        ]
        
        result, edge = component.run(products, {})
        
        assert edge == "output_1"
        assert "ranked_products" in result
        assert "scores" in result
        assert "ranking_method" in result
        assert result["ranking_method"] == "fallback"
        assert len(result["ranked_products"]) == 3
        assert len(result["scores"]) == 3
    
    def test_preference_ranker_with_preferences(self):
        """Test preference ranker with user preferences."""
        component = PreferenceRankerComponent(top_k=2)
        
        products = [
            {"name": "Budget Laptop", "price": "800 CHF", "description": "affordable laptop"},
            {"name": "Gaming Laptop", "price": "2000 CHF", "description": "high-performance gaming"},
            {"name": "Business Laptop", "price": "1200 CHF", "description": "professional business laptop"}
        ]
        
        preferences = {
            "price": "below 1500 CHF",
            "use_case": "business work"
        }
        
        result, edge = component.run(products, preferences)
        
        assert edge == "output_1"
        assert "ranked_products" in result
        assert "scores" in result
        assert len(result["ranked_products"]) == 2
        assert len(result["scores"]) == 2
        
        for score in result["scores"]:
            assert 0.0 <= score <= 1.0
    
    def test_preference_ranker_empty_products(self):
        """Test preference ranker with empty product list."""
        component = PreferenceRankerComponent()
        
        result, edge = component.run([], {"price": "below 1000 CHF"})
        
        assert edge == "output_1"
        assert result["ranked_products"] == []
        assert result["scores"] == []
    
    def test_preference_ranker_top_k_limiting(self):
        """Test that preference ranker respects top_k limit."""
        component = PreferenceRankerComponent(top_k=2)
        
        products = [
            {"name": f"Product {i}", "price": f"{i*100} CHF", "rating": 4.0}
            for i in range(5)
        ]
        
        preferences = {"price": "affordable"}
        
        result, edge = component.run(products, preferences)
        
        assert len(result["ranked_products"]) == 2
        assert len(result["scores"]) == 2
    
    def test_preference_ranker_fallback_scoring(self):
        """Test preference ranker fallback scoring mechanism."""
        component = PreferenceRankerComponent()
        
        products = [
            {"name": "Cheap Product", "price": "500 CHF", "description": "budget option"},
            {"name": "Expensive Product", "price": "1500 CHF", "description": "premium option"}
        ]
        
        preferences = {"price": "below 1000 CHF"}
        
        result, edge = component.run(products, preferences)
        
        assert "ranked_products" in result
        assert "scores" in result
        assert all(0.0 <= score <= 1.0 for score in result["scores"])
    
    def test_preference_ranker_batch_processing(self):
        """Test preference ranker batch processing."""
        component = PreferenceRankerComponent(top_k=2)
        
        products_batch = [
            [{"name": "Product A", "price": "100 CHF"}],
            [{"name": "Product B", "price": "200 CHF"}]
        ]
        
        preferences_batch = [
            {"price": "below 150 CHF"},
            {"price": "below 250 CHF"}
        ]
        
        results = component.run_batch(products_batch, preferences_batch)
        
        assert len(results) == 2
        assert all(edge == "output_1" for _, edge in results)
        assert all("ranked_products" in result for result, _ in results)


class TestPipelineComponentsIntegration:
    """Test integration between pipeline components."""
    
    def test_spec_scraper_to_compatibility_checker_flow(self):
        """Test flow from spec scraper to compatibility checker."""
        scraper = SpecScraperComponent()
        checker = CompatibilityCheckerComponent()
        
        products = [
            {"name": "Samsung Washing Machine", "price": "599 CHF"}
        ]
        
        scraper_result, _ = scraper.run(products, "washing machine")
        enhanced_products = scraper_result["enhanced_products"]
        
        constraints = {"capacity": "at least 7kg"}
        checker_result, _ = checker.run(enhanced_products, constraints, "washing machine")
        
        assert "compatible_products" in checker_result
    
    def test_compatibility_checker_to_preference_ranker_flow(self):
        """Test flow from compatibility checker to preference ranker."""
        checker = CompatibilityCheckerComponent()
        ranker = PreferenceRankerComponent(top_k=2)
        
        products = [
            {"name": "Product A", "price": "500 CHF", "rating": 4.5},
            {"name": "Product B", "price": "700 CHF", "rating": 4.2}
        ]
        
        checker_result, _ = checker.run(products, {}, "test")
        compatible_products = checker_result["compatible_products"]
        
        preferences = {"price": "below 600 CHF"}
        ranker_result, _ = ranker.run(compatible_products, preferences)
        
        assert "ranked_products" in ranker_result
        assert len(ranker_result["ranked_products"]) <= 2
