"""
Angel One SmartAPI Data Adapter

Provides real-time market data from Angel One broker.
Used as secondary data source to cross-validate with Yahoo Finance.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from SmartApi import SmartConnect
import pyotp

from app.core.config import settings
from app.schemas.market import (
    OHLCV,
    SymbolData,
    Timeframe,
    Exchange,
)

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


# Angel One interval mapping
INTERVAL_MAP = {
    Timeframe.M1: "ONE_MINUTE",
    Timeframe.M5: "FIVE_MINUTE",
    Timeframe.M15: "FIFTEEN_MINUTE",
    Timeframe.M30: "THIRTY_MINUTE",
    Timeframe.H1: "ONE_HOUR",
    Timeframe.D1: "ONE_DAY",
}

# Common NSE symbols to token mapping (partial list - extend as needed)
# You can get full list from Angel One's symbol master file
SYMBOL_TOKEN_MAP = {
    # Nifty 50 stocks
    "RELIANCE": "2885",
    "TCS": "11536",
    "HDFCBANK": "1333",
    "INFY": "1594",
    "ICICIBANK": "4963",
    "HINDUNILVR": "1394",
    "SBIN": "3045",
    "BHARTIARTL": "10604",
    "ITC": "1660",
    "KOTAKBANK": "1922",
    "LT": "11483",
    "AXISBANK": "5900",
    "ASIANPAINT": "236",
    "MARUTI": "10999",
    "TITAN": "3506",
    "SUNPHARMA": "3351",
    "BAJFINANCE": "317",
    "WIPRO": "3787",
    "ULTRACEMCO": "11532",
    "HCLTECH": "7229",
    "TATAMOTORS": "3456",
    "TATASTEEL": "3499",
    "NTPC": "11630",
    "POWERGRID": "14977",
    "M&M": "2031",
    "TECHM": "13538",
    "INDUSINDBK": "5258",
    "DRREDDY": "881",
    "BAJAJFINSV": "16675",
    "NESTLEIND": "17963",
    "ONGC": "2475",
    "JSWSTEEL": "11723",
    "GRASIM": "1232",
    "ADANIENT": "25",
    "ADANIPORTS": "15083",
    "COALINDIA": "20374",
    "BPCL": "526",
    "CIPLA": "694",
    "DIVISLAB": "10940",
    "EICHERMOT": "910",
    "HEROMOTOCO": "1348",
    "HINDALCO": "1363",
    "TATACONSUM": "3432",
    "APOLLOHOSP": "157",
    "SBILIFE": "21808",
    "BRITANNIA": "547",
    "BAJAJ-AUTO": "16669",
    "UPL": "11287",
    "LTIM": "17818",
    # Indices
    "NIFTY": "99926000",
    "BANKNIFTY": "99926009",
    "NIFTY50": "99926000",
}


class AngelOneClient:
    """
    Angel One SmartAPI client wrapper.

    Handles authentication and data fetching.
    """

    def __init__(self):
        self._smart_api: Optional[SmartConnect] = None
        self._auth_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._feed_token: Optional[str] = None
        self._last_auth_time: Optional[datetime] = None

    def _get_totp(self) -> str:
        """Generate TOTP if secret is configured."""
        if settings.angel_one_totp_secret:
            totp = pyotp.TOTP(settings.angel_one_totp_secret)
            return totp.now()
        return ""

    async def connect(self) -> bool:
        """
        Authenticate with Angel One SmartAPI.

        Returns True if successful, False otherwise.
        """
        try:
            # Use Historical API key for data access
            api_key = getattr(settings, 'angel_one_historical_api_key', None)
            if not api_key:
                api_key = getattr(settings, 'angel_one_api_key', None)

            if not api_key:
                logger.error("No Angel One API key configured")
                return False

            self._smart_api = SmartConnect(api_key=api_key)

            # Generate TOTP if configured
            totp = self._get_totp()

            # Login
            data = self._smart_api.generateSession(
                clientCode=settings.angel_one_client_id,
                password=settings.angel_one_password,
                totp=totp if totp else None,
            )

            if data.get("status"):
                self._auth_token = data["data"]["jwtToken"]
                self._refresh_token = data["data"]["refreshToken"]
                self._feed_token = self._smart_api.getfeedToken()
                self._last_auth_time = datetime.now()
                logger.info("Angel One authentication successful")
                return True
            else:
                error_msg = data.get('message', 'Unknown error')
                error_code = data.get('errorcode', '')

                # Helpful error messages
                if 'totp' in error_msg.lower() or error_code == 'AB1050':
                    logger.warning(
                        "Angel One requires TOTP authentication. "
                        "To enable: 1) Set up authenticator app with Angel One, "
                        "2) Add ANGEL_ONE_TOTP_SECRET to .env file. "
                        "System will use Yahoo Finance as primary source."
                    )
                else:
                    logger.error(f"Angel One auth failed: {error_msg}")
                return False

        except Exception as e:
            logger.error(f"Angel One connection error: {e}")
            return False

    def _ensure_connected(self) -> bool:
        """Ensure we have a valid connection."""
        if self._smart_api is None:
            return False

        # Re-auth if token is old (>8 hours)
        if self._last_auth_time:
            age = datetime.now() - self._last_auth_time
            if age > timedelta(hours=8):
                import asyncio
                return asyncio.get_event_loop().run_until_complete(self.connect())

        return self._auth_token is not None

    def get_token(self, symbol: str) -> Optional[str]:
        """Get Angel One token for a symbol."""
        symbol = symbol.upper().strip()
        return SYMBOL_TOKEN_MAP.get(symbol)

    async def get_quote(self, symbol: str) -> Optional[dict]:
        """Get live quote for a symbol."""
        if not self._ensure_connected():
            if not await self.connect():
                return None

        token = self.get_token(symbol)
        if not token:
            logger.warning(f"No token mapping for {symbol}")
            return None

        try:
            data = self._smart_api.ltpData(
                exchange="NSE",
                tradingsymbol=symbol,
                symboltoken=token,
            )

            if data.get("status"):
                ltp_data = data["data"]
                return {
                    "symbol": symbol,
                    "ltp": float(ltp_data.get("ltp", 0)),
                    "open": float(ltp_data.get("open", 0)),
                    "high": float(ltp_data.get("high", 0)),
                    "low": float(ltp_data.get("low", 0)),
                    "close": float(ltp_data.get("close", 0)),
                    "volume": int(ltp_data.get("volume", 0)),
                    "source": "Angel One",
                }
            return None

        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return None

    async def get_historical_data(
        self,
        symbol: str,
        timeframe: Timeframe = Timeframe.D1,
        lookback: int = 100,
    ) -> Optional[SymbolData]:
        """
        Fetch historical OHLCV data from Angel One.
        """
        if not self._ensure_connected():
            if not await self.connect():
                return None

        token = self.get_token(symbol)
        if not token:
            logger.warning(f"No token mapping for {symbol}")
            return None

        interval = INTERVAL_MAP.get(timeframe, "ONE_DAY")

        # Calculate date range
        to_date = datetime.now()
        if timeframe in [Timeframe.M1, Timeframe.M5]:
            from_date = to_date - timedelta(days=5)
        elif timeframe in [Timeframe.M15, Timeframe.M30]:
            from_date = to_date - timedelta(days=30)
        elif timeframe == Timeframe.H1:
            from_date = to_date - timedelta(days=60)
        else:
            from_date = to_date - timedelta(days=365)

        try:
            params = {
                "exchange": "NSE",
                "symboltoken": token,
                "interval": interval,
                "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
                "todate": to_date.strftime("%Y-%m-%d %H:%M"),
            }

            data = self._smart_api.getCandleData(params)

            if not data.get("status") or not data.get("data"):
                logger.warning(f"No historical data for {symbol}")
                return None

            candles = data["data"]

            # Convert to OHLCV list
            ohlcv_list = []
            for candle in candles[-lookback:]:
                # Candle format: [timestamp, open, high, low, close, volume]
                ts = datetime.strptime(candle[0], "%Y-%m-%dT%H:%M:%S%z")
                ohlcv_list.append(
                    OHLCV(
                        timestamp=ts,
                        open=float(candle[1]),
                        high=float(candle[2]),
                        low=float(candle[3]),
                        close=float(candle[4]),
                        volume=int(candle[5]),
                    )
                )

            if not ohlcv_list:
                return None

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
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None


# Singleton client
_angel_client: Optional[AngelOneClient] = None


def get_angel_client() -> AngelOneClient:
    """Get or create Angel One client singleton."""
    global _angel_client
    if _angel_client is None:
        _angel_client = AngelOneClient()
    return _angel_client


async def fetch_angelone_data(
    symbol: str,
    timeframe: Timeframe = Timeframe.D1,
    lookback: int = 100,
) -> Optional[SymbolData]:
    """
    Fetch market data from Angel One.

    Convenience function that uses the singleton client.
    """
    client = get_angel_client()
    return await client.get_historical_data(symbol, timeframe, lookback)


async def get_angelone_quote(symbol: str) -> Optional[dict]:
    """Get live quote from Angel One."""
    client = get_angel_client()
    return await client.get_quote(symbol)


async def validate_angelone_connection() -> bool:
    """Test Angel One connectivity."""
    client = get_angel_client()
    return await client.connect()
