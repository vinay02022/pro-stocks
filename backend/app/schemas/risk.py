"""
CONTRACT 4: Risk Validation Engine

Input: TradeIdea + PortfolioState + RiskConfig
Output: RiskPlan

This module performs DETERMINISTIC risk checks.
Pure Python logic - NO LLM involvement.
Can REJECT or MODIFY trades that violate risk rules.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================


class ValidationStatus(str, Enum):
    APPROVED = "APPROVED"  # Trade passes all risk checks
    REJECTED = "REJECTED"  # Trade violates risk rules
    MODIFIED = "MODIFIED"  # Trade approved with modifications


class InstrumentType(str, Enum):
    EQUITY = "EQUITY"
    INDEX = "INDEX"
    FUTURES = "FUTURES"
    OPTIONS_CALL = "OPTIONS_CALL"
    OPTIONS_PUT = "OPTIONS_PUT"


# =============================================================================
# INPUT: Portfolio State
# =============================================================================


class Position(BaseModel):
    """Current open position."""

    symbol: str
    exchange: str = "NSE"
    quantity: int
    avg_buy_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    market_value: float
    weight_percent: float = Field(..., description="% of portfolio")
    sector: Optional[str] = None


class PortfolioMetrics(BaseModel):
    """Portfolio-level metrics."""

    total_value: float
    cash_available: float
    invested_amount: float
    unrealized_pnl: float
    realized_pnl_today: float
    exposure_percent: float = Field(..., ge=0, le=100)
    today_trades: int
    today_loss_percent: float
    max_drawdown: float
    current_drawdown: float


class PortfolioState(BaseModel):
    """
    Current state of user's portfolio.
    Sent by: Portfolio Service
    Received by: Risk Engine
    """

    user_id: str
    portfolio_id: str
    positions: list[Position]
    metrics: PortfolioMetrics
    last_updated: datetime


# =============================================================================
# INPUT: Risk Configuration
# =============================================================================


class RiskConfig(BaseModel):
    """
    User's risk management settings.
    These are HARD LIMITS that cannot be overridden.
    """

    # Position Limits
    max_position_percent: float = Field(
        default=5.0,
        ge=1,
        le=25,
        description="Max % of portfolio in single position",
    )
    max_sector_exposure_percent: float = Field(
        default=25.0,
        ge=5,
        le=50,
        description="Max % in single sector",
    )
    max_portfolio_exposure_percent: float = Field(
        default=50.0,
        ge=10,
        le=100,
        description="Max total invested %",
    )
    max_correlated_positions: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max positions in correlated stocks",
    )

    # Loss Limits
    max_daily_loss_percent: float = Field(
        default=2.0,
        ge=0.5,
        le=10,
        description="Max daily loss as % of portfolio",
    )
    max_weekly_loss_percent: float = Field(
        default=5.0,
        ge=1,
        le=20,
    )
    max_drawdown_percent: float = Field(
        default=10.0,
        ge=2,
        le=30,
    )

    # Trade Limits
    max_daily_trades: int = Field(
        default=10,
        ge=1,
        le=50,
    )
    min_risk_reward_ratio: float = Field(
        default=1.5,
        ge=1.0,
        le=5.0,
    )

    # Allowed Strategies
    allowed_timeframes: list[str] = Field(
        default=["INTRADAY", "SWING"],
    )
    allowed_instruments: list[InstrumentType] = Field(
        default=[InstrumentType.EQUITY],
    )


# =============================================================================
# OUTPUT: RiskPlan Components
# =============================================================================


class TakeProfitTarget(BaseModel):
    """Single take profit level."""

    price: float = Field(..., gt=0)
    exit_percent: float = Field(
        ...,
        gt=0,
        le=100,
        description="% of position to exit at this level",
    )
    label: Optional[str] = Field(default=None, description="e.g., 'TP1', 'TP2'")


class TrailingStopConfig(BaseModel):
    """Trailing stop configuration."""

    activation_price: float = Field(
        ...,
        gt=0,
        description="Price at which trailing stop activates",
    )
    trail_percent: float = Field(
        ...,
        gt=0,
        le=20,
        description="Trail distance as % of price",
    )


class ApprovedPlan(BaseModel):
    """
    Risk-approved execution plan.
    Only present if validation_status is APPROVED or MODIFIED.
    """

    position_size: int = Field(..., gt=0, description="Number of shares/lots")
    position_value: float = Field(..., gt=0, description="Total value in INR")
    max_loss_amount: float = Field(..., gt=0, description="Max loss if SL hit")
    max_loss_percent: float = Field(
        ...,
        gt=0,
        le=100,
        description="Max loss as % of portfolio",
    )
    risk_reward_ratio: float = Field(..., gt=0, description="Reward/Risk ratio")
    stop_loss: float = Field(..., gt=0, description="Stop loss price")
    take_profit: list[TakeProfitTarget] = Field(
        ...,
        min_length=1,
        description="Exit targets",
    )
    trailing_stop: Optional[TrailingStopConfig] = None


class PortfolioImpact(BaseModel):
    """How this trade affects portfolio risk."""

    current_exposure_percent: float
    new_exposure_percent: float
    sector_exposure: Optional[dict[str, float]] = Field(
        default=None,
        description="Exposure by sector after trade",
    )
    correlation_warning: Optional[str] = Field(
        default=None,
        description="Warning if correlated with existing positions",
    )
    max_drawdown_if_all_sl_hit: float = Field(
        ...,
        description="Worst case portfolio drawdown",
    )


# =============================================================================
# OUTPUT: RiskPlan (Complete Response)
# =============================================================================


class RiskPlan(BaseModel):
    """
    Risk validation result.
    Returned by: Risk Validation Engine
    Consumed by: Explanation Layer, Frontend

    IMPORTANT: If REJECTED, trade CANNOT proceed.
    Risk rules are non-negotiable.
    """

    trade_id: UUID = Field(..., description="Links to TradeIdea.id")
    validation_status: ValidationStatus
    rejection_reasons: Optional[list[str]] = Field(
        default=None,
        description="Why trade was rejected (if REJECTED)",
    )
    approved_plan: Optional[ApprovedPlan] = Field(
        default=None,
        description="Execution plan (if APPROVED/MODIFIED)",
    )
    portfolio_impact: PortfolioImpact
    risk_warnings: list[str] = Field(
        ...,
        min_length=1,
        description="Mandatory warnings for human trader",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trade_id": "123e4567-e89b-12d3-a456-426614174000",
                "validation_status": "APPROVED",
                "approved_plan": {
                    "position_size": 40,
                    "position_value": 98000,
                    "max_loss_amount": 2800,
                    "max_loss_percent": 1.4,
                    "risk_reward_ratio": 2.5,
                    "stop_loss": 2380,
                    "take_profit": [
                        {"price": 2520, "exit_percent": 50, "label": "TP1"},
                        {"price": 2600, "exit_percent": 50, "label": "TP2"},
                    ],
                },
                "portfolio_impact": {
                    "current_exposure_percent": 35,
                    "new_exposure_percent": 40,
                    "max_drawdown_if_all_sl_hit": 4.2,
                },
                "risk_warnings": [
                    "Position size is at maximum allowed for single stock",
                    "Earnings announcement in 5 days - increased volatility expected",
                ],
            }
        }
