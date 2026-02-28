"""
Multi-Source Data Aggregator

Fetches data from multiple sources (Yahoo Finance + Angel One) and
cross-validates for higher confidence trading decisions.
"""

import logging
from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass

from app.schemas.market import SymbolData, Timeframe, Exchange
from app.services.data_ingestion.yahoo_adapter import fetch_yahoo_data
from app.services.data_ingestion.angelone_adapter import (
    fetch_angelone_data,
    get_angelone_quote,
    validate_angelone_connection,
)

logger = logging.getLogger(__name__)


@dataclass
class DataQualityScore:
    """Quality assessment of fetched data."""

    source_count: int  # Number of sources that returned data
    price_match: bool  # Whether prices match within tolerance
    price_deviation_percent: float  # Price difference between sources
    volume_confirmed: bool  # Volume data available
    data_freshness: str  # "live", "delayed", "historical"
    confidence: float  # Overall confidence score 0-1
    warnings: list[str]

    @property
    def is_reliable(self) -> bool:
        """Check if data is reliable enough for trading decisions."""
        return self.source_count >= 1 and self.confidence >= 0.6


@dataclass
class MultiSourceData:
    """Aggregated data from multiple sources with quality metrics."""

    symbol: str
    primary_data: SymbolData
    secondary_data: Optional[SymbolData]
    quality: DataQualityScore
    sources_used: list[str]
    fetch_timestamp: datetime


# Price tolerance for cross-validation (1% difference allowed)
PRICE_TOLERANCE_PERCENT = 1.0


async def fetch_multi_source_data(
    symbol: str,
    timeframe: Timeframe = Timeframe.D1,
    lookback: int = 100,
    exchange: Exchange = Exchange.NSE,
) -> Optional[MultiSourceData]:
    """
    Fetch market data from multiple sources with cross-validation.

    Priority:
    1. Yahoo Finance (free, reliable for EOD)
    2. Angel One (real-time if connected)

    Returns aggregated data with quality score.
    """
    warnings = []
    sources_used = []
    primary_data: Optional[SymbolData] = None
    secondary_data: Optional[SymbolData] = None

    # Fetch from Yahoo Finance (primary for historical)
    try:
        yahoo_data = await fetch_yahoo_data(
            symbol=symbol,
            timeframe=timeframe,
            lookback=lookback,
            exchange=exchange,
        )
        if yahoo_data:
            primary_data = yahoo_data
            sources_used.append("Yahoo Finance")
            logger.info(f"Yahoo Finance: {symbol} @ Rs.{yahoo_data.current_price}")
    except Exception as e:
        logger.warning(f"Yahoo Finance failed for {symbol}: {e}")
        warnings.append(f"Yahoo Finance unavailable: {str(e)}")

    # Fetch from Angel One (secondary, real-time)
    try:
        angelone_data = await fetch_angelone_data(
            symbol=symbol,
            timeframe=timeframe,
            lookback=lookback,
        )
        if angelone_data:
            if primary_data is None:
                primary_data = angelone_data
            else:
                secondary_data = angelone_data
            sources_used.append("Angel One")
            logger.info(f"Angel One: {symbol} @ Rs.{angelone_data.current_price}")
    except Exception as e:
        logger.debug(f"Angel One failed for {symbol}: {e}")
        # Don't warn - Angel One is optional secondary source

    # If no data from any source
    if primary_data is None:
        logger.error(f"No data available for {symbol} from any source")
        return None

    # Calculate quality metrics
    quality = _calculate_quality_score(
        primary=primary_data,
        secondary=secondary_data,
        warnings=warnings,
    )

    return MultiSourceData(
        symbol=symbol.upper(),
        primary_data=primary_data,
        secondary_data=secondary_data,
        quality=quality,
        sources_used=sources_used,
        fetch_timestamp=datetime.now(),
    )


def _calculate_quality_score(
    primary: SymbolData,
    secondary: Optional[SymbolData],
    warnings: list[str],
) -> DataQualityScore:
    """Calculate data quality score based on source agreement."""

    source_count = 1 if secondary is None else 2
    price_match = True
    price_deviation = 0.0

    # Cross-validate prices if we have both sources
    if secondary is not None:
        price_deviation = abs(
            (primary.current_price - secondary.current_price)
            / primary.current_price * 100
        )
        price_match = price_deviation <= PRICE_TOLERANCE_PERCENT

        if not price_match:
            warnings.append(
                f"Price mismatch: Yahoo Rs.{primary.current_price:.2f} vs "
                f"Angel One Rs.{secondary.current_price:.2f} ({price_deviation:.2f}% diff)"
            )

    # Check volume data
    volume_confirmed = (
        len(primary.ohlcv) > 0
        and primary.ohlcv[-1].volume > 0
    )

    # Determine data freshness
    if len(primary.ohlcv) > 0:
        last_candle_time = primary.ohlcv[-1].timestamp
        age_seconds = (datetime.now(last_candle_time.tzinfo) - last_candle_time).total_seconds()

        if age_seconds < 60:
            data_freshness = "live"
        elif age_seconds < 900:  # 15 minutes
            data_freshness = "delayed"
        else:
            data_freshness = "historical"
    else:
        data_freshness = "unknown"

    # Calculate confidence score
    confidence = _calculate_confidence(
        source_count=source_count,
        price_match=price_match,
        price_deviation=price_deviation,
        volume_confirmed=volume_confirmed,
        data_freshness=data_freshness,
    )

    return DataQualityScore(
        source_count=source_count,
        price_match=price_match,
        price_deviation_percent=round(price_deviation, 4),
        volume_confirmed=volume_confirmed,
        data_freshness=data_freshness,
        confidence=round(confidence, 2),
        warnings=warnings,
    )


