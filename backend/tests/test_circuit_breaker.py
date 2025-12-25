"""
Unit tests for circuit breaker functionality.

Tests cover state transitions, failure counting, and recovery.
"""

import pytest
import time
from src.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpen


class TestCircuitBreaker:
    """Test circuit breaker logic."""
    
    def test_initial_state_closed(self):
        """Test that circuit starts in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        assert cb.state == CircuitState.CLOSED
    
    def test_successful_calls_keep_circuit_closed(self):
        """Test that successful calls don't open circuit."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        
        def success_func():
            return "success"
        
        for i in range(5):
            result = cb.call(success_func)
            assert result == "success"
            assert cb.state == CircuitState.CLOSED
    
    def test_failures_open_circuit(self):
        """Test that repeated failures open the circuit."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        
        def failing_func():
            raise ValueError("Test error")
        
        # Make failures up to threshold
        for i in range(3):
            with pytest.raises(ValueError):
                cb.call(failing_func)
        
        # Circuit should be open
        assert cb.state == CircuitState.OPEN
    
    def test_open_circuit_rejects_calls(self):
        """Test that open circuit rejects calls immediately."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10)
        
        def failing_func():
            raise ValueError("Test error")
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_func)
        
        # Next call should be rejected immediately
        with pytest.raises(CircuitBreakerOpen):
            cb.call(failing_func)
    
    def test_half_open_after_timeout(self):
        """Test that circuit enters HALF_OPEN after recovery timeout."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        
        def failing_func():
            raise ValueError("Test error")
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(1.1)
        
        # Next call should attempt (HALF_OPEN)
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitState.CLOSED
    
    def test_reset_circuit(self):
        """Test manual circuit reset."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10)
        
        def failing_func():
            raise ValueError("Test error")
        
        # Open the circuit
        for i in range(2):
            with pytest.raises(ValueError):
                cb.call(failing_func)
        
        assert cb.state == CircuitState.OPEN
        
        # Reset
        cb.reset()
        
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
