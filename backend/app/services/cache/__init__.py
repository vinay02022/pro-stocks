"""
Cache module for StockPro.

Provides Redis caching for real-time price data.
"""

from app.services.cache.redis_client import (
    PriceCache,
    get_price_cache,
    init_redis,
    close_redis,
)

__all__ = [
    "PriceCache",
    "get_price_cache",
    "init_redis",
    "close_redis",
]
