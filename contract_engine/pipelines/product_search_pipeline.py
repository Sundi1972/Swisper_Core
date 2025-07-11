"""
Product Search Pipeline - Data plane component for product discovery.

This pipeline handles the stateless data transformation for product search:
1. Search Component (Google Shopping ≤100 items)
2. Attribute Analyzer (detect key attributes & ranges)  
3. Result Limiter (if ≤50 pass, else return too_many_results)
"""

from haystack.pipelines import Pipeline
from ..haystack_components import MockGoogleShoppingComponent, AttributeAnalyzerComponent, ResultLimiterComponent
from swisper_core.errors import handle_pipeline_error
from swisper_core.monitoring import health_monitor
from swisper_core import get_logger

logger = get_logger(__name__)

def create_product_search_pipeline() -> Pipeline:
    """
    Create the product search pipeline for contract engine.
    
    Returns:
        Pipeline: Configured pipeline for product search and analysis
    """
    pipeline = Pipeline()
    
    search_component = MockGoogleShoppingComponent()
    pipeline.add_node(component=search_component, name="search", inputs=["Query"])
    
    analyzer_component = AttributeAnalyzerComponent()
    pipeline.add_node(component=analyzer_component, name="analyze_attributes", inputs=["search"])
    
    # Node 3: Result Limiter (if ≤50 pass, else return too_many_results)
    limiter_component = ResultLimiterComponent(max_results=50)
    pipeline.add_node(component=limiter_component, name="limit_results", inputs=["analyze_attributes"])
    
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
        if not health_monitor.is_service_available("product_search"):
            logger.warning("Product search service unavailable, using fallback")
            from swisper_core.errors import create_fallback_product_search
            return create_fallback_product_search(query, max_results=50)
        
        result = pipeline.run(query=query)
        
        final_result = result.get("limit_results", {})
        
        if not isinstance(final_result, dict):
            final_result = {"status": "ok", "items": [], "attributes": []}
        
        health_monitor.report_service_recovery("product_search")
        
        return final_result
            
    except Exception as e:
        logger.error(f"Product search pipeline failed: {e}")
        
        def fallback():
            from swisper_core.errors import create_fallback_product_search
            return create_fallback_product_search(query, max_results=50)
        
        return handle_pipeline_error(e, "product_search_pipeline", fallback)
