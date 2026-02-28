"""
WebSocket module for real-time market data streaming.

Provides persistent WebSocket connections to:
- Angel One SmartAPI
- Upstox (fallback)
"""

from app.services.websocket.manager import (
    WebSocketManager,
    get_websocket_manager,
    start_websocket_manager,
    stop_websocket_manager,
)

__all__ = [
    "WebSocketManager",
    "get_websocket_manager",
    "start_websocket_manager",
    "stop_websocket_manager",
]
