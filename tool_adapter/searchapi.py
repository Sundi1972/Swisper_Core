import requests
import logging
import os
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def searchapi_web_search(query: str, api_key: str = None) -> List[Dict[str, Any]]:
    """Call SearchAPI.io for web search results
    
    Args:
        query: Search query string
        api_key: SearchAPI.io API key (optional, will use env var if not provided)
    
    Returns:
        List of search result dictionaries
    """
    if not api_key:
        api_key = os.getenv("SearchAPI_API_Key")
    
    if not api_key:
        logger.warning("No SearchAPI_API_Key found, returning mock results")
        return _get_mock_search_results(query)
    
    try:
        response = requests.get(
            "https://www.searchapi.io/api/v1/search",
            params={
                "q": query,
                "engine": "google",
                "num": 10,
                "gl": "us",
                "hl": "en"
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        organic_results = data.get("organic_results", [])
        filtered_results = [
            r for r in organic_results 
            if not r.get("is_ad", False) and not r.get("sponsored", False)
        ]
        
        logger.info(f"SearchAPI returned {len(filtered_results)} organic results for query: {query}")
        return filtered_results
        
    except requests.exceptions.RequestException as e:
        logger.error(f"SearchAPI request error for query '{query}': {e}")
        return [{"error": f"Request error: {str(e)}", "query": query}]
    except Exception as e:
        logger.error(f"SearchAPI error for query '{query}': {e}")
        return [{"error": str(e), "query": query}]


def _get_mock_search_results(query: str) -> List[Dict[str, Any]]:
    """Return mock search results for development/testing"""
    return [
        {
            "title": f"Current Information about {query}",
            "link": "https://example.com/news1",
            "snippet": f"Latest news and updates about {query}. This mock result provides current information for testing purposes.",
            "position": 1,
            "source": "Example News"
        },
        {
            "title": f"Recent Developments in {query}",
            "link": "https://news.example.org/article2",
            "snippet": f"Breaking news and recent developments related to {query}. Updated information from reliable sources.",
            "position": 2,
            "source": "Example News Org"
        },
        {
            "title": f"Analysis: {query}",
            "link": "https://analysis.com/report3",
            "snippet": f"In-depth analysis and expert commentary on {query}. Comprehensive coverage of the topic.",
            "position": 3,
            "source": "Analysis.com"
        }
    ]


adapter_map = {
    "searchapi_web_search": searchapi_web_search
}


def route(name: str, params: dict):
    """Route tool calls to appropriate adapter functions
    
    Args:
        name: Tool name to route to
        params: Parameters to pass to the tool
    
    Returns:
        Result from the tool function
    
    Raises:
        TypeError: If required parameters are missing
        ValueError: If tool name is unknown
    """
    if name in adapter_map:
        if name == "searchapi_web_search" and 'query' not in params:
            logger.error("Query parameter 'query' missing for tool %s", name)
            raise TypeError(f"Missing required parameter 'query' for tool {name}")
        
        try:
            return adapter_map[name](**params)
        except TypeError as te:
            logger.error("TypeError calling tool %s with params %s: %s", name, params, te, exc_info=True)
            raise TypeError(f"Invalid parameters for tool {name}: {te}")
    else:
        logger.error("Unknown tool name in searchapi adapter route: %s", name)
        raise ValueError(f"Unknown tool: {name}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    
    test_query = "Who are the new German ministers 2025"
    logger.info(f"Testing SearchAPI adapter with query: '{test_query}'")
    
    try:
        results = searchapi_web_search(test_query)
        logger.info(f"Received {len(results)} results")
        
        for i, result in enumerate(results[:3]):
            logger.info(f"Result {i+1}: {result.get('title', 'No title')}")
            logger.info(f"  Link: {result.get('link', 'No link')}")
            logger.info(f"  Snippet: {result.get('snippet', 'No snippet')[:100]}...")
    
    except Exception as e:
        logger.error(f"Error testing SearchAPI adapter: {e}", exc_info=True)
