"""
CONTRACT 5: Explanation Layer

Input: TradeIdea + RiskPlan (ValidatedTrade)
Output: TradeExplanation

This module uses a CHEAPER LLM (Haiku/GPT-3.5) to generate:
- Human-readable summaries
- Risk disclosures
- "What could go wrong" scenarios
- Human verification checklist

This is the final output shown to the user.
"""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.trade import TradeIdea
from app.schemas.risk import RiskPlan


# =============================================================================
# INPUT: ValidatedTrade
# =============================================================================


class ValidatedTrade(BaseModel):
    """
    Combined input for explanation generation.
    Contains both the trade idea and its risk validation.
    """

    idea: TradeIdea
    risk_plan: RiskPlan


# =============================================================================
# OUTPUT: Explanation Components
# =============================================================================


class AlternativeScenario(BaseModel):
    """
    Alternative outcome scenario.
    Must always present what could go wrong.
    """

    scenario: str = Field(
        ...,
        min_length=10,
        description="Description of the scenario",
    )
    probability: str = Field(
        ...,
        description="Rough probability (e.g., '30%', 'Low', 'Moderate')",
    )
    outcome: str = Field(
        ...,
        description="What happens in this scenario",
    )
    action: str = Field(
        ...,
        description="What to do if this happens",
    )


# =============================================================================
# OUTPUT: TradeExplanation (Final Output)
# =============================================================================


class TradeExplanation(BaseModel):
    """
    Human-readable explanation of the trade suggestion.
    Returned by: Explanation Layer
    Consumed by: Frontend (shown to user)

    CRITICAL: Must include risk disclosure and uncertainty.
    Never present as guaranteed or certain.
    """

    trade_id: UUID = Field(..., description="Links to TradeIdea.id")
    timestamp: datetime

    # Summary (1-2 sentences)
    summary: str = Field(
        ...,
        min_length=20,
        max_length=200,
        description="Brief summary of the trade suggestion",
    )

    # Detailed rationale
    rationale: str = Field(
        ...,
        min_length=100,
        max_length=2000,
        description="Detailed reasoning in plain English",
    )

    # Mandatory risk disclosure
    risk_disclosure: str = Field(
        ...,
        min_length=50,
        max_length=500,
        description="Mandatory risk warning",
    )

    # What could go wrong (ALWAYS required)
    what_could_go_wrong: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Things that could invalidate this trade",
    )

    # Alternative scenarios
    alternative_scenarios: list[AlternativeScenario] = Field(
        ...,
        min_length=1,
        max_length=3,
        description="Other possible outcomes",
    )

    # Confidence statement (probabilistic, not certain)
    confidence_statement: str = Field(
        ...,
        min_length=30,
        max_length=300,
        description="Probabilistic confidence statement",
    )

    # Checklist for human verification
    human_checklist: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Things for human to verify before executing",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trade_id": "123e4567-e89b-12d3-a456-426614174000",
                "timestamp": "2024-02-04T10:35:00+05:30",
                "summary": "RELIANCE shows bullish momentum with price above key moving averages. Consider a swing long position with defined risk.",
                "rationale": "The stock has been consolidating above the 21 EMA and recently broke out of a 3-day range with above-average volume. RSI at 62 shows momentum without being overbought. The broader sector (Oil & Gas) is showing relative strength against Nifty. However, there is resistance at 2500 which has been tested twice before.",
                "risk_disclosure": "This is a SUGGESTION based on technical analysis, not financial advice. Past patterns do not guarantee future results. You could lose the entire amount risked (₹2,800 or 1.4% of portfolio) if the stop loss is hit. Only trade with money you can afford to lose.",
                "what_could_go_wrong": [
                    "Broader market selloff could drag the stock down regardless of technicals",
                    "Resistance at 2500 may hold, causing a reversal",
                    "Unexpected negative news about the company",
                    "Global crude oil price volatility affecting sentiment",
                ],
                "alternative_scenarios": [
                    {
                        "scenario": "Price reverses at 2500 resistance",
                        "probability": "35%",
                        "outcome": "Trade hits stop loss at 2380",
                        "action": "Accept the loss, do not average down",
                    },
                    {
                        "scenario": "Sideways consolidation",
                        "probability": "25%",
                        "outcome": "Price stays between 2420-2500 for several days",
                        "action": "Consider trailing stop or time-based exit after 5 days",
                    },
                ],
                "confidence_statement": "Based on backtesting similar setups (price above EMAs + RSI 55-70 + volume confirmation), approximately 62% have reached the first target within the specified timeframe. This is a probability, not a guarantee.",
                "human_checklist": [
                    "Check if any company announcements are expected this week",
                    "Verify current price is still in the entry zone",
                    "Confirm you have sufficient capital for this position",
                    "Ensure this trade doesn't exceed your sector concentration limits",
                    "Set the stop loss order immediately after entry",
                ],
            }
        }


# =============================================================================
# COMPLETE API RESPONSE
# =============================================================================


class TradeSuggestionResponse(BaseModel):
    """
    Complete response sent to frontend.
    Contains everything the user needs to make a decision.
    """

    idea: TradeIdea
    risk_plan: RiskPlan
    explanation: TradeExplanation

    # Metadata
    generated_at: datetime
    expires_at: datetime
    version: str = "1.0"
