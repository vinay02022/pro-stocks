"""
CONTRACT 2: Indicator Engine

Input: MarketSnapshot (specifically SymbolData with OHLCV)
Output: IndicatorOutput

This module performs ALL mathematical calculations.
Pure Python/NumPy - NO LLM involvement.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.market import MarketSnapshot


# =============================================================================
# ENUMS
# =============================================================================


class TrendDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    SIDEWAYS = "SIDEWAYS"


class VolatilityZone(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class PositionSizingMethod(str, Enum):
    ATR = "ATR"
    PERCENT_RISK = "PERCENT_RISK"
    KELLY = "KELLY"
    FIXED = "FIXED"


# =============================================================================
# INPUT: IndicatorRequest
# =============================================================================


class IndicatorRequest(BaseModel):
    """
    Request for indicator calculation.
    Sent by: API / Strategy Engine
    Received by: Indicator Service

    Note: Can accept full MarketSnapshot or minimal OHLCV data.
    """

    market_snapshot: MarketSnapshot
    symbol: str = Field(..., description="Which symbol to calculate indicators for")
    # Optional: specify which indicators to calculate (default: all)
    calculate_trend: bool = True
    calculate_momentum: bool = True
    calculate_volatility: bool = True
    calculate_volume: bool = True
    calculate_levels: bool = True
    calculate_risk_metrics: bool = True


# =============================================================================
# OUTPUT: Indicator Components
# =============================================================================


class TrendIndicators(BaseModel):
    """Trend-following indicators."""

    ema_9: float
    ema_21: float
    ema_50: float
    ema_200: float
    sma_20: float
    sma_50: float
    sma_200: float
    trend_direction: TrendDirection
    trend_strength: float = Field(..., ge=0, le=100, description="ADX-based strength")
    adx: Optional[float] = None
    plus_di: Optional[float] = None
    minus_di: Optional[float] = None


class MACDData(BaseModel):
    """MACD indicator values."""

    macd_line: float
    signal_line: float
    histogram: float
    crossover: Optional[SignalType] = None


class StochasticData(BaseModel):
    """Stochastic oscillator values."""

    k: float = Field(..., ge=0, le=100)
    d: float = Field(..., ge=0, le=100)
    zone: str = Field(..., description="OVERBOUGHT / OVERSOLD / NEUTRAL")


class MomentumIndicators(BaseModel):
    """Momentum indicators."""

    rsi_14: float = Field(..., ge=0, le=100)
    rsi_divergence: Optional[SignalType] = None
    macd: MACDData
    stochastic: Optional[StochasticData] = None
    cci: Optional[float] = None
    mfi: Optional[float] = Field(default=None, ge=0, le=100)
    williams_r: Optional[float] = Field(default=None, ge=-100, le=0)


class BollingerBandsData(BaseModel):
    """Bollinger Bands values."""

    upper: float
    middle: float
    lower: float
    bandwidth: float = Field(..., ge=0, description="Band width as ratio")
    percent_b: float = Field(..., description="Price position within bands (0-1)")


class VolatilityIndicators(BaseModel):
    """Volatility indicators."""

    atr_14: float = Field(..., ge=0)
    atr_percent: float = Field(..., ge=0, description="ATR as % of price")
    bollinger_bands: BollingerBandsData
    historical_volatility: Optional[float] = None
    implied_volatility: Optional[float] = None


class VolumeProfileLevel(BaseModel):
    """Single level in volume profile."""

    price: float
    volume: int
    is_poc: bool = Field(..., description="Is Point of Control")
    is_value_area: bool


class VolumeIndicators(BaseModel):
    """Volume-based indicators."""

    current_volume: int
    avg_volume_20: int
    volume_ratio: float = Field(..., ge=0, description="Current/Avg ratio")
    vwap: float
    vwap_deviation: float = Field(..., description="% deviation from VWAP")
    obv: Optional[int] = None
    volume_profile: Optional[list[VolumeProfileLevel]] = None


class PivotPoints(BaseModel):
    """Pivot point levels."""

    pivot: float
    r1: float
    r2: float
    r3: float
    s1: float
    s2: float
    s3: float
    type: str = Field(default="standard", description="standard/fibonacci/camarilla")


class SupportResistanceLevel(BaseModel):
    """Detected support/resistance level."""

    price: float
    strength: int = Field(..., ge=1, le=5)
    type: str = Field(..., description="support / resistance")
    touches: int = Field(..., ge=1)


class Levels(BaseModel):
    """Price levels and support/resistance."""

    support: list[float] = Field(..., description="Support levels (nearest first)")
    resistance: list[float] = Field(..., description="Resistance levels (nearest first)")
    pivot_points: PivotPoints
    key_levels: Optional[list[SupportResistanceLevel]] = None
    day_high: float
    day_low: float
    week_high: Optional[float] = None
    week_low: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None


class PositionSizing(BaseModel):
    """Position sizing recommendation."""

    recommended_shares: int = Field(..., ge=0)
    recommended_value: float = Field(..., ge=0)
    risk_amount: float = Field(..., ge=0, description="Amount at risk in INR")
    risk_percent: float = Field(..., ge=0, le=100)
    kelly_percent: Optional[float] = Field(default=None, ge=0, le=100)
    method: PositionSizingMethod


class RiskMetrics(BaseModel):
    """Risk-based calculations."""

    atr: float = Field(..., ge=0)
    atr_percent: float = Field(..., ge=0)
    suggested_sl: float = Field(..., gt=0, description="Stop loss price")
    suggested_sl_percent: float = Field(..., ge=0)
    suggested_tp: list[float] = Field(..., description="Take profit targets")
    risk_reward_ratios: list[float] = Field(..., description="R:R for each TP")
    position_sizing: PositionSizing
    volatility_zone: VolatilityZone


class IndicatorSignal(BaseModel):
    """Signal generated by an indicator."""

    indicator: str
    signal: SignalType
    strength: float = Field(..., ge=0, le=100)
    description: str


class PriceData(BaseModel):
    """Current price information."""

    current: float
    open: float
    high: float
    low: float
    previous_close: float
    change: float
    change_percent: float
    volume: int
    avg_volume: Optional[int] = None


# =============================================================================
# OUTPUT: IndicatorOutput (Complete Response)
# =============================================================================


class IndicatorOutput(BaseModel):
    """
    Complete indicator analysis for a symbol.
    Returned by: Indicator Service
    Consumed by: LLM Reasoning Layer, Risk Engine
    """

    symbol: str
    timestamp: datetime
    price: PriceData

    indicators: dict = Field(
        ...,
        description="Contains trend, momentum, volatility, volume sub-objects",
    )
    # Structured as:
    # {
    #   "trend": TrendIndicators,
    #   "momentum": MomentumIndicators,
    #   "volatility": VolatilityIndicators,
    #   "volume": VolumeIndicators
    # }

    levels: Levels
    risk_metrics: RiskMetrics
    signals: Optional[list[IndicatorSignal]] = Field(
        default=None,
        description="Summary signals from indicators",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "RELIANCE",
                "timestamp": "2024-02-04T10:30:00+05:30",
                "price": {
                    "current": 2450.50,
                    "open": 2440.00,
                    "high": 2465.00,
                    "low": 2435.00,
                    "previous_close": 2420.00,
                    "change": 30.50,
                    "change_percent": 1.26,
                    "volume": 5000000,
                },
                "indicators": {
                    "trend": {"ema_9": 2448.0, "trend_direction": "BULLISH"},
                    "momentum": {"rsi_14": 62.5},
                    "volatility": {"atr_14": 45.2, "atr_percent": 1.85},
                    "volume": {"vwap": 2452.30, "volume_ratio": 1.2},
                },
                "levels": {
                    "support": [2420, 2380],
                    "resistance": [2480, 2520],
                },
                "risk_metrics": {
                    "suggested_sl": 2405.0,
                    "suggested_tp": [2500, 2550],
                    "risk_reward_ratios": [1.1, 2.2],
                },
            }
        }
