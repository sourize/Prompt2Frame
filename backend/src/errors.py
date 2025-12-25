"""
Structured error handling and response formatting.

This module provides consistent error responses with correlation IDs
for better debugging and user experience.
"""

import uuid
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Structured error response with consistent format."""
    
    @staticmethod
    def create(
        status_code: int,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        suggestion: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> JSONResponse:
        """
        Create a structured error response.
        
        Args:
            status_code: HTTP status code
            error_type: Type of error (e.g., "ValidationError", "APIError")
            message: Human-readable error message
            details: Additional error details
            suggestion: Helpful suggestion for user
            correlation_id: Request correlation ID for tracing
            
        Returns:
            JSONResponse with structured error
        """
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        response_body = {
            "error": {
                "type": error_type,
                "message": message,
                "correlation_id": correlation_id,
            }
        }
        
        if details:
            response_body["error"]["details"] = details
        
        if suggestion:
            response_body["error"]["suggestion"] = suggestion
        
        # Log the error with correlation ID
        logger.error(
            f"[{correlation_id}] {error_type}: {message}",
            extra={
                "correlation_id": correlation_id,
                "error_type": error_type,
                "status_code": status_code
            }
        )
        
        return JSONResponse(
            status_code=status_code,
            content=response_body,
            headers={"X-Correlation-ID": correlation_id}
        )


class ErrorMessages:
    """Standard error messages for common scenarios."""
    
    # Prompt validation errors
    PROMPT_TOO_SHORT = "Prompt is too short. Please provide at least 3 characters."
    PROMPT_TOO_LONG = "Prompt is too long. Maximum 500 characters allowed."
    PROMPT_INVALID_CONTENT = (
        "Your prompt contains potentially unsafe content. "
        "Please describe visual animations only."
    )
    
    # API errors
    GROQ_API_UNAVAILABLE = (
        "The AI service is temporarily unavailable. "
        "This usually resolves within a few minutes."
    )
    GROQ_API_TIMEOUT = (
        "The AI service took too long to respond. "
        "Please try again with a simpler prompt."
    )
    GROQ_API_RATE_LIMIT = (
        "Too many requests to the AI service. "
        "Please wait a moment before trying again."
    )
    
    # Generation errors
    CODE_GENERATION_FAILED = (
        "Failed to generate animation code. "
        "The AI had trouble understanding your prompt."
    )
    VIDEO_RENDERING_FAILED = (
        "Failed to render the animation video. "
        "The generated code may have been too complex."
    )
    
    # System errors
    SYSTEM_OVERLOADED = (
        "The service is currently overloaded. "
        "Please try again in a few moments."
    )
    INTERNAL_ERROR = (
        "An unexpected error occurred. "
        "Our team has been notified."
    )
    
    # Suggestions
    SUGGEST_SIMPLER_PROMPT = "Try using a simpler, more direct description."
    SUGGEST_RETRY = "Please try again in a few moments."
    SUGGEST_CHECK_PROMPT = "Check your prompt for any unusual characters or requests."


def get_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())
