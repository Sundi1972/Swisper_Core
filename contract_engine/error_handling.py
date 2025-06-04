"""
Error Handling and Resilience Module for Swisper Core Pipeline Architecture.

This module provides comprehensive error handling, fallback mechanisms, and graceful
degradation for the FSM and Pipeline architecture when external services are unavailable.
"""

import logging
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class OperationMode(Enum):
    """Operation modes for the system"""
    FULL = "full"           # All services available
    DEGRADED = "degraded"   # Some services unavailable, using fallbacks
    MINIMAL = "minimal"     # Only basic functionality available

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"         # Minor issues, system continues normally
    MEDIUM = "medium"   # Some functionality affected, fallbacks used
    HIGH = "high"       # Major issues, degraded operation
    CRITICAL = "critical"  # System barely functional

class PipelineError(Exception):
    """Custom exception for pipeline errors"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 component: str = None, fallback_available: bool = True):
        super().__init__(message)
        self.severity = severity
        self.component = component
        self.fallback_available = fallback_available

class SystemHealthMonitor:
    """Monitor system health and determine operation mode"""
    
    def __init__(self):
        self.operation_mode = OperationMode.FULL
        self.service_status = {
            "openai_api": True,
            "web_scraping": True,
            "product_search": True,
            "attribute_analysis": True
        }
        self.error_counts = {service: 0 for service in self.service_status}
        self.max_errors_before_degradation = 3
    
    def report_service_error(self, service: str, error: Exception) -> OperationMode:
        """Report a service error and update operation mode"""
        if service in self.error_counts:
            self.error_counts[service] += 1
            
            if self.error_counts[service] >= self.max_errors_before_degradation:
                self.service_status[service] = False
                logger.warning(f"Service {service} marked as unavailable after {self.error_counts[service]} errors")
        
        self._update_operation_mode()
        return self.operation_mode
    
    def report_service_recovery(self, service: str):
        """Report service recovery"""
        if service in self.service_status:
            self.service_status[service] = True
            self.error_counts[service] = 0
            logger.info(f"Service {service} recovered")
            self._update_operation_mode()
    
    def _update_operation_mode(self):
        """Update operation mode based on service status"""
        unavailable_services = [s for s, status in self.service_status.items() if not status]
        
        if not unavailable_services:
            self.operation_mode = OperationMode.FULL
        elif len(unavailable_services) <= 2:
            self.operation_mode = OperationMode.DEGRADED
        else:
            self.operation_mode = OperationMode.MINIMAL
        
        logger.info(f"Operation mode updated to: {self.operation_mode.value}")
    
    def get_operation_mode(self) -> OperationMode:
        """Get current operation mode"""
        return self.operation_mode
    
    def is_service_available(self, service: str) -> bool:
        """Check if a service is available"""
        return self.service_status.get(service, False)

health_monitor = SystemHealthMonitor()

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

def handle_pipeline_error(error: Exception, pipeline_name: str, fallback_function=None) -> Dict[str, Any]:
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

def create_fallback_preference_ranking(products: List[Dict], preferences: Dict = None) -> Dict[str, Any]:
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
                
                rating_score = rating / 5.0  # Assuming 5-star scale
                price_score = max(0, 1 - (price / 1000))  # Assuming max reasonable price 1000
                
                return (rating_score * 0.6) + (price_score * 0.4)
            except:
                return 0.5  # Default score
        
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
