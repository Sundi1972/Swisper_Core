"""
Error handling and exceptions for Swisper Core
"""

from .exceptions import PipelineError, ErrorSeverity
from ..monitoring.health import OperationMode, health_monitor
from .handlers import (
    create_user_friendly_error_message, handle_pipeline_error,
    get_degraded_operation_message
)

try:
    from ..handlers import (
        create_fallback_product_search, create_fallback_preference_ranking
    )
except ImportError:
    def create_fallback_product_search(query, max_results=10):
        return {"status": "fallback", "items": [], "query": query}
    
    def create_fallback_preference_ranking(products, preferences=None):
        if not products:
            return {"status": "no_products", "ranked_products": [], "scores": [], "ranking_method": "none"}
        return {"status": "fallback", "ranked_products": products[:3], "scores": [0.5] * min(3, len(products)), "ranking_method": "simple_fallback"}

__all__ = [
    'PipelineError', 'ErrorSeverity', 'OperationMode', 'health_monitor',
    'create_user_friendly_error_message', 'handle_pipeline_error',
    'get_degraded_operation_message', 'create_fallback_product_search',
    'create_fallback_preference_ranking'
]
