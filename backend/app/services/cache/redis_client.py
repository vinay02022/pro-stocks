"""
Redis cache client for real-time price data.

Provides microsecond-level read latency for LTP (Last Traded Price).
Also caches OHLC candles for instant timeframe switching.
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from zoneinfo import ZoneInfo

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

# Global Redis connection pool
_redis_pool: Optional[redis.Redis] = None


async def init_redis() -> redis.Redis:
    """
    Initialize Redis connection pool.
    Called on application startup.
    """
    global _redis_pool

    if _redis_pool is not None:
        return _redis_pool

    try:
        _redis_pool = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        # Test connection
        await _redis_pool.ping()
        logger.info(f"Redis connected: {settings.redis_url}")
        return _redis_pool
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
        _redis_pool = None
        return None


async def close_redis() -> None:
    """Close Redis connection pool."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None
        logger.info("Redis connection closed")


def get_redis() -> Optional[redis.Redis]:
    """Get the Redis connection pool."""
    return _redis_pool


class PriceCache:
    """
    Redis-based cache for real-time price data.

    Keys:
    - ltp:{symbol} → float (Last Traded Price)
    - quote:{symbol} → JSON {ltp, open, high, low, close, volume, timestamp}
    - candle:{symbol}:{timeframe} → JSON {o, h, l, c, v, t}
    - candles:{symbol}:{timeframe} → List of OHLC candles (for chart data)
    """

    # In-memory fallback when Redis is unavailable
    _memory_cache: Dict[str, Any] = {}

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self._redis = redis_client or _redis_pool

    @property
    def redis(self) -> Optional[redis.Redis]:
        return self._redis or _redis_pool

    def _memory_get(self, key: str) -> Optional[str]:
        """Fallback to memory cache."""
        return self._memory_cache.get(key)

    def _memory_set(self, key: str, value: str, ex: int = None):
        """Fallback to memory cache."""
        self._memory_cache[key] = value

    # ============ LTP (Last Traded Price) ============

    async def set_ltp(self, symbol: str, price: float, timestamp: datetime = None) -> bool:
        """
        Store the last traded price for a symbol.
        Optimized for high-frequency updates.
        """
        key = f"ltp:{symbol.upper()}"
        value = str(price)

        if self.redis:
            try:
                await self.redis.set(key, value)
                return True
            except Exception as e:
                logger.debug(f"Redis set_ltp failed: {e}")

        # Fallback to memory
        self._memory_set(key, value)
        return True

    async def get_ltp(self, symbol: str) -> Optional[float]:
        """
        Get the last traded price for a symbol.
        Returns None if not cached.
        """
        key = f"ltp:{symbol.upper()}"

        if self.redis:
            try:
                value = await self.redis.get(key)
                return float(value) if value else None
            except Exception as e:
                logger.debug(f"Redis get_ltp failed: {e}")

        # Fallback to memory
        value = self._memory_get(key)
        return float(value) if value else None

    async def get_multiple_ltp(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get LTP for multiple symbols in a single call.
        Uses Redis pipeline for efficiency.
        """
        result = {}
        keys = [f"ltp:{s.upper()}" for s in symbols]

        if self.redis:
            try:
                values = await self.redis.mget(keys)
                for symbol, value in zip(symbols, values):
                    if value:
                        result[symbol.upper()] = float(value)
                return result
            except Exception as e:
                logger.debug(f"Redis get_multiple_ltp failed: {e}")

        # Fallback to memory
        for symbol, key in zip(symbols, keys):
            value = self._memory_get(key)
            if value:
                result[symbol.upper()] = float(value)
        return result

    # ============ Full Quote ============

    async def set_quote(self, symbol: str, quote: Dict[str, Any]) -> bool:
        """
        Store a full quote (LTP, OHLC, volume) for a symbol.
        """
        key = f"quote:{symbol.upper()}"
        value = json.dumps(quote)

        # Also update LTP separately for fast access
        if "ltp" in quote:
            await self.set_ltp(symbol, quote["ltp"])

        if self.redis:
            try:
                await self.redis.set(key, value, ex=60)  # 1 minute TTL
                return True
            except Exception as e:
                logger.debug(f"Redis set_quote failed: {e}")

        self._memory_set(key, value)
        return True

    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the full quote for a symbol."""
        key = f"quote:{symbol.upper()}"

        if self.redis:
            try:
                value = await self.redis.get(key)
                return json.loads(value) if value else None
            except Exception as e:
                logger.debug(f"Redis get_quote failed: {e}")

        value = self._memory_get(key)
        return json.loads(value) if value else None

    # ============ Current Candle (Real-Time) ============

    async def update_candle(
        self,
        symbol: str,
        timeframe: str,
        tick: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update the current candle with a new tick.
        Creates a new candle if needed.

        tick = {
            "price": float,
            "volume": int,
            "timestamp": datetime
        }
        """
        key = f"candle:{symbol.upper()}:{timeframe}"
        price = tick["price"]
        volume = tick.get("volume", 0)
        timestamp = tick.get("timestamp", datetime.now(IST))

        # Get current candle
        current = await self.get_current_candle(symbol, timeframe)

        if current is None:
            # Create new candle
            candle = {
                "o": price,
                "h": price,
                "l": price,
                "c": price,
                "v": volume,
                "t": timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp,
            }
        else:
            # Update existing candle
            candle = {
                "o": current["o"],
                "h": max(current["h"], price),
                "l": min(current["l"], price),
                "c": price,
                "v": current["v"] + volume,
                "t": current["t"],
            }

        # Store updated candle
        value = json.dumps(candle)
        if self.redis:
            try:
                await self.redis.set(key, value, ex=3600)  # 1 hour TTL
            except Exception as e:
                logger.debug(f"Redis update_candle failed: {e}")

        self._memory_set(key, value)
        return candle

    async def get_current_candle(
        self,
        symbol: str,
        timeframe: str,
    ) -> Optional[Dict[str, Any]]:
        """Get the current (incomplete) candle for a symbol/timeframe."""
        key = f"candle:{symbol.upper()}:{timeframe}"

        if self.redis:
            try:
                value = await self.redis.get(key)
                return json.loads(value) if value else None
            except Exception as e:
                logger.debug(f"Redis get_current_candle failed: {e}")

        value = self._memory_get(key)
        return json.loads(value) if value else None

    # ============ Chart Data Cache ============

    async def cache_chart_data(
        self,
        symbol: str,
        timeframe: str,
        data: Dict[str, Any],
        ttl: int = 300,  # 5 minutes default
    ) -> bool:
        """
        Cache complete chart data for a symbol/timeframe.
        Used for instant timeframe switching.
        """
        key = f"chartdata:{symbol.upper()}:{timeframe}"
        value = json.dumps(data)

        if self.redis:
            try:
                await self.redis.set(key, value, ex=ttl)
                return True
            except Exception as e:
                logger.debug(f"Redis cache_chart_data failed: {e}")

        self._memory_set(key, value)
        return True

    async def get_cached_chart_data(
        self,
        symbol: str,
        timeframe: str,
    ) -> Optional[Dict[str, Any]]:
        """Get cached chart data for instant display."""
        key = f"chartdata:{symbol.upper()}:{timeframe}"

        if self.redis:
            try:
                value = await self.redis.get(key)
                return json.loads(value) if value else None
            except Exception as e:
                logger.debug(f"Redis get_cached_chart_data failed: {e}")

        value = self._memory_get(key)
        return json.loads(value) if value else None

    # ============ Subscribed Symbols ============

    async def add_subscribed_symbol(self, symbol: str) -> bool:
        """Add a symbol to the subscription list."""
        key = "subscribed_symbols"

        if self.redis:
            try:
                await self.redis.sadd(key, symbol.upper())
                return True
            except Exception as e:
                logger.debug(f"Redis add_subscribed_symbol failed: {e}")

        # Memory fallback
        if key not in self._memory_cache:
            self._memory_cache[key] = set()
        self._memory_cache[key].add(symbol.upper())
        return True

    async def get_subscribed_symbols(self) -> List[str]:
        """Get all subscribed symbols."""
        key = "subscribed_symbols"

        if self.redis:
            try:
                members = await self.redis.smembers(key)
                return list(members)
            except Exception as e:
                logger.debug(f"Redis get_subscribed_symbols failed: {e}")

        return list(self._memory_cache.get(key, set()))

    async def remove_subscribed_symbol(self, symbol: str) -> bool:
        """Remove a symbol from the subscription list."""
        key = "subscribed_symbols"

        if self.redis:
            try:
                await self.redis.srem(key, symbol.upper())
                return True
            except Exception as e:
                logger.debug(f"Redis remove_subscribed_symbol failed: {e}")

        if key in self._memory_cache:
            self._memory_cache[key].discard(symbol.upper())
        return True


# Singleton instance
_price_cache: Optional[PriceCache] = None


def get_price_cache() -> PriceCache:
    """Get the price cache singleton."""
    global _price_cache
    if _price_cache is None:
        _price_cache = PriceCache()
    return _price_cache
