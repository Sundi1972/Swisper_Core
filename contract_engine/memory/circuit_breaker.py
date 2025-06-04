import logging
from typing import Callable, Any, Optional
from functools import wraps
import time
from enum import Enum
from contract_engine.error_handling import health_monitor, ErrorSeverity

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class RedisCircuitBreaker:
    """Circuit breaker for Redis operations with health monitoring integration"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.logger = logging.getLogger(__name__)
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.logger.info("Circuit breaker moving to HALF_OPEN state")
                else:
                    raise Exception("Circuit breaker is OPEN - Redis unavailable")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure(e)
                raise
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.logger.info("Circuit breaker reset to CLOSED state")
            health_monitor.report_service_recovery("redis")
    
    def _on_failure(self, error: Exception):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        self.logger.warning(f"Redis operation failed ({self.failure_count}/{self.failure_threshold}): {error}")
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.error(f"Circuit breaker opened after {self.failure_count} failures")
            health_monitor.report_service_error("redis", error)
    
    def get_state(self) -> CircuitState:
        """Get current circuit breaker state"""
        return self.state
    
    def reset(self):
        """Manually reset circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.logger.info("Circuit breaker manually reset")

redis_circuit_breaker = RedisCircuitBreaker()
