"""
Upstox API Data Adapter

Provides real-time market data from Upstox broker.
Used as secondary/fallback data source with WebSocket streaming.

Upstox API v2 Documentation: https://upstox.com/developer/api-documentation/
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, List
from zoneinfo import ZoneInfo
import aiohttp

from app.core.config import settings
from app.schemas.market import (
    OHLCV,
    SymbolData,
    Timeframe,
    Exchange,
)

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


# Upstox interval mapping
INTERVAL_MAP = {
    Timeframe.M1: "1minute",
    Timeframe.M5: "5minute",
    Timeframe.M15: "15minute",
    Timeframe.M30: "30minute",
    Timeframe.H1: "60minute",
    Timeframe.D1: "day",
    Timeframe.W1: "week",
}

# NSE symbols to Upstox instrument key mapping
# Format: NSE_EQ|<ISIN> or simplified NSE_EQ|<SYMBOL>
SYMBOL_INSTRUMENT_MAP = {
    # Nifty 50 stocks
    "RELIANCE": "NSE_EQ|INE002A01018",
    "TCS": "NSE_EQ|INE467B01029",
    "HDFCBANK": "NSE_EQ|INE040A01034",
    "INFY": "NSE_EQ|INE009A01021",
    "ICICIBANK": "NSE_EQ|INE090A01021",
    "HINDUNILVR": "NSE_EQ|INE030A01027",
    "SBIN": "NSE_EQ|INE062A01020",
    "BHARTIARTL": "NSE_EQ|INE397D01024",
    "ITC": "NSE_EQ|INE154A01025",
    "KOTAKBANK": "NSE_EQ|INE237A01028",
    "LT": "NSE_EQ|INE018A01030",
    "AXISBANK": "NSE_EQ|INE238A01034",
    "ASIANPAINT": "NSE_EQ|INE021A01026",
    "MARUTI": "NSE_EQ|INE585B01010",
    "TITAN": "NSE_EQ|INE280A01028",
    "SUNPHARMA": "NSE_EQ|INE044A01036",
    "BAJFINANCE": "NSE_EQ|INE296A01024",
    "WIPRO": "NSE_EQ|INE075A01022",
    "ULTRACEMCO": "NSE_EQ|INE481G01011",
    "HCLTECH": "NSE_EQ|INE860A01027",
    "TATAMOTORS": "NSE_EQ|INE155A01022",
    "TATASTEEL": "NSE_EQ|INE081A01020",
    "NTPC": "NSE_EQ|INE733E01010",
    "POWERGRID": "NSE_EQ|INE752E01010",
    "M&M": "NSE_EQ|INE101A01026",
    "TECHM": "NSE_EQ|INE669C01036",
    "INDUSINDBK": "NSE_EQ|INE095A01012",
    "DRREDDY": "NSE_EQ|INE089A01023",
    "BAJAJFINSV": "NSE_EQ|INE918I01026",
    "NESTLEIND": "NSE_EQ|INE239A01016",
    "ONGC": "NSE_EQ|INE213A01029",
    "JSWSTEEL": "NSE_EQ|INE019A01038",
    "GRASIM": "NSE_EQ|INE047A01021",
    "ADANIENT": "NSE_EQ|INE423A01024",
    "ADANIPORTS": "NSE_EQ|INE742F01042",
    "COALINDIA": "NSE_EQ|INE522F01014",
    "BPCL": "NSE_EQ|INE541A01012",
    "CIPLA": "NSE_EQ|INE059A01026",
    "DIVISLAB": "NSE_EQ|INE361B01024",
    "EICHERMOT": "NSE_EQ|INE066A01013",
    "HEROMOTOCO": "NSE_EQ|INE158A01026",
    "HINDALCO": "NSE_EQ|INE038A01020",
    "TATACONSUM": "NSE_EQ|INE192A01025",
    "APOLLOHOSP": "NSE_EQ|INE437A01024",
    "SBILIFE": "NSE_EQ|INE123W01016",
    "BRITANNIA": "NSE_EQ|INE216A01030",
    "BAJAJ-AUTO": "NSE_EQ|INE917I01010",
    "UPL": "NSE_EQ|INE628A01036",
    "LTIM": "NSE_EQ|INE214T01019",
    # Indices
    "NIFTY": "NSE_INDEX|Nifty 50",
    "NIFTY50": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
}


class UpstoxClient:
    """
    Upstox API v2 client wrapper.

    Handles OAuth2 authentication and data fetching.
    """

    def __init__(self):
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._ws_callbacks: List[Callable] = []

    @property
    def is_authenticated(self) -> bool:
        """Check if we have a valid access token."""
        if not self._access_token:
            return False
        if self._token_expiry and datetime.now() > self._token_expiry:
            return False
        return True

    def get_auth_url(self) -> str:
        """Get the OAuth2 authorization URL for user login."""
        return (
            f"https://api.upstox.com/v2/login/authorization/dialog"
            f"?response_type=code"
            f"&client_id={settings.upstox_api_key}"
            f"&redirect_uri={settings.upstox_redirect_uri}"
        )

    async def exchange_code_for_token(self, auth_code: str) -> bool:
        """Exchange authorization code for access token."""
        try:
            async with aiohttp.ClientSession() as session:
                data = {
                    "code": auth_code,
                    "client_id": settings.upstox_api_key,
                    "client_secret": settings.upstox_api_secret,
                    "redirect_uri": settings.upstox_redirect_uri,
                    "grant_type": "authorization_code",
                }

                async with session.post(
                    "https://api.upstox.com/v2/login/authorization/token",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        self._access_token = result.get("access_token")
                        # Token typically valid for 1 day
                        self._token_expiry = datetime.now() + timedelta(hours=23)
                        logger.info("Upstox authentication successful")
                        return True
                    else:
                        error = await resp.text()
                        logger.error(f"Upstox token exchange failed: {error}")
                        return False

        except Exception as e:
            logger.error(f"Upstox token exchange error: {e}")
            return False

    async def connect(self) -> bool:
        """
        Initialize Upstox connection.

        If access token is configured in settings, use it directly.
        Otherwise, needs OAuth2 flow.
        """
        # Check if access token is configured
        if settings.upstox_access_token:
            self._access_token = settings.upstox_access_token
            self._token_expiry = datetime.now() + timedelta(hours=23)
            logger.info("Upstox using configured access token")
            return True

        if not settings.upstox_api_key or not settings.upstox_api_secret:
            logger.warning("Upstox API credentials not configured")
            return False

        # Without access token, we need OAuth flow
        logger.warning(
            f"Upstox requires OAuth2 login. Visit: {self.get_auth_url()}"
        )
        return False

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an active HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Accept": "application/json",
                }
            )
        return self._session

    async def close(self) -> None:
        """Close all connections."""
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session and not self._session.closed:
            await self._session.close()

    def get_instrument_key(self, symbol: str) -> Optional[str]:
        """Get Upstox instrument key for a symbol."""
        symbol = symbol.upper().strip()
        return SYMBOL_INSTRUMENT_MAP.get(symbol)

    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get live quote for a symbol."""
        if not self.is_authenticated:
            if not await self.connect():
                return None

        instrument_key = self.get_instrument_key(symbol)
        if not instrument_key:
            logger.warning(f"No instrument mapping for {symbol}")
            return None

        try:
            session = await self._ensure_session()
            url = f"{settings.upstox_base_url}/market-quote/quotes"

            async with session.get(
                url,
                params={"instrument_key": instrument_key},
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("status") == "success":
                        quote_data = result.get("data", {}).get(instrument_key, {})
                        return {
                            "symbol": symbol,
                            "ltp": float(quote_data.get("last_price", 0)),
                            "open": float(quote_data.get("ohlc", {}).get("open", 0)),
                            "high": float(quote_data.get("ohlc", {}).get("high", 0)),
                            "low": float(quote_data.get("ohlc", {}).get("low", 0)),
                            "close": float(quote_data.get("ohlc", {}).get("close", 0)),
                            "volume": int(quote_data.get("volume", 0)),
                            "source": "Upstox",
                        }
                else:
                    logger.error(f"Upstox quote error: {await resp.text()}")

        except Exception as e:
            logger.error(f"Error getting Upstox quote for {symbol}: {e}")

        return None

    async def get_historical_data(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.D1,
        lookback: int = 100,
    ) -> Optional[SymbolData]:
        """Fetch historical OHLCV data from Upstox."""
        if not self.is_authenticated:
            if not await self.connect():
                return None

        instrument_key = self.get_instrument_key(symbol)
        if not instrument_key:
            logger.warning(f"No instrument mapping for {symbol}")
            return None

        interval = INTERVAL_MAP.get(timeframe, "day")

        # Calculate date range
        to_date = datetime.now(IST)
        if timeframe in [Timeframe.M1, Timeframe.M5]:
            from_date = to_date - timedelta(days=5)
        elif timeframe in [Timeframe.M15, Timeframe.M30]:
            from_date = to_date - timedelta(days=30)
        elif timeframe == Timeframe.H1:
            from_date = to_date - timedelta(days=60)
        else:
            from_date = to_date - timedelta(days=365)

        try:
            session = await self._ensure_session()
            url = f"{settings.upstox_base_url}/historical-candle/{instrument_key}/{interval}/{to_date.strftime('%Y-%m-%d')}/{from_date.strftime('%Y-%m-%d')}"

            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"Upstox historical error: {await resp.text()}")
                    return None

                result = await resp.json()
                if result.get("status") != "success":
                    return None

                candles = result.get("data", {}).get("candles", [])
                if not candles:
                    return None

                # Upstox candle format: [timestamp, open, high, low, close, volume, oi]
                ohlcv_list = []
                for candle in candles[-lookback:]:
                    ts = datetime.fromisoformat(candle[0].replace("Z", "+00:00"))
                    ohlcv_list.append(
                        OHLCV(
                            timestamp=ts.astimezone(IST),
                            open=float(candle[1]),
                            high=float(candle[2]),
                            low=float(candle[3]),
                            close=float(candle[4]),
                            volume=int(candle[5]),
                        )
                    )

                if not ohlcv_list:
                    return None

                # Sort by timestamp (Upstox returns newest first)
                ohlcv_list.sort(key=lambda x: x.timestamp)

                current_price = ohlcv_list[-1].close
                prev_close = ohlcv_list[-2].close if len(ohlcv_list) > 1 else current_price

                return SymbolData(
                    symbol=symbol.upper(),
                    exchange=Exchange.NSE,
                    timeframe=timeframe,
                    ohlcv=ohlcv_list,
                    current_price=current_price,
                    day_change_percent=round(
                        ((current_price - prev_close) / prev_close) * 100, 2
                    ),
                )

        except Exception as e:
            logger.error(f"Error fetching Upstox historical data for {symbol}: {e}")
            return None

    # ============ WebSocket Streaming ============

    async def connect_websocket(self) -> bool:
        """Connect to Upstox WebSocket for real-time data."""
        if not self.is_authenticated:
            if not await self.connect():
                return False

        try:
            session = await self._ensure_session()

            # Get WebSocket authorization
            async with session.get(
                f"{settings.upstox_base_url}/feed/market-data-feed/authorize"
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Upstox WS auth failed: {await resp.text()}")
                    return False

                result = await resp.json()
                ws_url = result.get("data", {}).get("authorizedRedirectUri")
                if not ws_url:
                    logger.error("No WebSocket URL in Upstox response")
                    return False

            # Connect to WebSocket
            self._ws = await session.ws_connect(ws_url)
            logger.info("Upstox WebSocket connected")
            return True

        except Exception as e:
            logger.error(f"Upstox WebSocket connection error: {e}")
            return False

    async def subscribe(self, symbols: List[str]) -> bool:
        """Subscribe to real-time updates for symbols."""
        if not self._ws or self._ws.closed:
            if not await self.connect_websocket():
                return False

        instrument_keys = []
        for symbol in symbols:
            key = self.get_instrument_key(symbol.upper())
            if key:
                instrument_keys.append(key)

        if not instrument_keys:
            return False

        try:
            subscribe_msg = {
                "guid": "stockpro-subscribe",
                "method": "sub",
                "data": {
                    "mode": "full",  # full, ltpc, or ltp
                    "instrumentKeys": instrument_keys,
                },
            }
            await self._ws.send_json(subscribe_msg)
            logger.info(f"Subscribed to {len(instrument_keys)} symbols on Upstox")
            return True

        except Exception as e:
            logger.error(f"Upstox subscribe error: {e}")
            return False

    async def listen(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Listen for WebSocket messages and call callback with tick data."""
        if not self._ws or self._ws.closed:
            logger.error("WebSocket not connected")
            return

        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    # Parse and normalize tick data
                    tick = self._parse_tick(data)
                    if tick:
                        callback(tick)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"Upstox WebSocket error: {msg}")
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.warning("Upstox WebSocket closed")
                    break

        except Exception as e:
            logger.error(f"Upstox listen error: {e}")

    def _parse_tick(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse Upstox WebSocket message into normalized tick format."""
        try:
            if "feeds" not in data:
                return None

            # Reverse lookup instrument key to symbol
            key_to_symbol = {v: k for k, v in SYMBOL_INSTRUMENT_MAP.items()}

            ticks = []
            for instrument_key, feed_data in data.get("feeds", {}).items():
                symbol = key_to_symbol.get(instrument_key)
                if not symbol:
                    continue

                ff = feed_data.get("ff", {}).get("marketFF", {})
                ltpc = ff.get("ltpc", {})

                ticks.append({
                    "symbol": symbol,
                    "ltp": float(ltpc.get("ltp", 0)),
                    "open": float(ff.get("ohlc", {}).get("open", 0)),
                    "high": float(ff.get("ohlc", {}).get("high", 0)),
                    "low": float(ff.get("ohlc", {}).get("low", 0)),
                    "close": float(ltpc.get("cp", 0)),  # close/prev close
                    "volume": int(ff.get("v", 0)),
                    "timestamp": datetime.now(IST),
                    "source": "upstox",
                })

            return ticks[0] if len(ticks) == 1 else ticks if ticks else None

        except Exception as e:
            logger.debug(f"Upstox tick parse error: {e}")
            return None


# Singleton client
_upstox_client: Optional[UpstoxClient] = None


def get_upstox_client() -> UpstoxClient:
    """Get or create Upstox client singleton."""
    global _upstox_client
    if _upstox_client is None:
        _upstox_client = UpstoxClient()
    return _upstox_client


async def fetch_upstox_data(
    symbol: str,
    timeframe: Timeframe = Timeframe.D1,
    lookback: int = 100,
) -> Optional[SymbolData]:
    """Fetch market data from Upstox."""
    client = get_upstox_client()
    return await client.get_historical_data(symbol, timeframe, lookback)


async def get_upstox_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """Get live quote from Upstox."""
    client = get_upstox_client()
    return await client.get_quote(symbol)


async def validate_upstox_connection() -> bool:
    """Test Upstox connectivity."""
    client = get_upstox_client()
    return await client.connect()
