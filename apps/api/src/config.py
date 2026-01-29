"""Application settings using pydantic-settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # ==========================================================================
    # Application
    # ==========================================================================
    app_name: str = "DevFlow Agent"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"
    
    # ==========================================================================
    # Database
    # ==========================================================================
    database_url: PostgresDsn = Field(
        default="postgresql+psycopg://devflow:devflow@localhost:5432/devflow"
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10
    
    # ==========================================================================
    # Redis
    # ==========================================================================
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")
    
    # ==========================================================================
    # LLM Providers
    # ==========================================================================
    # DeepSeek
    deepseek_api_key: str = Field(default="")
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model_chat: str = "deepseek-chat"
    deepseek_model_reasoner: str = "deepseek-reasoner"
    
    # Kimi/Moonshot
    kimi_api_key: str = Field(default="")
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "moonshot-v1-32k"
    
    # Model Routing
    primary_provider: Literal["deepseek", "kimi"] = "deepseek"
    fallback_provider: Literal["deepseek", "kimi"] = "kimi"
    
    # ==========================================================================
    # GitHub OAuth
    # ==========================================================================
    github_client_id: str = Field(default="")
    github_client_secret: str = Field(default="")
    github_redirect_uri: str = "http://localhost:3000/api/auth/callback/github"
    
    # ==========================================================================
    # JWT Auth
    # ==========================================================================
    jwt_secret_key: str = Field(default="change-me-in-production-please")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7  # 1 week
    
    # ==========================================================================
    # Sandbox
    # ==========================================================================
    sandbox_enabled: bool = True
    sandbox_timeout_seconds: int = 60
    sandbox_memory_limit_mb: int = 512
    sandbox_allowed_commands: list[str] = Field(
        default=["pytest", "ruff", "mypy", "uv", "pip", "python"]
    )
    
    # ==========================================================================
    # API
    # ==========================================================================
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = Field(default=["http://localhost:3000"])


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