def _calculate_confidence(
    source_count: int,
    price_match: bool,
    price_deviation: float,
    volume_confirmed: bool,
    data_freshness: str,
) -> float:
    """
    Calculate overall confidence score (0-1).

    Scoring:
    - Base: 0.5 (single source)
    - +0.25 for second source
    - +0.15 for price match
    - +0.05 for volume data
    - +0.05 for live/recent data
    """
    confidence = 0.5  # Base score for having any data

    # Multi-source bonus
    if source_count >= 2:
        confidence += 0.25

        # Price agreement bonus
        if price_match:
            confidence += 0.15
        else:
            # Penalize based on deviation
            confidence -= min(price_deviation / 10, 0.2)

    # Volume confirmation
    if volume_confirmed:
        confidence += 0.05

    # Freshness bonus
    if data_freshness == "live":
        confidence += 0.05
    elif data_freshness == "delayed":
        confidence += 0.02

    return max(0.0, min(1.0, confidence))


async def get_cross_validated_quote(symbol: str) -> Optional[dict]:
    """
    Get live quote with cross-validation from multiple sources.

    Returns combined quote with confidence metrics.
    """
    quotes = []
    sources = []

    # Try Yahoo Finance (via ticker.info)
    try:
        from app.services.data_ingestion.yahoo_adapter import get_stock_info
        yahoo_info = await get_stock_info(symbol)
        if "error" not in yahoo_info and yahoo_info.get("current_price"):
            quotes.append({
                "source": "Yahoo Finance",
                "price": yahoo_info["current_price"],
                "previous_close": yahoo_info.get("previous_close", 0),
            })
            sources.append("Yahoo Finance")
    except Exception as e:
        logger.debug(f"Yahoo quote failed: {e}")

    # Try Angel One
    try:
        angelone_quote = await get_angelone_quote(symbol)
        if angelone_quote:
            quotes.append({
                "source": "Angel One",
                "price": angelone_quote["ltp"],
                "previous_close": angelone_quote.get("close", 0),
            })
            sources.append("Angel One")
    except Exception as e:
        logger.debug(f"Angel One quote failed: {e}")

    if not quotes:
        return None

    # Use first quote as primary
    primary = quotes[0]

    # Calculate cross-validation metrics
    if len(quotes) >= 2:
        prices = [q["price"] for q in quotes]
        avg_price = sum(prices) / len(prices)
        max_deviation = max(abs(p - avg_price) / avg_price * 100 for p in prices)
        price_match = max_deviation <= PRICE_TOLERANCE_PERCENT
    else:
        avg_price = primary["price"]
        max_deviation = 0
        price_match = True

    return {
        "symbol": symbol.upper(),
        "price": avg_price if len(quotes) > 1 else primary["price"],
        "previous_close": primary["previous_close"],
        "sources": sources,
        "source_count": len(sources),
        "price_match": price_match,
        "max_deviation_percent": round(max_deviation, 4),
        "confidence": 0.95 if (len(sources) >= 2 and price_match) else 0.7,
        "quotes": quotes,
    }


async def validate_data_sources() -> dict:
    """
    Check connectivity to all data sources.

    Returns status dict for each source.
    """
    status = {}

    # Check Yahoo Finance
    try:
        from app.services.data_ingestion.yahoo_adapter import validate_symbol
        yahoo_ok = await validate_symbol("RELIANCE")
        status["yahoo_finance"] = {
            "available": yahoo_ok,
            "message": "Connected" if yahoo_ok else "Failed to fetch test symbol",
        }
    except Exception as e:
        status["yahoo_finance"] = {
            "available": False,
            "message": str(e),
        }

    # Check Angel One
    try:
        angelone_ok = await validate_angelone_connection()
        status["angel_one"] = {
            "available": angelone_ok,
            "message": "Connected" if angelone_ok else "Authentication failed",
        }
    except Exception as e:
        status["angel_one"] = {
            "available": False,
            "message": str(e),
        }

    # Overall status
    status["overall"] = {
        "sources_available": sum(1 for s in status.values() if isinstance(s, dict) and s.get("available", False)),
        "primary_source": "yahoo_finance" if status.get("yahoo_finance", {}).get("available") else "angel_one",
        "recommendation": (
            "Multi-source validation enabled"
            if status.get("yahoo_finance", {}).get("available") and status.get("angel_one", {}).get("available")
            else "Single source mode - reduced confidence"
        ),
    }

    return status
