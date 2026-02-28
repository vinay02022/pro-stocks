"""
Application Configuration

All settings loaded from environment variables.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Application
    app_name: str = "StockPro Backend"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database (PostgreSQL - for future production use)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/stockpro"

    # SQLite (local persistence)
    sqlite_path: Optional[str] = None  # Defaults to ./data/stockpro.db

    # Redis
    redis_url: str = "redis://localhost:6379"

    # CORS (Frontend URL)
    frontend_url: str = "http://localhost:3000"
    allowed_origins: list[str] = ["http://localhost:3000"]

    # Broker APIs
    groww_api_key: Optional[str] = None
    groww_api_secret: Optional[str] = None
    groww_base_url: str = "https://api.groww.in"

    # Angel One API Keys (multiple apps for different purposes)
    angel_one_api_key: Optional[str] = None  # Legacy/fallback
    angel_one_historical_api_key: Optional[str] = None  # For historical data
    angel_one_historical_secret: Optional[str] = None
    angel_one_trading_api_key: Optional[str] = None  # For trading
    angel_one_trading_secret: Optional[str] = None
    angel_one_market_api_key: Optional[str] = None  # For market feed
    angel_one_market_secret: Optional[str] = None
    angel_one_client_id: Optional[str] = None
    angel_one_password: Optional[str] = None
    angel_one_totp_secret: Optional[str] = None
    angel_one_base_url: str = "https://apiconnect.angelone.in"

    # Upstox API (for WebSocket streaming fallback)
    upstox_api_key: Optional[str] = None
    upstox_api_secret: Optional[str] = None
    upstox_redirect_uri: str = "http://localhost:3000/api/auth/upstox/callback"
    upstox_access_token: Optional[str] = None
    upstox_ws_enabled: bool = True
    upstox_base_url: str = "https://api.upstox.com/v2"

    # WebSocket settings
    angel_one_ws_enabled: bool = True

    # LLM Providers
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    llm_primary_provider: str = "gemini"  # Options: gemini, anthropic, openai
    llm_reasoning_model: str = "gemini-1.5-pro"
    llm_explanation_model: str = "gemini-1.5-flash"

    # News API
    news_api_key: Optional[str] = None
    news_api_base_url: str = "https://newsapi.org/v2"

    # Feature Flags
    enable_live_data: bool = False
    enable_options: bool = False
    enable_paper_trading: bool = True

    # Risk Limits (Defaults)
    default_max_position_percent: float = 5.0
    default_max_daily_loss_percent: float = 2.0
    default_max_daily_trades: int = 10
    default_min_risk_reward: float = 1.5

    # Rate Limits (requests per minute)
    groww_rate_limit: int = 60
    angel_one_rate_limit: int = 120
    news_rate_limit: int = 100
    llm_rate_limit: int = 60

    # Market Hours (IST)
    market_open: str = "09:15"
    market_close: str = "15:30"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
