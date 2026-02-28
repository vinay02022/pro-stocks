"""
CONTRACT 1: Data Ingestion Layer

Input: DataRequest
Output: MarketSnapshot

This module fetches raw market data from external APIs (Groww, Angel One, News)
and normalizes it into a standard format.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"


class Timeframe(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


class DataType(str, Enum):
    OHLCV = "OHLCV"
    OPTIONS_CHAIN = "OPTIONS_CHAIN"
    NEWS = "NEWS"
    FUNDAMENTALS = "FUNDAMENTALS"


class MarketPhase(str, Enum):
    PRE_OPEN = "pre_open"
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"


class NewsSentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


# =============================================================================
# INPUT: DataRequest
# =============================================================================


class DataRequest(BaseModel):
    """
    Request for market data.
    Sent by: Frontend / Strategy Engine
    Received by: Data Ingestion Service
    """

    symbols: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of symbols to fetch (e.g., ['RELIANCE', 'NIFTY'])",
    )
    data_types: list[DataType] = Field(
        default=[DataType.OHLCV],
        description="Types of data to fetch",
    )
    timeframe: Timeframe = Field(
        default=Timeframe.M15,
        description="Candle timeframe",
    )
    lookback: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Number of candles to fetch",
    )
    include_options: bool = Field(
        default=False,
        description="Include options chain data",
    )
    include_news: bool = Field(
        default=False,
        description="Include related news",
    )
    options_expiry: Optional[str] = Field(
        default=None,
        description="Specific expiry date for options (YYYY-MM-DD)",
    )


# =============================================================================
# OUTPUT: MarketSnapshot Components
# =============================================================================


class OHLCV(BaseModel):
    """Single candlestick data point."""

    timestamp: datetime
    open: float = Field(..., gt=0)
    high: float = Field(..., gt=0)
    low: float = Field(..., gt=0)
    close: float = Field(..., gt=0)
    volume: int = Field(..., ge=0)


class SymbolData(BaseModel):
    """Complete data for a single symbol."""

    symbol: str
    exchange: Exchange = Exchange.NSE
    timeframe: Timeframe
    ohlcv: list[OHLCV]
    current_price: float = Field(..., gt=0)
    day_change_percent: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_qty: Optional[int] = None
    ask_qty: Optional[int] = None


class OptionLeg(BaseModel):
    """Single option contract data."""

    ltp: float = Field(..., ge=0, description="Last traded price")
    oi: int = Field(..., ge=0, description="Open interest")
    oi_change: int = Field(..., description="Change in OI")
    volume: int = Field(..., ge=0)
    iv: float = Field(..., ge=0, description="Implied volatility %")
    delta: Optional[float] = Field(default=None, ge=-1, le=1)
    gamma: Optional[float] = Field(default=None, ge=0)
    theta: Optional[float] = None
    vega: Optional[float] = Field(default=None, ge=0)


class StrikeData(BaseModel):
    """Option data for a single strike price."""

    strike: float = Field(..., gt=0)
    call: Optional[OptionLeg] = None
    put: Optional[OptionLeg] = None


class OptionsChainData(BaseModel):
    """Complete options chain for an underlying."""

    underlying: str
    spot_price: float = Field(..., gt=0)
    expiry_dates: list[str]
    selected_expiry: str
    strikes: list[StrikeData]
    atm_strike: float = Field(..., gt=0)
    pcr: float = Field(..., ge=0, description="Put-Call Ratio")
    max_pain_strike: Optional[float] = None


class NewsItem(BaseModel):
    """Single news item."""

    id: Optional[str] = None
    headline: str
    summary: Optional[str] = None
    source: str
    url: Optional[str] = None
    timestamp: datetime
    sentiment: NewsSentiment
    relevance_score: float = Field(..., ge=0, le=1)
    symbols: Optional[list[str]] = None


class MarketMetadata(BaseModel):
    """Metadata about the data fetch."""

    source: str = Field(..., description="Data source(s) used")
    latency_ms: int = Field(..., ge=0)
    is_market_open: bool
    market_phase: MarketPhase
    next_market_open: Optional[datetime] = None
    last_updated: datetime


# =============================================================================
# OUTPUT: MarketSnapshot (Complete Response)
# =============================================================================


class MarketSnapshot(BaseModel):
    """
    Complete market data snapshot.
    Returned by: Data Ingestion Service
    Consumed by: Indicator Engine, LLM Reasoning
    """

    timestamp: datetime
    symbols: list[SymbolData]
    options_chain: Optional[OptionsChainData] = None
    news: Optional[list[NewsItem]] = None
    metadata: MarketMetadata

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2024-02-04T10:30:00+05:30",
                "symbols": [
                    {
                        "symbol": "RELIANCE",
                        "exchange": "NSE",
                        "timeframe": "15m",
                        "ohlcv": [],
                        "current_price": 2450.50,
                        "day_change_percent": 1.25,
                    }
                ],
                "metadata": {
                    "source": "Groww, AngelOne",
                    "latency_ms": 245,
                    "is_market_open": True,
                    "market_phase": "open",
                    "last_updated": "2024-02-04T10:30:00+05:30",
                },
            }
        }
