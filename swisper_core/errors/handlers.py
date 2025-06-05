"""
Error handling functions for Swisper Core
"""

from typing import Dict, Any, Optional, Callable
from ..monitoring.health import OperationMode
from ..monitoring.health import health_monitor
from ..logging import get_logger

logger = get_logger(__name__)

def create_user_friendly_error_message(error: Exception, context: str = "") -> str:
    """Create user-friendly error messages"""
    error_messages = {
        "openai_api": "I'm having trouble with my AI analysis right now, but I can still help you find products using basic search and filtering.",
        "web_scraping": "I can't access detailed product specifications at the moment, but I can work with the basic product information available.",
        "product_search": "Product search is temporarily unavailable. Please try again in a few moments, or let me know if you'd like to browse by category.",
        "attribute_analysis": "I'm having trouble analyzing product attributes right now, but I can still help you compare products based on basic information."
    }
    
    error_str = str(error).lower()
    
    for service, message in error_messages.items():
        if service in error_str or service.replace("_", " ") in error_str:
            return f"{message} {context}".strip()
    
    return f"I'm experiencing some technical difficulties, but I'm still here to help you find the right product. {context}".strip()

def handle_pipeline_error(error: Exception, pipeline_name: str, fallback_function: Optional[Callable] = None) -> Dict[str, Any]:
    """Handle pipeline errors with fallback mechanisms"""
    logger.error(f"Pipeline error in {pipeline_name}: {error}")
    
    service_map = {
        "product_search_pipeline": "product_search",
        "preference_match_pipeline": "openai_api"
    }
    
    service = service_map.get(pipeline_name, "unknown")
    operation_mode = health_monitor.report_service_error(service, error)
    
    user_message = create_user_friendly_error_message(error, 
        "Let me try a different approach to help you.")
    
    if fallback_function:
        try:
            logger.info(f"Attempting fallback for {pipeline_name}")
            fallback_result = fallback_function()
            fallback_result.update({
                "status": "fallback",
                "operation_mode": operation_mode.value,
                "user_message": user_message,
                "original_error": str(error)
            })
            return fallback_result
        except Exception as fallback_error:
            logger.error(f"Fallback also failed for {pipeline_name}: {fallback_error}")
    
    return {
        "status": "error",
        "operation_mode": operation_mode.value,
        "user_message": user_message,
        "error": str(error),
        "pipeline": pipeline_name,
        "fallback_attempted": fallback_function is not None
    }

def get_degraded_operation_message(operation_mode: OperationMode) -> str:
    """Get message explaining current operation mode to user"""
    messages = {
        OperationMode.FULL: "",
        OperationMode.DEGRADED: "Note: Some advanced features are temporarily unavailable, but I can still help you find great products.",
        OperationMode.MINIMAL: "Note: I'm running in basic mode right now. I can help with simple product searches and comparisons."
    }
    return messages.get(operation_mode, "")
