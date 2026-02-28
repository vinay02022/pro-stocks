"""
WebSocket Manager for real-time market data.

Manages WebSocket connections to broker APIs:
- Primary: Angel One SmartAPI
- Fallback: Upstox

Features:
- Auto-reconnect on disconnect
- Failover between providers
- Tick processing and caching
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Callable, Set, Dict, Any
from zoneinfo import ZoneInfo
from enum import Enum

from app.core.config import settings
from app.services.cache.redis_client import get_price_cache

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class WebSocketManager:
    """
    Manages WebSocket connections to market data providers.

    Usage:
        manager = WebSocketManager()
        await manager.start()
        await manager.subscribe(["RELIANCE", "TCS", "INFY"])
        # Ticks are automatically pushed to Redis and SSE clients
        await manager.stop()
    """

    def __init__(self):
        self._state = ConnectionState.DISCONNECTED
        self._subscribed_symbols: Set[str] = set()
        self._tick_callbacks: List[Callable] = []
        self._ws_task: Optional[asyncio.Task] = None
        self._reconnect_delay = 1  # Start with 1 second
        self._max_reconnect_delay = 60  # Max 60 seconds
        self._running = False

        # Angel One WebSocket
        self._angelone_ws = None
        self._angelone_connected = False

        # Upstox WebSocket
        self._upstox_client = None
        self._upstox_connected = False

        # SSE subscribers (for pushing to frontend)
        self._sse_queues: Dict[str, asyncio.Queue] = {}

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    @property
    def subscribed_symbols(self) -> List[str]:
        return list(self._subscribed_symbols)

    async def start(self) -> bool:
        """Start the WebSocket manager."""
        if self._running:
            logger.warning("WebSocket manager already running")
            return True

        self._running = True
        self._state = ConnectionState.CONNECTING

        # Start connection task
        self._ws_task = asyncio.create_task(self._connection_loop())
        logger.info("WebSocket manager started")
        return True

    async def stop(self) -> None:
        """Stop the WebSocket manager."""
        self._running = False
        self._state = ConnectionState.DISCONNECTED

        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass

        # Close any open connections
        await self._disconnect_angelone()
        await self._disconnect_upstox()

        logger.info("WebSocket manager stopped")

    async def subscribe(self, symbols: List[str]) -> bool:
        """
        Subscribe to price updates for symbols.
        """
        new_symbols = set(s.upper() for s in symbols) - self._subscribed_symbols
        if not new_symbols:
            return True

        self._subscribed_symbols.update(new_symbols)

        # Update cache with subscribed symbols
        cache = get_price_cache()
        for symbol in new_symbols:
            await cache.add_subscribed_symbol(symbol)

        # If connected, subscribe immediately
        if self._angelone_connected:
            await self._subscribe_angelone(list(new_symbols))

        logger.info(f"Subscribed to: {list(new_symbols)}")
        return True

    async def unsubscribe(self, symbols: List[str]) -> bool:
        """Unsubscribe from price updates."""
        symbols_to_remove = set(s.upper() for s in symbols) & self._subscribed_symbols
        self._subscribed_symbols -= symbols_to_remove

        cache = get_price_cache()
        for symbol in symbols_to_remove:
            await cache.remove_subscribed_symbol(symbol)

        logger.info(f"Unsubscribed from: {list(symbols_to_remove)}")
        return True

    def add_tick_callback(self, callback: Callable) -> None:
        """Add a callback to be called on each tick."""
        self._tick_callbacks.append(callback)

    def remove_tick_callback(self, callback: Callable) -> None:
        """Remove a tick callback."""
        if callback in self._tick_callbacks:
            self._tick_callbacks.remove(callback)

    # ============ SSE Queue Management ============

    def create_sse_queue(self, client_id: str) -> asyncio.Queue:
        """Create a queue for an SSE client."""
        queue = asyncio.Queue(maxsize=100)
        self._sse_queues[client_id] = queue
        return queue

    def remove_sse_queue(self, client_id: str) -> None:
        """Remove an SSE client queue."""
        if client_id in self._sse_queues:
            del self._sse_queues[client_id]

    async def _broadcast_to_sse(self, tick: Dict[str, Any]) -> None:
        """Broadcast a tick to all SSE clients."""
        for queue in self._sse_queues.values():
            try:
                queue.put_nowait(tick)
            except asyncio.QueueFull:
                # Drop old messages if queue is full
                try:
                    queue.get_nowait()
                    queue.put_nowait(tick)
                except:
                    pass

    # ============ Connection Loop ============

    async def _connection_loop(self) -> None:
        """Main connection loop with auto-reconnect."""
        while self._running:
            try:
                # Try Angel One first
                if settings.angel_one_ws_enabled:
                    connected = await self._connect_angelone()
                    if connected:
                        self._state = ConnectionState.CONNECTED
                        self._reconnect_delay = 1  # Reset delay on success

                        # Subscribe to symbols
                        if self._subscribed_symbols:
                            await self._subscribe_angelone(list(self._subscribed_symbols))

                        # Listen for messages
                        await self._listen_angelone()

                # If Angel One fails, try Upstox as fallback
                if settings.upstox_ws_enabled and not self._angelone_connected:
                    connected = await self._connect_upstox()
                    if connected:
                        self._state = ConnectionState.CONNECTED
                        self._reconnect_delay = 1

                        # Subscribe to symbols
                        if self._subscribed_symbols:
                            await self._subscribe_upstox(list(self._subscribed_symbols))

                        # Listen for messages
                        await self._listen_upstox()

                # If both fail, wait and retry
                if not self._angelone_connected and not self._upstox_connected:
                    self._state = ConnectionState.RECONNECTING
                    logger.info(f"Reconnecting in {self._reconnect_delay}s...")
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(
                        self._reconnect_delay * 2,
                        self._max_reconnect_delay
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection loop error: {e}")
                self._state = ConnectionState.ERROR
                await asyncio.sleep(self._reconnect_delay)

    # ============ Angel One WebSocket ============

    async def _connect_angelone(self) -> bool:
        """Connect to Angel One WebSocket."""
        try:
            from SmartApi.smartWebSocketV2 import SmartWebSocketV2

            # Check if we have credentials
            api_key = settings.angel_one_api_key or settings.angel_one_historical_api_key
            client_id = settings.angel_one_client_id

            if not api_key or not client_id:
                logger.warning("Angel One credentials not configured")
                return False

            # Get auth token (need to authenticate first)
            from app.services.data_ingestion.angelone_adapter import get_angel_client
            client = get_angel_client()
            if not await client.connect():
                logger.warning("Angel One authentication failed")
                return False

            # Create WebSocket connection
            self._angelone_ws = SmartWebSocketV2(
                auth_token=client._auth_token,
                api_key=api_key,
                client_code=client_id,
                feed_token=client._feed_token,
            )

            # Set callbacks
            self._angelone_ws.on_open = self._on_angelone_open
            self._angelone_ws.on_data = self._on_angelone_data
            self._angelone_ws.on_error = self._on_angelone_error
            self._angelone_ws.on_close = self._on_angelone_close

            # Connect (non-blocking)
            self._angelone_ws.connect()
            self._angelone_connected = True
            logger.info("Angel One WebSocket connected")
            return True

        except ImportError:
            logger.warning("SmartApi package not installed for WebSocket")
            return False
        except Exception as e:
            logger.error(f"Angel One WebSocket connection failed: {e}")
            return False

    async def _disconnect_angelone(self) -> None:
        """Disconnect from Angel One WebSocket."""
        if self._angelone_ws:
            try:
                self._angelone_ws.close_connection()
            except:
                pass
            self._angelone_ws = None
        self._angelone_connected = False

    async def _subscribe_angelone(self, symbols: List[str]) -> None:
        """Subscribe to symbols on Angel One WebSocket."""
        if not self._angelone_ws or not self._angelone_connected:
            return

        try:
            from app.services.data_ingestion.angelone_adapter import SYMBOL_TOKEN_MAP

            # Build token list
            token_list = []
            for symbol in symbols:
                token = SYMBOL_TOKEN_MAP.get(symbol.upper())
                if token:
                    # Format: [exchange_type, token]
                    # exchange_type: 1 = NSE, 2 = NFO, 3 = BSE
                    token_list.append({
                        "exchangeType": 1,  # NSE
                        "tokens": [token]
                    })

            if token_list:
                # Subscribe mode: 1 = LTP, 2 = Quote, 3 = Snap Quote
                self._angelone_ws.subscribe("abc123", 1, token_list)
                logger.info(f"Subscribed to {len(token_list)} symbols on Angel One")

        except Exception as e:
            logger.error(f"Angel One subscribe failed: {e}")

    async def _listen_angelone(self) -> None:
        """Listen for messages (keep connection alive)."""
        while self._running and self._angelone_connected:
            await asyncio.sleep(1)

    def _on_angelone_open(self, wsapp) -> None:
        """Callback when Angel One WebSocket opens."""
        logger.info("Angel One WebSocket opened")
        self._angelone_connected = True

    def _on_angelone_data(self, wsapp, message) -> None:
        """Callback when Angel One WebSocket receives data."""
        try:
            # Parse tick data
            # Message format varies by subscription mode
            if isinstance(message, dict):
                tick = self._parse_angelone_tick(message)
                if tick:
                    # Process tick asynchronously
                    asyncio.create_task(self._process_tick(tick))
        except Exception as e:
            logger.debug(f"Error processing Angel One data: {e}")

    def _on_angelone_error(self, wsapp, error) -> None:
        """Callback when Angel One WebSocket has an error."""
        logger.error(f"Angel One WebSocket error: {error}")
        self._angelone_connected = False

    def _on_angelone_close(self, wsapp, close_status_code, close_msg) -> None:
        """Callback when Angel One WebSocket closes."""
        logger.warning(f"Angel One WebSocket closed: {close_status_code} - {close_msg}")
        self._angelone_connected = False

    def _parse_angelone_tick(self, message: dict) -> Optional[Dict[str, Any]]:
        """Parse Angel One WebSocket message into standard tick format."""
        from app.services.data_ingestion.angelone_adapter import SYMBOL_TOKEN_MAP

        # Reverse lookup token to symbol
        token_to_symbol = {v: k for k, v in SYMBOL_TOKEN_MAP.items()}

        token = str(message.get("token", ""))
        symbol = token_to_symbol.get(token)

        if not symbol:
            return None

        return {
            "symbol": symbol,
            "ltp": float(message.get("ltp", 0)) / 100,  # Angel One sends in paise
            "open": float(message.get("open", 0)) / 100,
            "high": float(message.get("high", 0)) / 100,
            "low": float(message.get("low", 0)) / 100,
            "close": float(message.get("close", 0)) / 100,
            "volume": int(message.get("volume", 0)),
            "timestamp": datetime.now(IST),
            "source": "angel_one",
        }

    async def _process_tick(self, tick: Dict[str, Any]) -> None:
        """Process a tick - cache and broadcast."""
        symbol = tick["symbol"]
        price = tick["ltp"]

        # Update Redis cache
        cache = get_price_cache()
        await cache.set_ltp(symbol, price)
        await cache.set_quote(symbol, tick)

        # Update current candle for each timeframe
        for timeframe in ["1m", "5m", "15m"]:
            await cache.update_candle(symbol, timeframe, {
                "price": price,
                "volume": tick.get("volume", 0),
                "timestamp": tick.get("timestamp"),
            })

        # Broadcast to SSE clients
        await self._broadcast_to_sse(tick)

        # Call registered callbacks
        for callback in self._tick_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(tick)
                else:
                    callback(tick)
            except Exception as e:
                logger.debug(f"Tick callback error: {e}")

    # ============ Upstox WebSocket ============

    async def _connect_upstox(self) -> bool:
        """Connect to Upstox WebSocket."""
        try:
            from app.services.data_ingestion.upstox_adapter import get_upstox_client

            self._upstox_client = get_upstox_client()

            if not await self._upstox_client.connect():
                logger.warning("Upstox authentication failed")
                return False

            if not await self._upstox_client.connect_websocket():
                logger.warning("Upstox WebSocket connection failed")
                return False

            self._upstox_connected = True
            logger.info("Upstox WebSocket connected")
            return True

        except ImportError:
            logger.warning("Upstox adapter not available")
            return False
        except Exception as e:
            logger.error(f"Upstox WebSocket connection failed: {e}")
            return False

    async def _disconnect_upstox(self) -> None:
        """Disconnect from Upstox WebSocket."""
        if self._upstox_client:
            try:
                await self._upstox_client.close()
            except:
                pass
            self._upstox_client = None
        self._upstox_connected = False

    async def _subscribe_upstox(self, symbols: List[str]) -> None:
        """Subscribe to symbols on Upstox WebSocket."""
        if not self._upstox_client or not self._upstox_connected:
            return

        try:
            await self._upstox_client.subscribe(symbols)
            logger.info(f"Subscribed to {len(symbols)} symbols on Upstox")
        except Exception as e:
            logger.error(f"Upstox subscribe failed: {e}")

    async def _listen_upstox(self) -> None:
        """Listen for Upstox WebSocket messages."""
        if not self._upstox_client or not self._upstox_connected:
            return

        def tick_handler(tick):
            if isinstance(tick, list):
                for t in tick:
                    asyncio.create_task(self._process_tick(t))
            elif tick:
                asyncio.create_task(self._process_tick(tick))

        try:
            await self._upstox_client.listen(tick_handler)
        except Exception as e:
            logger.error(f"Upstox listen error: {e}")
            self._upstox_connected = False


# Singleton instance
_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get the WebSocket manager singleton."""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager


async def start_websocket_manager() -> WebSocketManager:
    """Start the WebSocket manager."""
    manager = get_websocket_manager()
    await manager.start()
    return manager


async def stop_websocket_manager() -> None:
    """Stop the WebSocket manager."""
    global _websocket_manager
    if _websocket_manager:
        await _websocket_manager.stop()
        _websocket_manager = None
