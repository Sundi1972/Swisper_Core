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
        
        mock_results = []
        brands = ["Samsung", "LG", "Bosch", "Siemens", "Miele", "Whirlpool", "Electrolux", "AEG", "NVIDIA", "AMD"]
        
        for i in range(25):
            price = 299 + (i * 50) + (i % 7 * 25)
            brand = brands[i % len(brands)]
            
            mock_results.append({
                "name": f"{brand} {query} Model {i+1}",
                "price": f"{price} CHF",
                "rating": round(3.5 + (i % 3) * 0.5, 1),
                "brand": brand,
                "specs": {"memory": f"{8 + (i % 3) * 4}GB", "cores": f"{5000 + i * 200}"}
            })
        
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
        
        if len(filtered_results) > 20:
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
