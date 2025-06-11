#!/usr/bin/env python3
"""
Configure detailed logging for debugging preference extraction
"""
import logging
import sys

def setup_debug_logging():
    """Set up comprehensive logging for debugging"""
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    
    loggers = [
        'contract_engine.llm_helpers',
        'contract_engine.contract_engine',
        'root'
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(console_handler)
        logger.propagate = False

if __name__ == "__main__":
    setup_debug_logging()
    print("✅ Debug logging configured")
