"""
Synchronous version of product search pipeline for FSM integration.
"""
import logging
from typing import Dict, List, Any, Optional
from haystack import Pipeline
from tool_adapter.mock_google import google_shopping_search
from swisper_core import get_logger

logger = get_logger(__name__)

def run_product_search_sync(
    pipeline: Pipeline,
    query: str,
    hard_constraints: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Synchronous wrapper for product search pipeline execution using real SearchAPI.
    
    Args:
        pipeline: The Haystack pipeline to run
        query: Product search query
        hard_constraints: List of hard constraints to apply
        
    Returns:
        Dict containing search results, status, and attributes
    """
    try:
        logger.info(f"Running sync product search for query: {query}")
        
        search_results = google_shopping_search(query)
        
        transformed_results = []
        for item in search_results:
            if isinstance(item, dict) and "error" not in item:
                transformed_item = {
                    "name": item.get("name", ""),
                    "price": item.get("price", 0),
                    "rating": item.get("rating", 0),
                    "brand": item.get("brand", ""),
                    "specs": item.get("specs", {}),
                    "link": item.get("link", ""),
                    "thumbnail": item.get("thumbnail", "")
                }
                transformed_results.append(transformed_item)
        
        filtered_results = transformed_results
        if hard_constraints:
            logger.info(f"Applying hard constraints: {hard_constraints}")
            for constraint in hard_constraints:
                if "price <" in constraint.lower():
                    try:
                        max_price = float(constraint.lower().split("price <")[1].strip().replace("chf", "").strip())
                        filtered_results = [
                            item for item in filtered_results 
                            if isinstance(item.get("price"), (int, float)) and item["price"] < max_price
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
            "attributes": ["price", "brand", "rating", "name"],
            "total_found": len(transformed_results),
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
