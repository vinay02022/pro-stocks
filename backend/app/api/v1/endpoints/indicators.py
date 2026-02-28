"""
Indicator API Endpoints

Endpoints for technical indicator calculations.
"""

import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.schemas.market import Timeframe, DataRequest
from app.schemas.indicators import IndicatorOutput
from app.services.data_ingestion import get_data_ingestion_service
from app.services.indicators import get_indicator_service
from app.services.data_ingestion.angelone_adapter import get_angelone_quote
from app.core.market_hours import is_market_open, get_market_status

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

router = APIRouter()


class RealtimeQuoteResponse(BaseModel):
    """Response for real-time quote endpoint."""
    symbol: str
    ltp: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: str
    source: str
    is_market_open: bool


@router.get("/{symbol}/realtime", response_model=RealtimeQuoteResponse)
async def get_realtime_quote(symbol: str):
    """
    Get real-time quote for a symbol.

    Optimized for low latency (<100ms) polling.
    Primary source: Angel One API
    Fallback: Yahoo Finance

    Returns minimal data for efficient real-time updates:
    - LTP (Last Traded Price)
    - OHLC for current session
    - Volume
    - Timestamp
    """
    symbol = symbol.upper().strip()
    market_open = is_market_open()

    # Try Angel One first (real-time NSE data)
    try:
        quote = await get_angelone_quote(symbol)
        if quote:
            return RealtimeQuoteResponse(
                symbol=symbol,
                ltp=quote["ltp"],
                open=quote["open"],
                high=quote["high"],
                low=quote["low"],
                close=quote["close"],
                volume=quote["volume"],
                timestamp=datetime.now(IST).isoformat(),
                source="Angel One",
                is_market_open=market_open,
            )
    except Exception as e:
        logger.debug(f"Angel One quote failed for {symbol}: {e}")

    # Fallback to Yahoo Finance
    try:
        import yfinance as yf

        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.info

        # Get fast quote data
        ltp = info.get("currentPrice") or info.get("regularMarketPrice", 0)
        open_price = info.get("regularMarketOpen", ltp)
        high = info.get("regularMarketDayHigh", ltp)
        low = info.get("regularMarketDayLow", ltp)
        close = info.get("previousClose", ltp)
        volume = info.get("regularMarketVolume", 0)

        if ltp == 0:
            raise HTTPException(status_code=404, detail=f"No quote data for {symbol}")

        return RealtimeQuoteResponse(
            symbol=symbol,
            ltp=ltp,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume or 0,
            timestamp=datetime.now(IST).isoformat(),
            source="Yahoo Finance",
            is_market_open=market_open,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Yahoo Finance quote failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get quote for {symbol}")


@router.get("/{symbol}", response_model=IndicatorOutput)
async def get_indicators(
    symbol: str,
    timeframe: Timeframe = Timeframe.M15,
    lookback: int = Query(default=100, ge=20, le=500),
    portfolio_value: Optional[float] = Query(default=None),
    risk_percent: float = Query(default=1.0, ge=0.1, le=5.0),
):
    """
    Get complete indicator analysis for a symbol.

    Returns:
        - Trend indicators (EMA, SMA, ADX)
        - Momentum indicators (RSI, MACD, Stochastic)
        - Volatility indicators (ATR, Bollinger Bands)
        - Volume indicators (VWAP, OBV)
        - Support/Resistance levels
        - Risk metrics (suggested SL/TP)
    """
    # Fetch market data
    data_service = get_data_ingestion_service()
    request = DataRequest(
        symbols=[symbol.upper()],
        timeframe=timeframe,
        lookback=lookback,
    )
    data_result = await data_service.execute(request)

    if not data_result.snapshot.symbols:
        raise HTTPException(status_code=404, detail=f"Data not found for {symbol}")

    symbol_data = data_result.snapshot.symbols[0]

    # Calculate indicators
    indicator_service = get_indicator_service()
    try:
        output = await indicator_service.calculate_for_symbol(
            symbol_data,
            portfolio_value=portfolio_value,
            risk_percent=risk_percent,
        )
        return output
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indicator calculation failed: {e}")


@router.get("/{symbol}/levels")
async def get_levels(
    symbol: str,
    timeframe: Timeframe = Timeframe.D1,
):
    """
    Get support/resistance levels for a symbol.
    """
    # Fetch market data
    data_service = get_data_ingestion_service()
    request = DataRequest(
        symbols=[symbol.upper()],
        timeframe=timeframe,
        lookback=100,
    )
    data_result = await data_service.execute(request)

    if not data_result.snapshot.symbols:
        raise HTTPException(status_code=404, detail=f"Data not found for {symbol}")

    symbol_data = data_result.snapshot.symbols[0]

    # Calculate indicators (we only need levels)
    indicator_service = get_indicator_service()
    output = await indicator_service.calculate_for_symbol(symbol_data)

    return {
        "symbol": symbol.upper(),
        "levels": output.levels.model_dump(),
        "current_price": output.price.current,
    }


@router.get("/{symbol}/risk-metrics")
async def get_risk_metrics(
    symbol: str,
    portfolio_value: Optional[float] = Query(default=None),
    risk_percent: float = Query(default=1.0, ge=0.1, le=5.0),
):
    """
    Get risk metrics and position sizing for a symbol.

    Args:
        portfolio_value: Total portfolio value for position sizing
        risk_percent: Percentage of portfolio to risk per trade
    """
    # Fetch market data
    data_service = get_data_ingestion_service()
    request = DataRequest(
        symbols=[symbol.upper()],
        timeframe=Timeframe.D1,
        lookback=50,
    )
    data_result = await data_service.execute(request)

    if not data_result.snapshot.symbols:
        raise HTTPException(status_code=404, detail=f"Data not found for {symbol}")

    symbol_data = data_result.snapshot.symbols[0]

    # Calculate indicators with position sizing
    indicator_service = get_indicator_service()
    output = await indicator_service.calculate_for_symbol(
        symbol_data,
        portfolio_value=portfolio_value,
        risk_percent=risk_percent,
    )

    return {
        "symbol": symbol.upper(),
        "current_price": output.price.current,
        "risk_metrics": output.risk_metrics.model_dump(),
    }


@router.get("/{symbol}/chart-data")
async def get_chart_indicators(
    symbol: str,
    timeframe: Timeframe = Timeframe.D1,
    lookback: int = Query(default=300, ge=20, le=1000),
):
    """
    Get OHLCV data with indicator series for charting.

    Returns arrays that can be directly plotted on charts:
    - Candles (OHLCV)
    - Moving averages (EMA 9, 21, 50, 200 / SMA 20)
    - RSI series
    - MACD series (MACD line, signal, histogram)
    - Bollinger Bands
    - Volume
    """
    import numpy as np

    # Fetch market data
    data_service = get_data_ingestion_service()
    request = DataRequest(
        symbols=[symbol.upper()],
        timeframe=timeframe,
        lookback=lookback,
    )
    data_result = await data_service.execute(request)

    if not data_result.snapshot.symbols:
        raise HTTPException(status_code=404, detail=f"Data not found for {symbol}")

    symbol_data = data_result.snapshot.symbols[0]
    candles = symbol_data.ohlcv

    # Extract price arrays
    closes = np.array([c.close for c in candles])
    highs = np.array([c.high for c in candles])
    lows = np.array([c.low for c in candles])
    volumes = np.array([c.volume for c in candles])

    # Helper functions for indicator calculation
    def ema(data, period):
        result = np.zeros_like(data)
        result[:period] = np.nan
        multiplier = 2 / (period + 1)
        result[period - 1] = np.mean(data[:period])
        for i in range(period, len(data)):
            result[i] = (data[i] * multiplier) + (result[i - 1] * (1 - multiplier))
        return result

    def sma(data, period):
        result = np.zeros_like(data)
        result[:period - 1] = np.nan
        for i in range(period - 1, len(data)):
            result[i] = np.mean(data[i - period + 1:i + 1])
        return result

    def rsi(data, period=14):
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.zeros(len(data))
        avg_loss = np.zeros(len(data))

        avg_gain[period] = np.mean(gains[:period])
        avg_loss[period] = np.mean(losses[:period])

        for i in range(period + 1, len(data)):
            avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
            avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period

        rs = np.where(avg_loss != 0, avg_gain / avg_loss, 100)
        rsi_values = 100 - (100 / (1 + rs))
        rsi_values[:period] = np.nan
        return rsi_values

    # Calculate indicators
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)
    sma20 = sma(closes, 20)

    # RSI
    rsi_values = rsi(closes, 14)

    # MACD
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = ema12 - ema26
    macd_signal = ema(macd_line, 9)
    macd_histogram = macd_line - macd_signal

    # Bollinger Bands
    bb_middle = sma20
    bb_std = np.zeros_like(closes)
    for i in range(19, len(closes)):
        bb_std[i] = np.std(closes[i - 19:i + 1])
    bb_upper = bb_middle + (2 * bb_std)
    bb_lower = bb_middle - (2 * bb_std)

    # Build response with series data
    def to_series(timestamps, values):
        """Convert to chart-compatible series format."""
        series = []
        for i, (ts, val) in enumerate(zip(timestamps, values)):
            if not np.isnan(val):
                series.append({
                    "time": ts.isoformat(),
                    "value": round(float(val), 2)
                })
        return series

    timestamps = [c.timestamp for c in candles]

    response = {
        "symbol": symbol.upper(),
        "timeframe": timeframe.value,
        "current_price": float(closes[-1]),
        "candles": [
            {
                "time": c.timestamp.isoformat(),
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ],
        "overlays": {
            "ema9": to_series(timestamps, ema9),
            "ema21": to_series(timestamps, ema21),
            "ema50": to_series(timestamps, ema50),
            "sma20": to_series(timestamps, sma20),
            "bb_upper": to_series(timestamps, bb_upper),
            "bb_middle": to_series(timestamps, bb_middle),
            "bb_lower": to_series(timestamps, bb_lower),
        },
        "panels": {
            "rsi": {
                "data": to_series(timestamps, rsi_values),
                "overbought": 70,
                "oversold": 30,
            },
            "macd": {
                "macd": to_series(timestamps, macd_line),
                "signal": to_series(timestamps, macd_signal),
                "histogram": [
                    {
                        "time": ts.isoformat(),
                        "value": round(float(val), 4) if not np.isnan(val) else 0,
                        "color": "#22c55e" if val >= 0 else "#ef4444"
                    }
                    for ts, val in zip(timestamps, macd_histogram)
                    if not np.isnan(val)
                ],
            },
            "volume": [
                {
                    "time": c.timestamp.isoformat(),
                    "value": c.volume,
                    "color": "#22c55e80" if c.close >= c.open else "#ef444480"
                }
                for c in candles
            ],
        },
    }

    return response


@router.get("/{symbol}/summary")
async def get_indicator_summary(symbol: str):
    """
    Get a quick summary of key indicators.
    """
    # Fetch market data
    data_service = get_data_ingestion_service()
    request = DataRequest(
        symbols=[symbol.upper()],
        timeframe=Timeframe.D1,
        lookback=50,
    )
    data_result = await data_service.execute(request)

    if not data_result.snapshot.symbols:
        raise HTTPException(status_code=404, detail=f"Data not found for {symbol}")

    symbol_data = data_result.snapshot.symbols[0]

    # Calculate indicators
    indicator_service = get_indicator_service()
    output = await indicator_service.calculate_for_symbol(symbol_data)

    # Extract key values
    trend = output.indicators.get("trend", {})
    momentum = output.indicators.get("momentum", {})
    volatility = output.indicators.get("volatility", {})

    return {
        "symbol": symbol.upper(),
        "price": output.price.current,
        "change_percent": output.price.change_percent,
        "trend": {
            "direction": trend.get("trend_direction"),
            "strength": trend.get("trend_strength"),
        },
        "momentum": {
            "rsi": momentum.get("rsi_14"),
            "macd_histogram": momentum.get("macd", {}).get("histogram"),
        },
        "volatility": {
            "atr_percent": volatility.get("atr_percent"),
            "zone": output.risk_metrics.volatility_zone,
        },
        "levels": {
            "nearest_support": output.levels.support[0] if output.levels.support else None,
            "nearest_resistance": output.levels.resistance[0] if output.levels.resistance else None,
        },
    }
