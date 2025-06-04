import json
import os
import requests
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Determine path to mock_gpus.json relative to this file or an absolute path
# This assumes tool_adapter is one level down from repository root, and tests is also one level down.
MOCK_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'tests', 'data', 'mock_gpus.json')


def real_google_shopping(q: str) -> List[Dict[str, Any]]:
    """Real SearchAPI.io Google Shopping integration"""
    api_key = os.environ.get("SEARCHAPI_API_KEY")
    if not api_key:
        logger.warning("SEARCHAPI_API_KEY not found, falling back to mock data")
        return mock_google_shopping(q)
    
    try:
        url = "https://www.searchapi.io/api/v1/search"
        params = {
            "engine": "google_shopping",
            "q": q,
            "api_key": api_key,
            "gl": "ch",
            "num": 20
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        shopping_results = data.get("shopping_results", [])
        transformed_results = []
        
        for item in shopping_results:
            transformed_item = {
                "name": item.get("title", ""),
                "brand": item.get("seller", ""),
                "price": item.get("extracted_price", 0),
                "rating": item.get("rating", 0),
                "reviews": item.get("reviews", 0),
                "link": item.get("link", ""),
                "thumbnail": item.get("thumbnail", "")
            }
            transformed_results.append(transformed_item)
        
        logger.info(f"SearchAPI returned {len(transformed_results)} products for query: {q}")
        return transformed_results
        
    except Exception as e:
        logger.error(f"SearchAPI error for query '{q}': {e}", exc_info=True)
        logger.info("Falling back to mock data")
        return mock_google_shopping(q)

def mock_google_shopping(q: str) -> List[Dict[str, Any]]:
    logger.info("Mock Google Shopping called with query: %s", q)
    try:
        absolute_mock_data_path = os.path.abspath(MOCK_DATA_PATH)
        logger.debug("Attempting to load mock GPU data from: %s", absolute_mock_data_path)

        if not os.path.exists(absolute_mock_data_path):
            logger.error("Mock data file not found at %s. Query: '%s'", absolute_mock_data_path, q)
            # Try an alternative common path if running from repository root (e.g. if CWD is repo root)
            alt_path = os.path.join("tests", "data", "mock_gpus.json") 
            if os.path.exists(alt_path):
                absolute_mock_data_path = alt_path
                logger.info("Found mock data at alternative relative path: %s", alt_path)
            else:
                 logger.error("Alternative mock data file not found at %s either.", alt_path)
                 return [{"error": "Mock data file not found.", "query": q}]

        with open(absolute_mock_data_path, 'r') as f:
            all_products = json.load(f)
        
        # Basic filtering: return products containing the query string (case-insensitive) in name or brand
        filtered_products = [
            p for p in all_products 
            if (q.lower() in p.get("name", "").lower()) or \
               (q.lower() in p.get("brand", "").lower())
        ]
        
        if not filtered_products and q: # If query doesn't match anything and query was not empty
            logger.warning("No direct match for query '%s' in mock data. Generating synthetic products for testing.", q)
            return _generate_synthetic_products(q, 25)
        elif not q: # If query is empty, return all products or a subset
             logger.warning("Empty query received. Returning all mock products.")
             return all_products


        logger.info("Returning %d mock products for query: %s", len(filtered_products), q)
        return filtered_products

    except FileNotFoundError: # This might be redundant if os.path.exists is checked first
        logger.error("Mock data file not found at %s (resolved to %s). Query: '%s'", MOCK_DATA_PATH, absolute_mock_data_path, q)
        return [{"error": "Mock data file not found.", "query": q}]
    except json.JSONDecodeError:
        logger.error("Error decoding JSON from %s. Query: '%s'", MOCK_DATA_PATH, q)
        return [{"error": "Error decoding mock data.", "query": q}]
    except Exception as e:
        logger.error("An unexpected error occurred in mock_google_shopping: %s", e, exc_info=True)
        return [{"error": f"Unexpected error: {str(e)}", "query": q}]

def google_shopping_search(q: str, **kwargs) -> List[Dict[str, Any]]:
    """Main search function - uses real API with mock fallback"""
    SEARCHAPI_API_KEY = os.environ.get("SEARCHAPI_API_KEY")
    logger.info("🔑 API Key status", extra={"searchapi_configured": bool(SEARCHAPI_API_KEY)})
    
    if SEARCHAPI_API_KEY:
        logger.info("🌐 Using real SearchAPI.io", extra={"query": q})
        return real_google_shopping(q, **kwargs)
    else:
        logger.warning("⚠️ Using mock data - SEARCHAPI_API_KEY not configured", extra={"query": q})
        return mock_google_shopping(q, **kwargs)

def mock_google_shopping_adapter(q: str) -> List[Dict[str, Any]]:
    return mock_google_shopping(q=q)

adapter_map = {
    "google_shopping": google_shopping_search,
    "mock_google_shopping": mock_google_shopping_adapter
}

def route(name: str, params: dict):
    if name in adapter_map:
        # Ensure all required parameters for the specific tool are passed.
        # For google_shopping and mock_google_shopping, 'q' is required.
        # This basic check can be expanded or made more generic if needed.
        if name in ["google_shopping", "mock_google_shopping"] and 'q' not in params:
            logger.error("Query parameter 'q' missing for tool %s", name)
            raise TypeError(f"Missing required parameter 'q' for tool {name}") # TypeError for missing args
        
        try:
            return adapter_map[name](**params)
        except TypeError as te: # Catching issues like unexpected keyword arguments if params don't match function signature
            logger.error("TypeError calling tool %s with params %s: %s", name, params, te, exc_info=True)
            # Re-raise as a more specific error or handle as appropriate
            raise TypeError(f"Invalid parameters for tool {name}: {te}")

    else:
        logger.error("Unknown tool name in mock_adapter.route: %s", name)
        raise ValueError(f"Unknown tool: {name}")

def _generate_synthetic_products(query: str, count: int = 25) -> List[Dict[str, Any]]:
    """Generate synthetic products for testing when no mock data matches"""
    products = []
    brands = ["Samsung", "LG", "Bosch", "Siemens", "Miele", "Whirlpool", "Electrolux", "AEG"]
    
    for i in range(count):
        price = 299 + (i * 50) + (i % 7 * 25)  # Varied pricing
        brand = brands[i % len(brands)]
        
        product = {
            "name": f"{brand} {query.title()} Model {i+1}",
            "brand": brand,
            "price": f"{price} CHF",
            "rating": round(3.5 + (i % 3) * 0.5, 1),
            "reviews": 50 + (i * 10),
            "link": f"https://example.com/product-{i+1}",
            "thumbnail": f"https://example.com/thumb-{i+1}.jpg",
            "source": "synthetic_test_data"
        }
        products.append(product)
    
    return products
