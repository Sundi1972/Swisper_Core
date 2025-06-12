"""
Exception classes for Swisper Core
"""

from typing import Optional
from enum import Enum

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PipelineError(Exception):
    """Custom exception for pipeline errors"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                 component: Optional[str] = None, fallback_available: bool = True):
        super().__init__(message)
        self.severity = severity
        self.component = component
        self.fallback_available = fallback_available
