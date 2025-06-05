import pytest
from unittest.mock import patch, MagicMock
import time
from contract_engine.memory.circuit_breaker import RedisCircuitBreaker, CircuitState

def test_circuit_breaker_closed_state():
    """Test circuit breaker in closed state allows operations"""
    breaker = RedisCircuitBreaker(failure_threshold=3)
    
    @breaker
    def test_operation():
        return "success"
    
    result = test_operation()
    assert result == "success"
    assert breaker.get_state() == CircuitState.CLOSED

def test_circuit_breaker_failure_counting():
    """Test circuit breaker counts failures correctly"""
    breaker = RedisCircuitBreaker(failure_threshold=3)
    
    @breaker
    def failing_operation():
        raise Exception("Redis connection failed")
    
    for i in range(2):
        with pytest.raises(Exception):
            failing_operation()
        assert breaker.failure_count == i + 1
        assert breaker.get_state() == CircuitState.CLOSED
    
    with pytest.raises(Exception):
        failing_operation()
    assert breaker.get_state() == CircuitState.OPEN

def test_circuit_breaker_open_state():
    """Test circuit breaker in open state rejects operations"""
    breaker = RedisCircuitBreaker(failure_threshold=2)
    
    @breaker
    def failing_operation():
        raise Exception("Redis connection failed")
    
    for _ in range(2):
        with pytest.raises(Exception):
            failing_operation()
    
    assert breaker.get_state() == CircuitState.OPEN
    
    @breaker
    def another_operation():
        return "should not execute"
    
    with pytest.raises(Exception, match="Circuit breaker is OPEN"):
        another_operation()

def test_circuit_breaker_half_open_recovery():
    """Test circuit breaker recovery through half-open state"""
    breaker = RedisCircuitBreaker(failure_threshold=2, recovery_timeout=1)
    
    @breaker
    def failing_operation():
        raise Exception("Redis connection failed")
    
    @breaker
    def successful_operation():
        return "success"
    
    for _ in range(2):
        with pytest.raises(Exception):
            failing_operation()
    
    assert breaker.get_state() == CircuitState.OPEN
    
    time.sleep(1.1)
    
    result = successful_operation()
    assert result == "success"
    assert breaker.get_state() == CircuitState.CLOSED

@patch('contract_engine.memory.circuit_breaker.health_monitor')
def test_circuit_breaker_health_monitoring_integration(mock_health_monitor):
    """Test circuit breaker integrates with health monitoring"""
    breaker = RedisCircuitBreaker(failure_threshold=2, recovery_timeout=1)
    
    @breaker
    def failing_operation():
        raise Exception("Redis connection failed")
    
    @breaker
    def successful_operation():
        return "success"
    
    for _ in range(2):
        with pytest.raises(Exception):
            failing_operation()
    
    mock_health_monitor.report_service_error.assert_called_once()
    
    time.sleep(1.1)
    successful_operation()
    
    mock_health_monitor.report_service_recovery.assert_called_with("redis")

def test_circuit_breaker_manual_reset():
    """Test manual circuit breaker reset"""
    breaker = RedisCircuitBreaker(failure_threshold=2)
    
    @breaker
    def failing_operation():
        raise Exception("Redis connection failed")
    
    for _ in range(2):
        with pytest.raises(Exception):
            failing_operation()
    
    assert breaker.get_state() == CircuitState.OPEN
    
    breaker.reset()
    assert breaker.get_state() == CircuitState.CLOSED
    assert breaker.failure_count == 0

def test_circuit_breaker_concurrent_operations():
    """Test circuit breaker behavior with concurrent operations"""
    breaker = RedisCircuitBreaker(failure_threshold=3)
    
    @breaker
    def mixed_operation(should_fail=False):
        if should_fail:
            raise Exception("Operation failed")
        return "success"
    
    assert mixed_operation(False) == "success"
    
    with pytest.raises(Exception):
        mixed_operation(True)
    
    assert mixed_operation(False) == "success"
    assert breaker.get_state() == CircuitState.CLOSED
