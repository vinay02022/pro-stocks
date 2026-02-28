"""
Market Scanner API Endpoints

Scan stocks for technical patterns and trading signals.
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException

from app.services.scanner import get_scanner, PatternType, ScanResult
from app.schemas.market import Timeframe

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/scan")
async def scan_stocks(
    symbols: str = Query(None, description="Comma-separated symbols (default: Nifty 50)"),
    patterns: str = Query("all", description="Comma-separated patterns: breakout,momentum,volume_spike,ema_crossover,rsi_extreme,macd_crossover,sr_bounce,bb_squeeze,all"),
    timeframe: str = Query("1d", description="Timeframe: 1m, 5m, 15m, 1h, 1d"),
    min_score: float = Query(40, ge=0, le=100, description="Minimum pattern score"),
    signal: str = Query(None, description="Filter by signal: BULLISH, BEARISH"),
):
    """
    Scan stocks for technical patterns.

    Returns stocks matching the specified patterns with scores.

    Example:
    - `/scanner/scan` - Scan Nifty 50 for all patterns
    - `/scanner/scan?patterns=breakout,momentum&min_score=60` - Scan for breakouts and momentum
    - `/scanner/scan?signal=BULLISH` - Only bullish signals
    """
    scanner = get_scanner()

    # Parse patterns
    pattern_list = []
    for p in patterns.lower().split(","):
        p = p.strip()
        if p == "all":
            pattern_list = [PatternType.ALL]
            break
        try:
            pattern_list.append(PatternType(p))
        except ValueError:
            pass  # Skip invalid patterns

    if not pattern_list:
        pattern_list = [PatternType.ALL]

    # Parse timeframe
    tf_map = {
        "1m": Timeframe.M1,
        "5m": Timeframe.M5,
        "15m": Timeframe.M15,
        "1h": Timeframe.H1,
        "1d": Timeframe.D1,
        "1w": Timeframe.W1,
    }
    tf = tf_map.get(timeframe.lower(), Timeframe.D1)

    # Parse signal filter
    signal_filter = signal.upper() if signal and signal.upper() in ["BULLISH", "BEARISH"] else None

    try:
        if symbols:
            # Scan specific symbols
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            results = await scanner.scan_multiple(
                symbols=symbol_list,
                patterns=pattern_list,
                timeframe=tf,
                min_score=min_score,
                signal_filter=signal_filter,
            )
        else:
            # Scan Nifty 50 by default
            results = await scanner.scan_nifty50(
                patterns=pattern_list,
                timeframe=tf,
                min_score=min_score,
                signal_filter=signal_filter,
            )

        return {
            "count": len(results),
            "filters": {
                "patterns": [p.value for p in pattern_list],
                "timeframe": timeframe,
                "min_score": min_score,
                "signal_filter": signal_filter,
            },
            "results": [r.to_dict() for r in results],
        }

    except Exception as e:
        logger.error(f"Scanner error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-bullish")
async def get_top_bullish(
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    timeframe: str = Query("1d", description="Timeframe"),
):
    """
    Get top bullish stocks from Nifty 50.

    Returns stocks with the strongest bullish patterns.
    """
    scanner = get_scanner()
    tf_map = {"1m": Timeframe.M1, "5m": Timeframe.M5, "15m": Timeframe.M15, "1h": Timeframe.H1, "1d": Timeframe.D1}
    tf = tf_map.get(timeframe.lower(), Timeframe.D1)

    results = await scanner.get_top_bullish(limit=limit, timeframe=tf)

    return {
        "signal": "BULLISH",
        "count": len(results),
        "results": [r.to_dict() for r in results],
    }


@router.get("/top-bearish")
async def get_top_bearish(
    limit: int = Query(10, ge=1, le=50, description="Number of results"),
    timeframe: str = Query("1d", description="Timeframe"),
):
    """
    Get top bearish stocks from Nifty 50.

    Returns stocks with the strongest bearish patterns.
    """
    scanner = get_scanner()
    tf_map = {"1m": Timeframe.M1, "5m": Timeframe.M5, "15m": Timeframe.M15, "1h": Timeframe.H1, "1d": Timeframe.D1}
    tf = tf_map.get(timeframe.lower(), Timeframe.D1)

    results = await scanner.get_top_bearish(limit=limit, timeframe=tf)

    return {
        "signal": "BEARISH",
        "count": len(results),
        "results": [r.to_dict() for r in results],
    }


@router.get("/breakouts")
async def get_breakouts(
    timeframe: str = Query("1d", description="Timeframe"),
):
    """
    Get stocks with breakout patterns.

    Identifies stocks breaking above resistance or below support with volume.
    """
    scanner = get_scanner()
    tf_map = {"1m": Timeframe.M1, "5m": Timeframe.M5, "15m": Timeframe.M15, "1h": Timeframe.H1, "1d": Timeframe.D1}
    tf = tf_map.get(timeframe.lower(), Timeframe.D1)

    results = await scanner.get_breakouts(timeframe=tf)

    return {
        "pattern": "breakout",
        "count": len(results),
        "results": [r.to_dict() for r in results],
    }


@router.get("/momentum")
async def get_momentum_stocks(
    timeframe: str = Query("1d", description="Timeframe"),
):
    """
    Get stocks with strong momentum.

    Identifies stocks with strong price momentum based on RSI, ROC, and volume.
    """
    scanner = get_scanner()
    tf_map = {"1m": Timeframe.M1, "5m": Timeframe.M5, "15m": Timeframe.M15, "1h": Timeframe.H1, "1d": Timeframe.D1}
    tf = tf_map.get(timeframe.lower(), Timeframe.D1)

    results = await scanner.get_momentum_stocks(timeframe=tf)

    return {
        "pattern": "momentum",
        "count": len(results),
        "results": [r.to_dict() for r in results],
    }


@router.get("/volume-spikes")
async def get_volume_spikes(
    timeframe: str = Query("1d", description="Timeframe"),
):
    """
    Get stocks with unusual volume spikes.

    Identifies stocks with significantly higher volume than average,
    which may indicate institutional activity.
    """
    scanner = get_scanner()
    tf_map = {"1m": Timeframe.M1, "5m": Timeframe.M5, "15m": Timeframe.M15, "1h": Timeframe.H1, "1d": Timeframe.D1}
    tf = tf_map.get(timeframe.lower(), Timeframe.D1)

    results = await scanner.get_volume_spikes(timeframe=tf)

    return {
        "pattern": "volume_spike",
        "count": len(results),
        "results": [r.to_dict() for r in results],
    }


@router.get("/symbol/{symbol}")
async def scan_single_symbol(
    symbol: str,
    patterns: str = Query("all", description="Comma-separated patterns"),
    timeframe: str = Query("1d", description="Timeframe"),
):
    """
    Scan a single symbol for all patterns.

    Returns detailed pattern analysis for the specified stock.
    """
    scanner = get_scanner()

    # Parse patterns
    pattern_list = []
    for p in patterns.lower().split(","):
        p = p.strip()
        if p == "all":
            pattern_list = [PatternType.ALL]
            break
        try:
            pattern_list.append(PatternType(p))
        except ValueError:
            pass

    if not pattern_list:
        pattern_list = [PatternType.ALL]

    tf_map = {"1m": Timeframe.M1, "5m": Timeframe.M5, "15m": Timeframe.M15, "1h": Timeframe.H1, "1d": Timeframe.D1}
    tf = tf_map.get(timeframe.lower(), Timeframe.D1)

    result = await scanner.scan_symbol(
        symbol=symbol.upper(),
        patterns=pattern_list,
        timeframe=tf,
    )

    if not result:
        raise HTTPException(status_code=404, detail=f"Could not scan {symbol}")

    return result.to_dict()


@router.get("/patterns")
async def get_available_patterns():
    """
    Get list of available pattern types for scanning.
    """
    return {
        "patterns": [
            {
                "id": "breakout",
                "name": "Breakout",
                "description": "Price breaking above resistance or below support with volume confirmation",
            },
            {
                "id": "momentum",
                "name": "Momentum",
                "description": "Strong price momentum based on RSI, rate of change, and volume trend",
            },
            {
                "id": "volume_spike",
                "name": "Volume Spike",
                "description": "Unusual volume indicating potential institutional activity",
            },
            {
                "id": "ema_crossover",
                "name": "EMA Crossover",
                "description": "Fast EMA crossing slow EMA (Golden Cross / Death Cross)",
            },
            {
                "id": "rsi_extreme",
                "name": "RSI Extreme",
                "description": "RSI in overbought or oversold territory",
            },
            {
                "id": "macd_crossover",
                "name": "MACD Crossover",
                "description": "MACD line crossing signal line",
            },
            {
                "id": "sr_bounce",
                "name": "Support/Resistance Bounce",
                "description": "Price bouncing off support or resistance levels",
            },
            {
                "id": "bb_squeeze",
                "name": "Bollinger Squeeze",
                "description": "Low volatility squeeze indicating potential big move",
            },
        ],
    }
