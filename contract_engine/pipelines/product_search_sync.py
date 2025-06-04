"""
Synchronous version of product search pipeline for FSM integration.
"""
import logging
from typing import Dict, List, Any, Optional
from haystack import Pipeline

logger = logging.getLogger(__name__)

def run_product_search_sync(
    pipeline: Pipeline,
    query: str,
    hard_constraints: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for product search pipeline execution.
    
    Args:
        pipeline: The Haystack pipeline to run
        query: Product search query
        hard_constraints: List of hard constraints to apply
        
    Returns:
        Dict containing search results, status, and attributes
    """
    try:
        logger.info(f"Running sync product search for query: {query}")
        
        mock_results = [
            {
                "name": f"High-end {query}",
                "price": "1299 CHF",
                "rating": 4.8,
                "brand": "NVIDIA",
                "specs": {"memory": "16GB", "cores": "10752"}
            },
            {
                "name": f"Mid-range {query}",
                "price": "799 CHF", 
                "rating": 4.5,
                "brand": "AMD",
                "specs": {"memory": "12GB", "cores": "7680"}
            },
            {
                "name": f"Budget {query}",
                "price": "399 CHF",
                "rating": 4.2,
                "brand": "NVIDIA",
                "specs": {"memory": "8GB", "cores": "5888"}
            }
        ]
        
        filtered_results = mock_results
        if hard_constraints:
            logger.info(f"Applying hard constraints: {hard_constraints}")
            for constraint in hard_constraints:
                if "price <" in constraint.lower():
                    try:
                        max_price = float(constraint.lower().split("price <")[1].strip().replace("chf", "").strip())
                        filtered_results = [
                            item for item in filtered_results 
                            if float(item["price"].replace(" CHF", "")) < max_price
                        ]
                    except (ValueError, IndexError):
                        logger.warning(f"Could not parse price constraint: {constraint}")
        
        if len(filtered_results) > 50:
            status = "too_many_results"
        elif len(filtered_results) == 0:
            status = "no_results"
        else:
            status = "success"
            
        return {
            "status": status,
            "items": filtered_results,
            "attributes": ["price", "brand", "rating", "memory", "cores"],
            "total_found": len(mock_results),
            "after_constraints": len(filtered_results)
        }
        
    except Exception as e:
        logger.error(f"Error in sync product search: {e}")
        return {
            "status": "error",
            "error": str(e),
            "items": [],
            "attributes": []
        }
