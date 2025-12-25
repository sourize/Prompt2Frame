"""
Rate limiting module for Prompt2Frame API.

Implements sliding window rate limiting per IP address to prevent abuse
and ensure fair resource allocation across users.
"""

import time
from collections import defaultdict, deque
from typing import Dict, Tuple, Optional
import logging
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter with multiple time windows.
    
    Tracks requests per IP address across different time windows
    (e.g., per minute, per hour) to enforce multiple rate limits.
    """
    
    def __init__(self):
        """Initialize rate limiter with request tracking."""
        # Store request timestamps per IP
        # Format: {ip_address: deque([(timestamp, window_name), ...])}
        self._requests: Dict[str, deque] = defaultdict(deque)
        
        # Rate limit configurations: (window_seconds, max_requests, name)
        self.limits = [
            (60, 5, "minute"),      # 5 requests per minute
            (3600, 20, "hour"),     # 20 requests per hour
        ]
        
        # Statistics
        self._total_requests = 0
        self._blocked_requests = 0
    
    def _cleanup_old_requests(self, ip: str, current_time: float):
        """
        Remove expired request timestamps for an IP.
        
        Args:
            ip: Client IP address
            current_time: Current timestamp
        """
        if ip not in self._requests:
            return
        
        # Find the longest window
        max_window = max(window[0] for window in self.limits)
        cutoff_time = current_time - max_window
        
        # Remove timestamps older than the longest window
        while self._requests[ip] and self._requests[ip][0] < cutoff_time:
            self._requests[ip].popleft()
        
        # Clean up empty entries
        if not self._requests[ip]:
            del self._requests[ip]
    
    def check_rate_limit(self, ip: str) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Check if request from IP is allowed.
        
        Args:
            ip: Client IP address
            
        Returns:
            Tuple of (is_allowed, limit_name, retry_after_seconds)
        """
        current_time = time.time()
        self._total_requests += 1
        
        # Cleanup old requests
        self._cleanup_old_requests(ip, current_time)
        
        # Check each limit window
        for window_seconds, max_requests, window_name in self.limits:
            cutoff_time = current_time - window_seconds
            
            # Count requests in this window
            request_count = sum(
                1 for timestamp in self._requests[ip]
                if timestamp >= cutoff_time
            )
            
            if request_count >= max_requests:
                # Rate limit exceeded
                self._blocked_requests += 1
                
                # Calculate retry-after (seconds until oldest request expires)
                if self._requests[ip]:
                    oldest_in_window = min(
                        t for t in self._requests[ip] if t >= cutoff_time
                    )
                    retry_after = int(window_seconds - (current_time - oldest_in_window)) + 1
                else:
                    retry_after = window_seconds
                
                logger.warning(
                    f"Rate limit exceeded for {ip}: {request_count}/{max_requests} per {window_name}"
                )
                
                return False, window_name, retry_after
        
        # All limits passed, record the request
        self._requests[ip].append(current_time)
        
        return True, None, None
    
    def get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request.
        
        Handles X-Forwarded-For header for proxied requests.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (for proxied requests)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client
        return request.client.host if request.client else "unknown"
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get rate limiter statistics.
        
        Returns:
            Dict with statistics
        """
        current_time = time.time()
        active_ips = 0
        
        # Count IPs with recent activity (last hour)
        for ip, timestamps in self._requests.items():
            if timestamps and timestamps[-1] > current_time - 3600:
                active_ips += 1
        
        block_rate = (
            self._blocked_requests / self._total_requests * 100
            if self._total_requests > 0
            else 0
        )
        
        return {
            "total_requests": self._total_requests,
            "blocked_requests": self._blocked_requests,
            "block_rate": f"{block_rate:.1f}%",
            "active_ips": active_ips,
            "tracked_ips": len(self._requests),
            "limits": [
                f"{count} req/{name}" for _, count, name in self.limits
            ]
        }
    
    def reset_client(self, ip: str):
        """
        Reset rate limit for a specific IP (admin function).
        
        Args:
            ip: Client IP to reset
        """
        if ip in self._requests:
            del self._requests[ip]
            logger.info(f"Rate limit reset for IP: {ip}")


# Global rate limiter instance
rate_limiter = SlidingWindowRateLimiter()


def check_rate_limit_middleware(request: Request):
    """
    Middleware function to check rate limits.
    
    Raises HTTPException if rate limit exceeded.
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    # Allow OPTIONS requests for CORS preflight checks without rate limiting
    if request.method == "OPTIONS":
        return

    ip = rate_limiter.get_client_ip(request)
    is_allowed, limit_name, retry_after = rate_limiter.check_rate_limit(ip)
    
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {limit_name}",
                "retry_after": retry_after,
                "suggestion": f"Please wait {retry_after} seconds before trying again."
            },
            headers={"Retry-After": str(retry_after)}
        )
