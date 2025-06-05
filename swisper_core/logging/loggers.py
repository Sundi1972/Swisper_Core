"""
Standardized logging configuration for Swisper Core
"""
import logging
import os
from typing import Optional

def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a standardized logger for Swisper Core modules
    
    Args:
        name: Logger name (typically __name__)
        level: Optional log level override
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if level:
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(numeric_level)
    
    return logger

def setup_logging(level: str = "INFO", format_string: Optional[str] = None):
    """Setup global logging configuration for Swisper Core"""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    if format_string is None:
        format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    
    logging.basicConfig(
        level=numeric_level,
        format=format_string
    )
