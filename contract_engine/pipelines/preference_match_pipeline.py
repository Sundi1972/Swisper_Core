"""
Preference Match Pipeline - Data plane component for preference matching.

This pipeline handles the stateless data transformation for preference matching:
1. SpecScraper Component (enhance with web data)
2. CompatibilityChecker Component (hard constraints validation)  
3. PreferenceRanker Component (soft prefs → LLM score 0-1, return top 3)
"""

import logging
from haystack.pipelines import Pipeline
from ..haystack_components import SpecScraperComponent, CompatibilityCheckerComponent, PreferenceRankerComponent

logger = logging.getLogger(__name__)

def create_preference_match_pipeline(top_k: int = 3) -> Pipeline:
    """
    Create the preference match pipeline for contract engine.
    
    Args:
        top_k: Number of top products to return (default: 3)
    
    Returns:
        Pipeline: Configured pipeline for preference matching and ranking
    """
    pipeline = Pipeline()
    
    # Node 1: Spec Scraper (enhance with web data)
    scraper_component = SpecScraperComponent()
    pipeline.add_node(component=scraper_component, name="scrape_specs", inputs=["Query"])
    
    checker_component = CompatibilityCheckerComponent()
    pipeline.add_node(component=checker_component, name="check_compat", inputs=["scrape_specs"])
    
    ranker_component = PreferenceRankerComponent(top_k=top_k)
    pipeline.add_node(component=ranker_component, name="rank_prefs", inputs=["check_compat"])
    
    logger.info(f"Preference match pipeline created successfully with top_k={top_k}")
    return pipeline

async def run_preference_match(pipeline: Pipeline, products: list, preferences: dict, 
                             constraints: dict = None, context: str = "") -> dict:
    """
    Run the preference match pipeline with given parameters.
    
    Args:
        pipeline: The preference match pipeline
        products: List of products to process (≤50 items from product search)
        preferences: User soft preferences dict
        constraints: Hard constraints dict (optional)
        context: Product context for spec scraping
        
    Returns:
        dict: Pipeline result with ranked products, scores, and metadata
    """
    try:
        if not products:
            return {
                "status": "no_products",
                "ranked_products": [],
                "scores": [],
                "ranking_method": "none",
                "message": "No products provided for preference matching"
            }
        
        if len(products) > 50:
            logger.warning(f"Too many products for preference matching: {len(products)}, truncating to 50")
            products = products[:50]
        
        result = pipeline.run(
            query=products,
            constraints=constraints or {},
            preferences=preferences
        )
        
        final_result = result.get("rank_prefs", {})
        
        if "ranked_products" not in final_result:
            logger.error("Pipeline did not return ranked_products")
            return _fallback_preference_match(products, preferences)
        
        final_result["status"] = "success"
        final_result["total_processed"] = len(products)
        final_result["preferences_applied"] = len(preferences) if preferences else 0
        
        logger.info(f"Preference match completed: {len(final_result.get('ranked_products', []))} products ranked")
        return final_result
            
    except Exception as e:
        logger.error(f"Preference match pipeline failed: {e}")
        return _fallback_preference_match(products, preferences, error=str(e))

def _fallback_preference_match(products: list, preferences: dict, error: str = None) -> dict:
    """
    Fallback preference matching when pipeline fails.
    
    Args:
        products: List of products to rank
        preferences: User preferences (may be ignored in fallback)
        error: Error message if pipeline failed
        
    Returns:
        dict: Fallback ranking result
    """
    try:
        ranked_products = []
        scores = []
        
        def safe_float(value, default=0):
            try:
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str):
                    return float(value.replace("CHF", "").replace(",", "").strip())
                return default
            except (ValueError, AttributeError):
                return default
        
        sorted_products = sorted(
            products,
            key=lambda p: (
                -safe_float(p.get("rating", 0)),  # Higher rating first
                safe_float(p.get("price", "999999"), 999999)  # Lower price first
            )
        )
        
        for i, product in enumerate(sorted_products[:3]):
            ranked_products.append(product)
            scores.append(max(0.5, 1.0 - (i * 0.1)))
        
        result = {
            "status": "fallback" if error else "success",
            "ranked_products": ranked_products,
            "scores": scores,
            "ranking_method": "fallback",
            "total_processed": len(products),
            "preferences_applied": 0,
            "message": f"Used fallback ranking due to: {error}" if error else "Used simple fallback ranking"
        }
        
        if error:
            result["error"] = error
            
        logger.info(f"Fallback preference match completed: {len(ranked_products)} products ranked")
        return result
        
    except Exception as fallback_error:
        logger.error(f"Even fallback preference matching failed: {fallback_error}")
        return {
            "status": "error",
            "ranked_products": [],
            "scores": [],
            "ranking_method": "none",
            "total_processed": 0,
            "preferences_applied": 0,
            "error": f"Complete failure: {fallback_error}",
            "message": "Unable to rank products due to system error"
        }

def get_pipeline_info(pipeline: Pipeline) -> dict:
    """
    Get information about the preference match pipeline structure.
    
    Args:
        pipeline: The preference match pipeline
        
    Returns:
        dict: Pipeline structure information
    """
    return {
        "nodes": list(pipeline.graph.nodes()),
        "edges": list(pipeline.graph.edges()),
        "node_count": len(pipeline.graph.nodes()),
        "pipeline_type": "preference_match",
        "components": {
            "scrape_specs": "SpecScraperComponent",
            "check_compat": "CompatibilityCheckerComponent", 
            "rank_prefs": "PreferenceRankerComponent"
        }
    }
