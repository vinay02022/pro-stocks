"""
Server-Sent Events (SSE) endpoint for real-time price streaming.

Provides push-based price updates to the frontend without polling.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.services.cache.redis_client import get_price_cache
from app.services.websocket.manager import get_websocket_manager
from app.core.market_hours import is_market_open

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

router = APIRouter()


@router.get("/price/{symbol}")
async def stream_price(
    symbol: str,
    interval: int = Query(default=100, ge=50, le=1000, description="Update interval in ms"),
):
    """
    Stream real-time price updates for a symbol via SSE.

    Frontend connects once, receives continuous price updates.
    No polling needed - server pushes data.

    Usage (JavaScript):
    ```js
    const eventSource = new EventSource('/api/v1/stream/price/RELIANCE');
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Price:', data.ltp);
    };
    ```
    """
    symbol = symbol.upper()
    interval_seconds = interval / 1000.0

    async def event_generator():
        cache = get_price_cache()
        ws_manager = get_websocket_manager()
        client_id = str(uuid.uuid4())

        # Create SSE queue for this client
        queue = ws_manager.create_sse_queue(client_id)

        # Subscribe to symbol
        await ws_manager.subscribe([symbol])

        try:
            last_price = None

            while True:
                # Try to get from WebSocket queue first (real-time)
                try:
                    tick = await asyncio.wait_for(queue.get(), timeout=interval_seconds)
                    if tick.get("symbol") == symbol:
                        data = {
                            "symbol": symbol,
                            "ltp": tick.get("ltp"),
                            "open": tick.get("open"),
                            "high": tick.get("high"),
                            "low": tick.get("low"),
                            "close": tick.get("close"),
                            "volume": tick.get("volume"),
                            "timestamp": datetime.now(IST).isoformat(),
                            "source": tick.get("source", "websocket"),
                            "is_market_open": is_market_open(),
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                        last_price = tick.get("ltp")
                        continue
                except asyncio.TimeoutError:
                    pass

                # Fallback: read from Redis cache
                ltp = await cache.get_ltp(symbol)
                quote = await cache.get_quote(symbol)

                if ltp and ltp != last_price:
                    data = {
                        "symbol": symbol,
                        "ltp": ltp,
                        "open": quote.get("open") if quote else None,
                        "high": quote.get("high") if quote else None,
                        "low": quote.get("low") if quote else None,
                        "close": quote.get("close") if quote else None,
                        "volume": quote.get("volume") if quote else None,
                        "timestamp": datetime.now(IST).isoformat(),
                        "source": "cache",
                        "is_market_open": is_market_open(),
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    last_price = ltp
                else:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat\n\n"

                await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            pass
        finally:
            ws_manager.remove_sse_queue(client_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering for nginx
        },
    )


@router.get("/prices")
async def stream_multiple_prices(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    interval: int = Query(default=100, ge=50, le=1000, description="Update interval in ms"),
):
    """
    Stream real-time price updates for multiple symbols via SSE.

    Usage:
    ```js
    const eventSource = new EventSource('/api/v1/stream/prices?symbols=RELIANCE,TCS,INFY');
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // data is an object: { RELIANCE: {...}, TCS: {...}, ... }
    };
    ```
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    interval_seconds = interval / 1000.0

    async def event_generator():
        cache = get_price_cache()
        ws_manager = get_websocket_manager()
        client_id = str(uuid.uuid4())

        # Create SSE queue for this client
        queue = ws_manager.create_sse_queue(client_id)

        # Subscribe to all symbols
        await ws_manager.subscribe(symbol_list)

        try:
            last_prices = {}

            while True:
                # Collect all updates from queue
                updates = {}
                while True:
                    try:
                        tick = queue.get_nowait()
                        symbol = tick.get("symbol")
                        if symbol in symbol_list:
                            updates[symbol] = tick
                    except asyncio.QueueEmpty:
                        break

                # Get any missing prices from cache
                cached = await cache.get_multiple_ltp(symbol_list)
                for symbol, ltp in cached.items():
                    if symbol not in updates and ltp != last_prices.get(symbol):
                        updates[symbol] = {
                            "symbol": symbol,
                            "ltp": ltp,
                            "source": "cache",
                        }

                if updates:
                    data = {
                        symbol: {
                            "ltp": tick.get("ltp"),
                            "open": tick.get("open"),
                            "high": tick.get("high"),
                            "low": tick.get("low"),
                            "close": tick.get("close"),
                            "volume": tick.get("volume"),
                            "source": tick.get("source", "cache"),
                        }
                        for symbol, tick in updates.items()
                    }
                    data["_meta"] = {
                        "timestamp": datetime.now(IST).isoformat(),
                        "is_market_open": is_market_open(),
                    }
                    yield f"data: {json.dumps(data)}\n\n"

                    # Update last prices
                    for symbol, tick in updates.items():
                        last_prices[symbol] = tick.get("ltp")
                else:
                    # Heartbeat
                    yield f": heartbeat\n\n"

                await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            pass
        finally:
            ws_manager.remove_sse_queue(client_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/candle/{symbol}")
async def stream_candle(
    symbol: str,
    timeframe: str = Query(default="1m", description="Candle timeframe"),
    interval: int = Query(default=1000, ge=100, le=5000, description="Update interval in ms"),
):
    """
    Stream real-time candle updates for charting.

    Sends the current (forming) candle as it updates.
    Useful for real-time chart updates without full refresh.
    """
    symbol = symbol.upper()
    interval_seconds = interval / 1000.0

    async def event_generator():
        cache = get_price_cache()
        last_candle = None

        while True:
            candle = await cache.get_current_candle(symbol, timeframe)

            if candle and candle != last_candle:
                data = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "candle": candle,
                    "timestamp": datetime.now(IST).isoformat(),
                    "is_market_open": is_market_open(),
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_candle = candle.copy()
            else:
                yield f": heartbeat\n\n"

            await asyncio.sleep(interval_seconds)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
