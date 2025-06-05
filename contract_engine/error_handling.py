"""
Fallback functions for error handling in Swisper Core Pipeline Architecture.

This module provides fallback mechanisms for when pipelines fail.
"""

from typing import Dict, List, Any, Optional
from swisper_core import get_logger

logger = get_logger(__name__)

def create_fallback_product_search(query: str, max_results: int = 10) -> Dict[str, Any]:
    """Fallback product search when main pipeline fails"""
    try:
        fallback_products = [
            {
                "name": f"Basic {query} Option 1",
                "price": "199 CHF",
                "rating": "4.0",
                "description": f"A reliable {query} with good basic features",
                "availability": "In Stock",
                "source": "fallback_search"
            },
            {
                "name": f"Budget {query} Option 2", 
                "price": "149 CHF",
                "rating": "3.8",
                "description": f"An affordable {query} option",
                "availability": "In Stock",
                "source": "fallback_search"
            },
            {
                "name": f"Premium {query} Option 3",
                "price": "299 CHF", 
                "rating": "4.5",
                "description": f"A high-quality {query} with advanced features",
                "availability": "In Stock",
                "source": "fallback_search"
            }
        ]
        
        return {
            "status": "fallback",
            "items": fallback_products[:max_results],
            "attributes": ["price", "rating", "availability"],
            "total_found": len(fallback_products),
            "message": "Using basic product search due to service limitations"
        }
    except Exception as e:
        logger.error(f"Even fallback product search failed: {e}")
        return {
            "status": "error",
            "items": [],
            "attributes": [],
            "error": str(e),
            "message": "Unable to search for products at this time"
        }

def create_fallback_preference_ranking(products: List[Dict], preferences: Optional[Dict] = None) -> Dict[str, Any]:
    """Fallback preference ranking when pipeline fails"""
    try:
        if not products:
            return {
                "status": "no_products",
                "ranked_products": [],
                "scores": [],
                "ranking_method": "none"
            }
        
        def simple_score(product):
            try:
                rating = float(product.get("rating", "0").replace("★", "").strip())
                price_str = product.get("price", "999").replace("CHF", "").replace(",", "").strip()
                price = float(price_str) if price_str.replace(".", "").isdigit() else 999
                
                rating_score = rating / 5.0
                price_score = max(0, 1 - (price / 1000))
                
                return (rating_score * 0.6) + (price_score * 0.4)
            except:
                return 0.5
        
        scored_products = [(product, simple_score(product)) for product in products]
        scored_products.sort(key=lambda x: x[1], reverse=True)
        
        top_products = scored_products[:3]
        
        return {
            "status": "fallback",
            "ranked_products": [p[0] for p in top_products],
            "scores": [p[1] for p in top_products],
            "ranking_method": "simple_fallback",
            "total_processed": len(products),
            "message": "Using basic ranking due to service limitations"
        }
    except Exception as e:
        logger.error(f"Fallback preference ranking failed: {e}")
        return {
            "status": "error",
            "ranked_products": [],
            "scores": [],
            "error": str(e),
            "ranking_method": "none"
        }
