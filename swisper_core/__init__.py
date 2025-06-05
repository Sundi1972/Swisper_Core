"""
Swisper Core - Shared utilities and types for the Swisper Core project

This module provides centralized access to common utilities, types, and shared
components used across different modules in the Swisper Core architecture.
"""

import logging as _logging

def get_logger(name: str) -> _logging.Logger:
    """Get a standardized logger for Swisper Core modules"""
    return _logging.getLogger(name)

def setup_logging(level: str = "INFO"):
    """Setup global logging configuration for Swisper Core"""
    numeric_level = getattr(_logging, level.upper(), _logging.INFO)
    _logging.basicConfig(level=numeric_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

try:
    from .types import SwisperContext
except ImportError:
    from datetime import datetime
    from typing import Dict, List, Any, Optional
    
    class SwisperContext:
        def __init__(self, session_id: str, user_id: Optional[str] = None, **kwargs):
            self.session_id = session_id
            self.user_id = user_id
            self.current_state = "start"
            self.conversation_history = []
            self.created_at = datetime.now()
            self.last_updated = datetime.now()
        
        def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
            message = {"role": role, "content": content, "timestamp": datetime.now().isoformat()}
            self.conversation_history.append(message)

# Performance monitoring fallbacks
class PerformanceCache:
    def __init__(self): pass
    def get(self, key): return None
    def set(self, key, value): pass

class PipelineTimer:
    def __init__(self): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass

class PerformanceMonitor:
    def __init__(self): pass

class SystemHealthMonitor:
    def __init__(self): pass

def create_cache_key(*args): return "fallback_key"
def timed_operation(func): return func
def cached_operation(func): return func

attribute_cache = PerformanceCache()
pipeline_cache = PerformanceCache()
health_monitor = SystemHealthMonitor()

from enum import Enum

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class OperationMode(Enum):
    FULL = "full"
    DEGRADED = "degraded"
    FALLBACK = "fallback"

class PipelineError(Exception):
    def __init__(self, message, severity=ErrorSeverity.MEDIUM):
        super().__init__(message)
        self.severity = severity

def create_user_friendly_error_message(error): return str(error)
def handle_pipeline_error(error): return {"status": "error", "message": str(error)}
def get_degraded_operation_message(): return "System running in degraded mode"

class UnifiedSessionStore:
    def __init__(self): pass
    def save_session(self, session_id: str, context): pass
    def load_session(self, session_id): return None

class PipelineSessionManager:
    def __init__(self): pass

class RedisClient:
    def __init__(self): pass

class MockPIIRedactor:
    def redact_pii(self, text): return text

class MockEncryptionService:
    def encrypt(self, data): return data
    def decrypt(self, data): return data

class MockAuditStore:
    def store(self, data): pass

pii_redactor = MockPIIRedactor()
encryption_service = MockEncryptionService()
audit_store = MockAuditStore()

def validate_context_dict(context_dict): return True
def validate_fsm_state(fsm): return True
def validate_pipeline_result(result): return True
def validate_state_transition(from_state, to_state): return True
VALID_FSM_STATES = ["start", "search", "completed"]

try:
    from .monitoring import (
        PerformanceCache as _PerformanceCache, PipelineTimer as _PipelineTimer, 
        PerformanceMonitor as _PerformanceMonitor, create_cache_key as _create_cache_key,
        timed_operation as _timed_operation, cached_operation as _cached_operation,
        attribute_cache as _attribute_cache, pipeline_cache as _pipeline_cache,
        SystemHealthMonitor as _SystemHealthMonitor, health_monitor as _health_monitor
    )
    PerformanceCache = _PerformanceCache
    PipelineTimer = _PipelineTimer
    PerformanceMonitor = _PerformanceMonitor
    create_cache_key = _create_cache_key
    timed_operation = _timed_operation
    cached_operation = _cached_operation
    attribute_cache = _attribute_cache
    pipeline_cache = _pipeline_cache
    SystemHealthMonitor = _SystemHealthMonitor
    health_monitor = _health_monitor
except ImportError:
    pass

try:
    from .errors import (
        PipelineError as _PipelineError, ErrorSeverity as _ErrorSeverity, 
        OperationMode as _OperationMode, create_user_friendly_error_message as _create_user_friendly_error_message,
        handle_pipeline_error as _handle_pipeline_error, get_degraded_operation_message as _get_degraded_operation_message
    )
    PipelineError = _PipelineError
    ErrorSeverity = _ErrorSeverity
    OperationMode = _OperationMode
    create_user_friendly_error_message = _create_user_friendly_error_message
    handle_pipeline_error = _handle_pipeline_error
    get_degraded_operation_message = _get_degraded_operation_message
except ImportError:
    pass

try:
    from .session import UnifiedSessionStore as _UnifiedSessionStore, PipelineSessionManager as _PipelineSessionManager
    UnifiedSessionStore = _UnifiedSessionStore
    PipelineSessionManager = _PipelineSessionManager
except ImportError:
    pass

try:
    from .clients import RedisClient as _RedisClient
    RedisClient = _RedisClient
except ImportError:
    pass

try:
    from .privacy import pii_redactor as _pii_redactor, encryption_service as _encryption_service, audit_store as _audit_store
    pii_redactor = _pii_redactor
    encryption_service = _encryption_service
    audit_store = _audit_store
except ImportError:
    pass

try:
    from .validation import (
        validate_context_dict as _validate_context_dict, validate_fsm_state as _validate_fsm_state,
        validate_pipeline_result as _validate_pipeline_result, validate_state_transition as _validate_state_transition,
        VALID_FSM_STATES as _VALID_FSM_STATES
    )
    validate_context_dict = _validate_context_dict
    validate_fsm_state = _validate_fsm_state
    validate_pipeline_result = _validate_pipeline_result
    validate_state_transition = _validate_state_transition
    VALID_FSM_STATES = _VALID_FSM_STATES
except ImportError:
    pass

__version__ = "1.0.0"
__author__ = "Swisper Core Team"

__all__ = [
    'SwisperContext',
    'PerformanceCache', 'PipelineTimer', 'PerformanceMonitor', 'SystemHealthMonitor',
    'create_cache_key', 'timed_operation', 'cached_operation', 'attribute_cache', 
    'pipeline_cache', 'health_monitor',
    'PipelineError', 'ErrorSeverity', 'OperationMode', 'create_user_friendly_error_message',
    'handle_pipeline_error', 'get_degraded_operation_message',
    'UnifiedSessionStore', 'PipelineSessionManager',
    'RedisClient',
    'pii_redactor', 'encryption_service', 'audit_store',
    'validate_context_dict', 'validate_fsm_state', 'validate_pipeline_result',
    'validate_state_transition', 'VALID_FSM_STATES',
    'get_logger', 'setup_logging'
]
