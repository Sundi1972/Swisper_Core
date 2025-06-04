"""
Product Search Pipeline - Data plane component for product discovery.

This pipeline handles the stateless data transformation for product search:
1. Search Component (Google Shopping ≤100 items)
2. Attribute Analyzer (detect key attributes & ranges)  
3. Result Limiter (if ≤50 pass, else return too_many_results)
"""

import logging
from haystack.pipelines import Pipeline
from ..haystack_components import MockGoogleShoppingComponent, AttributeAnalyzerComponent, ResultLimiterComponent

logger = logging.getLogger(__name__)

def create_product_search_pipeline() -> Pipeline:
    """
    Create the product search pipeline for contract engine.
    
    Returns:
        Pipeline: Configured pipeline for product search and analysis
    """
    pipeline = Pipeline()
    
    search_component = MockGoogleShoppingComponent()
    pipeline.add_node("search", search_component, inputs=["Query"])
    
    analyzer_component = AttributeAnalyzerComponent()
    pipeline.add_node("analyze_attributes", analyzer_component, inputs=["search"])
    
    # Node 3: Result Limiter (if ≤50 pass, else return too_many_results)
    limiter_component = ResultLimiterComponent(max_results=50)
    pipeline.add_node("limit_results", limiter_component, inputs=["analyze_attributes"])
    
    logger.info("Product search pipeline created successfully")
    return pipeline

async def run_product_search(pipeline: Pipeline, query: str, hard_constraints: list = None) -> dict:
    """
    Run the product search pipeline with given parameters.
    
    Args:
        pipeline: The product search pipeline
        query: Product search query
        hard_constraints: List of hard constraints to apply
        
    Returns:
        dict: Pipeline result with status, items, and attributes
    """
    try:
        result = pipeline.run(
            query=query,
            hard_constraints=hard_constraints or []
        )
        
        final_result = result.get("limit_results", {})
        
        return final_result
            
    except Exception as e:
        logger.error(f"Product search pipeline failed: {e}")
        return {
            "status": "error",
            "items": [],
            "attributes": [],
            "error": str(e)
        }
