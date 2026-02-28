"""
Yahoo Finance Data Adapter

Fetches REAL market data from Yahoo Finance.
Indian stocks use .NS suffix (NSE) or .BO suffix (BSE).
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import yfinance as yf

from app.schemas.market import (
    OHLCV,
    SymbolData,
    Timeframe,
    Exchange,
)

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


# Timeframe mapping for yfinance
TIMEFRAME_MAP = {
    Timeframe.M1: "1m",
    Timeframe.M5: "5m",
    Timeframe.M15: "15m",
    Timeframe.M30: "30m",
    Timeframe.H1: "1h",
    Timeframe.H4: "4h",
    Timeframe.D1: "1d",
    Timeframe.W1: "1wk",
}

# Period mapping based on timeframe (use max period for more history)
PERIOD_MAP = {
    Timeframe.M1: "7d",
    Timeframe.M5: "60d",
    Timeframe.M15: "60d",
    Timeframe.M30: "60d",
    Timeframe.H1: "2y",
    Timeframe.H4: "2y",
    Timeframe.D1: "5y",    # 5 years of daily data
    Timeframe.W1: "max",   # Maximum weekly data
}


def get_yahoo_symbol(symbol: str, exchange: Exchange = Exchange.NSE) -> str:
    """Convert Indian symbol to Yahoo Finance format."""
    symbol = symbol.upper().strip()

    # Already has suffix
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        return symbol

    # Index symbols
    index_map = {
        "NIFTY": "^NSEI",
        "NIFTY50": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
    }

    if symbol in index_map:
        return index_map[symbol]

    # Regular stocks - add NSE suffix
    if exchange == Exchange.NSE:
        return f"{symbol}.NS"
    else:
        return f"{symbol}.BO"


async def fetch_yahoo_data(
    symbol: str,
    timeframe: Timeframe = Timeframe.D1,
    lookback: int = 100,
    exchange: Exchange = Exchange.NSE,
) -> Optional[SymbolData]:
    """
    Fetch real market data from Yahoo Finance.

    Args:
        symbol: Stock symbol (e.g., "TATASTEEL", "RELIANCE")
        timeframe: Data timeframe
        lookback: Number of candles to fetch
        exchange: NSE or BSE

    Returns:
        SymbolData with real OHLCV data, or None on failure
    """
    yahoo_symbol = get_yahoo_symbol(symbol, exchange)

    try:
        logger.info(f"Fetching {yahoo_symbol} from Yahoo Finance...")

        ticker = yf.Ticker(yahoo_symbol)

        # Get historical data
        interval = TIMEFRAME_MAP.get(timeframe, "1d")

        # Dynamically choose period based on lookback needed
        # For daily data: 252 trading days per year
        # For intraday: varies by market hours
        if timeframe == Timeframe.D1:
            if lookback <= 252:
                period = "1y"
            elif lookback <= 504:
                period = "2y"
            elif lookback <= 1260:
                period = "5y"
            else:
                period = "max"
        elif timeframe == Timeframe.W1:
            if lookback <= 260:
                period = "5y"
            else:
                period = "max"
        else:
            period = PERIOD_MAP.get(timeframe, "1y")

        hist = ticker.history(period=period, interval=interval)

        if hist.empty:
            logger.warning(f"No data returned for {yahoo_symbol}")
            return None

        # Limit to lookback
        hist = hist.tail(lookback)

        # Convert to OHLCV list
        ohlcv_list = []
        for idx, row in hist.iterrows():
            # Handle timezone-aware datetime
            if hasattr(idx, 'tz_localize'):
                ts = idx.to_pydatetime()
            else:
                ts = idx.to_pydatetime()

            # Make timezone aware if not already
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=IST)

            ohlcv_list.append(
                OHLCV(
                    timestamp=ts,
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                )
            )

        if not ohlcv_list:
            return None

        # Current price info
        current_price = ohlcv_list[-1].close
        prev_close = ohlcv_list[-2].close if len(ohlcv_list) > 1 else current_price
        day_change = current_price - prev_close
        day_change_pct = (day_change / prev_close * 100) if prev_close > 0 else 0

        # Try to get live quote for more accurate current price
        try:
            info = ticker.info
            if "currentPrice" in info and info["currentPrice"]:
                current_price = float(info["currentPrice"])
            elif "regularMarketPrice" in info and info["regularMarketPrice"]:
                current_price = float(info["regularMarketPrice"])

            if "previousClose" in info and info["previousClose"]:
                prev_close = float(info["previousClose"])
                day_change = current_price - prev_close
                day_change_pct = (day_change / prev_close * 100) if prev_close > 0 else 0
        except Exception as e:
            logger.debug(f"Could not get live quote: {e}")

        return SymbolData(
            symbol=symbol.upper(),
            exchange=exchange,
            timeframe=timeframe,
            ohlcv=ohlcv_list,
            current_price=current_price,
            day_change_percent=round(day_change_pct, 2),
        )

    except Exception as e:
        logger.error(f"Error fetching {symbol} from Yahoo Finance: {e}")
        return None


async def get_stock_info(symbol: str, exchange: Exchange = Exchange.NSE) -> dict:
    """Get detailed stock information."""
    yahoo_symbol = get_yahoo_symbol(symbol, exchange)

    try:
        ticker = yf.Ticker(yahoo_symbol)
        info = ticker.info

        return {
            "symbol": symbol.upper(),
            "name": info.get("longName") or info.get("shortName", symbol),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "market_cap": info.get("marketCap", 0),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice", 0),
            "previous_close": info.get("previousClose", 0),
            "day_high": info.get("dayHigh", 0),
            "day_low": info.get("dayLow", 0),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
            "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
            "volume": info.get("volume", 0),
            "avg_volume": info.get("averageVolume", 0),
            "pe_ratio": info.get("trailingPE", 0),
            "dividend_yield": info.get("dividendYield", 0),
        }
    except Exception as e:
        logger.error(f"Error getting info for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


async def validate_symbol(symbol: str, exchange: Exchange = Exchange.NSE) -> bool:
    """Check if a symbol exists and has data."""
    yahoo_symbol = get_yahoo_symbol(symbol, exchange)

    try:
        ticker = yf.Ticker(yahoo_symbol)
        hist = ticker.history(period="5d")
        return not hist.empty
    except Exception:
        return False
