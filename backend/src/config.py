"""
Configuration management with validation for Prompt2Frame backend.

This module provides centralized configuration management using Pydantic for
validation and type safety. All environment variables are validated at startup.
"""

import os
from typing import List
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseModel):
    """Application settings with validation."""
    
    # Required: API Keys
    groq_api_key: str = Field(..., min_length=20, description="Groq API key for LLM services")
    
    # Server Configuration
    port: int = Field(default=5000, ge=1024, le=65535, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # Security 
    allowed_origins: List[str] = Field(
        default=["http://localhost:5173"],
        description="Allowed CORS origins"
    )
    
    # Performance
    max_concurrent_requests: int = Field(default=2, ge=1, le=10, description="Max concurrent requests")
    request_timeout: int = Field(default=300, ge=60, le=600, description="Request timeout in seconds")
    
    # File System
    video_cleanup_age_hours: int = Field(default=24, ge=1, description="Video cleanup age in hours")
    max_video_storage_gb: float = Field(default=5.0, ge=0.1, description="Max video storage in GB")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False
    
    @validator("groq_api_key")
    def validate_api_key(cls, v):
        """Validate API key format."""
        if v == "your_groq_api_key_here" or not v.strip():
            raise ValueError(
                "GROQ_API_KEY is not configured. "
                "Please set it in your .env file. "
                "Get your key from: https://console.groq.com/keys"
            )
        return v.strip()
    
    @validator("allowed_origins", pre=True)
    def parse_origins(cls, v):
        """Parse comma-separated origins string."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v
    
    @classmethod
    def load(cls) -> "Settings":
        """Load and validate settings with helpful error messages."""
        try:
            return cls(
                groq_api_key=os.getenv("GROQ_API_KEY", ""),
                port=int(os.getenv("PORT", "5000")),
                debug=os.getenv("DEBUG", "false").lower() in ("true", "1", "yes"),
                allowed_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:5173"),
                max_concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", "2")),
                request_timeout=int(os.getenv("REQUEST_TIMEOUT", "300")),
                video_cleanup_age_hours=int(os.getenv("VIDEO_CLEANUP_AGE_HOURS", "24")),
                max_video_storage_gb=float(os.getenv("MAX_VIDEO_STORAGE_GB", "5.0")),
            )
        except ValueError as e:
            print("\n" + "=" * 70)
            print("❌ CONFIGURATION ERROR")
            print("=" * 70)
            print(f"\n{str(e)}\n")
            print("Please check your .env file and ensure all required")
            print("environment variables are set correctly.")
            print("\nSee .env.example for a template with all available options.")
            print("=" * 70 + "\n")
            raise SystemExit(1)


# Global settings instance
settings: Settings = Settings.load()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings
