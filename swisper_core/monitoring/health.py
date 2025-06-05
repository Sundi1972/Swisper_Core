"""
System health monitoring for Swisper Core
"""

from typing import Dict
from enum import Enum
from ..logging import get_logger

logger = get_logger(__name__)

class OperationMode(Enum):
    """Operation modes for the system"""
    FULL = "full"
    DEGRADED = "degraded"
    MINIMAL = "minimal"
    
    def __eq__(self, other):
        if isinstance(other, OperationMode):
            return self.value == other.value
        return False
    
    def __hash__(self):
        return hash(self.value)

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
