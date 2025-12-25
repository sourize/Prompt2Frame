"""
Circuit breaker pattern implementation for external API calls.

This module provides a circuit breaker to prevent cascading failures
when external services (like Groq API) are experiencing issues.
"""

import time
import logging
from enum import Enum
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for external API calls.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing recovery, allow limited requests
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
            expected_exception: Exception type to catch
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func
            
        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Original exception from func
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise CircuitBreakerOpen(
                    f"Circuit breaker is OPEN. "
                    f"Wait {self.recovery_timeout}s before retry."
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try recovery."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit breaker recovered, now CLOSED")
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker OPENED after {self.failure_count} failures"
            )
    
    def reset(self):
        """Manually reset the circuit breaker."""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        logger.info("Circuit breaker manually reset to CLOSED")


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


# Global circuit breaker for Groq API
groq_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception
)


def with_circuit_breaker(circuit_breaker: CircuitBreaker):
    """
    Decorator to wrap function calls with circuit breaker.
    
    Usage:
        @with_circuit_breaker(groq_circuit_breaker)
        def call_groq_api():
            # API call here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return circuit_breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
