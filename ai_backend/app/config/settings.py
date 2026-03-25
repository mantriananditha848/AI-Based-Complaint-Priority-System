"""
Configuration settings for the AI Backend.
Uses pydantic-settings to load environment variables.
"""
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Hugging Face API key (optional — local YOLO models are used by default)
    HUGGINGFACE_API_KEY: Optional[str] = None

    # API Configuration
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
