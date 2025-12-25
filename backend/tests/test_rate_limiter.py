"""
Unit tests for rate limiting functionality.

Tests cover per-IP tracking, sliding windows, and rate limit enforcement.
"""

import pytest
import time
from src.rate_limiter import SlidingWindowRateLimiter


class TestRateLimiter:
    """Test rate limiting logic."""
    
    def test_allows_requests_under_limit(self):
        """Test that requests under limit are allowed."""
        limiter = SlidingWindowRateLimiter()
        
        for i in range(4):
            is_allowed, limit_name, retry_after = limiter.check_rate_limit("192.168.1.1")
            assert is_allowed is True
            assert limit_name is None
    
    def test_blocks_requests_over_minute_limit(self):
        """Test that >5 requests per minute are blocked."""
        limiter = SlidingWindowRateLimiter()
        
        # Make 5 requests (should all pass)
        for i in range(5):
            is_allowed, _, _ = limiter.check_rate_limit("192.168.1.1")
            assert is_allowed is True
        
        # 6th request should be blocked
        is_allowed, limit_name, retry_after = limiter.check_rate_limit("192.168.1.1")
        assert is_allowed is False
        assert limit_name == "minute"
        assert retry_after > 0
    
    def test_different_ips_tracked_separately(self):
        """Test that different IPs have separate limits."""
        limiter = SlidingWindowRateLimiter()
        
        # IP1 makes 5 requests
        for i in range(5):
            is_allowed, _, _ = limiter.check_rate_limit("192.168.1.1")
            assert is_allowed is True
        
        # IP2 should still be allowed
        is_allowed, _, _ = limiter.check_rate_limit("192.168.1.2")
        assert is_allowed is True
    
    def test_cleanup_old_requests(self):
        """Test that old requests are cleaned up."""
        limiter = SlidingWindowRateLimiter()
        
        # Make requests
        for i in range(3):
            limiter.check_rate_limit("192.168.1.1")
        
        # Verify requests are tracked
        assert len(limiter._requests["192.168.1.1"]) == 3
        
        # Simulate time passing (cleanup happens on next check)
        # Cleanup removes requests older than 1 hour
        current_time = time.time()
        limiter._requests["192.168.1.1"] = [current_time - 7200]  # 2 hours ago
        
        # Next check should cleanup
        limiter.check_rate_limit("192.168.1.1")
        
        # Old request should be gone, new one added
        assert len(limiter._requests["192.168.1.1"]) == 1
    
    def test_get_stats(self):
        """Test rate limiter statistics."""
        limiter = SlidingWindowRateLimiter()
        
        # Make some requests
        limiter.check_rate_limit("192.168.1.1")
        limiter.check_rate_limit("192.168.1.2")
        
        stats = limiter.get_stats()
        assert stats["total_requests"] == 2
        assert stats["blocked_requests"] == 0
        assert stats["active_ips"] >= 1
    
    def test_reset_client(self):
        """Test resetting rate limit for specific IP."""
        limiter = SlidingWindowRateLimiter()
        
        # Make 5 requests
        for i in range(5):
            limiter.check_rate_limit("192.168.1.1")
        
        # Reset
        limiter.reset_client("192.168.1.1")
        
        # Should be able to make requests again
        is_allowed, _, _ = limiter.check_rate_limit("192.168.1.1")
        assert is_allowed is True
