"""
CONTRACT 3: LLM Reasoning Layer

Input: IndicatorOutput + MarketContext
Output: TradeIdea

This module uses LLM (GPT-5/Opus) for:
- Market regime detection
- Trade suitability analysis
- Strategy selection
- Confluence analysis

CRITICAL: LLM does NO math. All numbers come from Indicator Engine.
LLM only provides reasoning and interpretation.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ENUMS
# =============================================================================


class TradeDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"  # No clear edge


class TradeTimeframe(str, Enum):
    INTRADAY = "INTRADAY"  # Same day exit
    SWING = "SWING"  # 2-10 days
    POSITIONAL = "POSITIONAL"  # Weeks to months


class TrendType(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    SIDEWAYS = "SIDEWAYS"


class VolatilityLevel(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class MomentumLevel(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    DIVERGING = "DIVERGING"  # Price/indicator divergence


class EntryType(str, Enum):
    MARKET = "MARKET"  # Enter at current price
    LIMIT = "LIMIT"  # Enter at specific price
    STOP_LIMIT = "STOP_LIMIT"  # Enter on breakout


class IdeaStatus(str, Enum):
    PENDING = "PENDING"  # Awaiting risk validation
    APPROVED = "APPROVED"  # Risk approved
    REJECTED = "REJECTED"  # Risk rejected
    EXECUTED = "EXECUTED"  # Human took the trade
    EXPIRED = "EXPIRED"  # Opportunity passed
    CANCELLED = "CANCELLED"  # User cancelled


# =============================================================================
# INPUT: Context for LLM
# =============================================================================


class MarketContext(BaseModel):
    """
    Additional context provided to LLM beyond indicators.
    """

    global_sentiment: Optional[str] = Field(
        default=None,
        description="Overall market sentiment (from news/indices)",
    )
    sector_sentiment: Optional[str] = None
    recent_news_summary: Optional[str] = None
    earnings_nearby: bool = False
    major_event_nearby: bool = False
    event_description: Optional[str] = None


# =============================================================================
# OUTPUT: TradeIdea Components
# =============================================================================


class ConfidenceBand(BaseModel):
    """
    Probability range for trade success.

    CRITICAL: This is a RANGE, not a point estimate.
    Never claim certainty. These reflect historical win rates of similar setups.
    """

    low: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Conservative probability estimate",
    )
    mid: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Base case probability",
    )
    high: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Optimistic probability estimate",
    )

    @field_validator("mid")
    @classmethod
    def mid_must_be_between(cls, v, info):
        low = info.data.get("low", 0)
        if v < low:
            raise ValueError("mid must be >= low")
        return v

    @field_validator("high")
    @classmethod
    def high_must_be_highest(cls, v, info):
        mid = info.data.get("mid", 0)
        if v < mid:
            raise ValueError("high must be >= mid")
        return v


class MarketRegime(BaseModel):
    """Current market regime assessment."""

    trend: TrendType
    volatility: VolatilityLevel
    momentum: MomentumLevel


class TradeReasoning(BaseModel):
    """
    Reasoning behind the trade idea.
    Must include concerns - no trade is certain.
    """

    primary_factors: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Main reasons supporting this trade",
    )
    confluences: list[str] = Field(
        default=[],
        max_length=5,
        description="Additional supporting factors",
    )
    concerns: list[str] = Field(
        ...,
        min_length=1,  # MUST always have concerns
        max_length=5,
        description="Factors that could invalidate the thesis",
    )


class EntryZone(BaseModel):
    """Price zone for entry."""

    low: float = Field(..., gt=0)
    high: float = Field(..., gt=0)

    @field_validator("high")
    @classmethod
    def high_must_be_above_low(cls, v, info):
        low = info.data.get("low", 0)
        if v < low:
            raise ValueError("high must be >= low")
        return v


class EntryPlan(BaseModel):
    """How to enter the trade."""

    entry_type: EntryType
    entry_price: Optional[float] = Field(
        default=None,
        gt=0,
        description="Specific price for LIMIT orders",
    )
    entry_zone: Optional[EntryZone] = Field(
        default=None,
        description="Price zone for flexible entry",
    )
    trigger_condition: Optional[str] = Field(
        default=None,
        description="Condition that must be met before entry",
    )


# =============================================================================
# OUTPUT: TradeIdea (Complete Response)
# =============================================================================


class TradeIdea(BaseModel):
    """
    AI-generated trade suggestion.
    Returned by: LLM Reasoning Layer
    Consumed by: Risk Validation Engine

    IMPORTANT: This is a SUGGESTION, not a recommendation.
    Human always makes final decision.
    """

    id: UUID = Field(..., description="Unique identifier")
    timestamp: datetime = Field(..., description="When idea was generated")
    symbol: str
    exchange: str = "NSE"
    direction: TradeDirection
    confidence_band: ConfidenceBand
    timeframe: TradeTimeframe
    regime: MarketRegime
    reasoning: TradeReasoning
    suggested_entry: EntryPlan
    invalidation: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Clear condition that would invalidate this thesis",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="When this idea becomes stale",
    )
    status: IdeaStatus = IdeaStatus.PENDING

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2024-02-04T10:30:00+05:30",
                "symbol": "RELIANCE",
                "direction": "LONG",
                "confidence_band": {"low": 0.55, "mid": 0.65, "high": 0.72},
                "timeframe": "SWING",
                "regime": {
                    "trend": "BULLISH",
                    "volatility": "NORMAL",
                    "momentum": "MODERATE",
                },
                "reasoning": {
                    "primary_factors": [
                        "Price above all major EMAs",
                        "RSI showing bullish momentum without overbought",
                    ],
                    "confluences": [
                        "Sector showing strength",
                        "Volume confirming move",
                    ],
                    "concerns": [
                        "Near resistance at 2500",
                        "Broader market showing weakness",
                    ],
                },
                "suggested_entry": {
                    "entry_type": "LIMIT",
                    "entry_price": 2440.0,
                },
                "invalidation": "Close below 2380 would invalidate bullish thesis",
            }
        }
