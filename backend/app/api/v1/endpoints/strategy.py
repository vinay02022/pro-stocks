"""
Strategy API Endpoints

Main endpoints for trade suggestions.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.market import Timeframe
from app.schemas.risk import RiskConfig, PortfolioState, PortfolioMetrics
from app.schemas.explanation import TradeSuggestionResponse
from app.services.strategy import get_strategy_service, StrategyRequest

IST = ZoneInfo("Asia/Kolkata")

router = APIRouter()


class AnalyzeRequest(BaseModel):
    """Request body for strategy analysis."""

    symbol: str = Field(..., description="Symbol to analyze (e.g., RELIANCE)")
    timeframe: Timeframe = Field(default=Timeframe.M15)
    portfolio_value: Optional[float] = Field(
        default=None,
        description="Portfolio value for position sizing (default: 10L)",
    )
    cash_available: Optional[float] = Field(
        default=None,
        description="Cash available in portfolio",
    )
    risk_percent: float = Field(
        default=1.0,
        ge=0.5,
        le=5.0,
        description="% of portfolio to risk per trade",
    )
    max_position_percent: float = Field(
        default=5.0,
        ge=1.0,
        le=20.0,
        description="Max position size as % of portfolio",
    )
    include_news: bool = Field(default=False)
    include_options: bool = Field(default=False)


@router.post("/analyze", response_model=TradeSuggestionResponse)
async def analyze_symbol(request: AnalyzeRequest):
    """
    Analyze a symbol and generate trade suggestion.

    This runs the FULL pipeline:
    1. Fetch market data
    2. Calculate indicators
    3. Generate trade idea (LLM)
    4. Validate against risk rules
    5. Generate explanation (LLM)

    Returns complete trade suggestion with:
    - Trade idea (direction, confidence, reasoning)
    - Risk plan (position size, SL/TP, warnings)
    - Human-readable explanation
    """
    strategy_service = get_strategy_service()

    # Build portfolio state
    # Default: Full cash available (no existing positions)
    portfolio_value = request.portfolio_value or 1_000_000.0
    cash = request.cash_available or portfolio_value  # Full cash by default
    invested = portfolio_value - cash

    portfolio_state = PortfolioState(
        user_id="api_user",
        portfolio_id="default",
        positions=[],  # No existing positions
        metrics=PortfolioMetrics(
            total_value=portfolio_value,
            cash_available=cash,
            invested_amount=invested,
            unrealized_pnl=0.0,
            realized_pnl_today=0.0,
            exposure_percent=0.0,  # No existing exposure
            today_trades=0,
            today_loss_percent=0.0,
            max_drawdown=0.0,
            current_drawdown=0.0,
        ),
        last_updated=datetime.now(IST),
    )

    # Build risk config
    risk_config = RiskConfig(
        max_position_percent=request.max_position_percent,
        max_daily_loss_percent=2.0,
        max_daily_trades=10,
        min_risk_reward_ratio=1.5,
        max_portfolio_exposure_percent=50.0,
        max_drawdown_percent=10.0,
        allowed_timeframes=["INTRADAY", "SWING", "POSITIONAL"],  # Trade timeframes
    )

    # Build strategy request
    strategy_request = StrategyRequest(
        symbol=request.symbol,
        timeframe=request.timeframe,
        portfolio_state=portfolio_state,
        risk_config=risk_config,
        include_news=request.include_news,
        include_options=request.include_options,
    )

    try:
        response = await strategy_service.execute(strategy_request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/health")
async def strategy_health():
    """Check health of the strategy pipeline."""
    strategy_service = get_strategy_service()
    healthy = await strategy_service.health_check()
    return {"healthy": healthy}


@router.get("/ideas")
async def list_recent_ideas(
    limit: int = 10,
    status: Optional[str] = None,
):
    """
    List recent trade ideas.

    Filter by status: PENDING, APPROVED, REJECTED, EXECUTED, EXPIRED

    Note: Requires database implementation.
    """
    # TODO: Implement with database persistence
    return {
        "message": "Trade idea persistence not yet implemented",
        "ideas": [],
    }


@router.get("/ideas/{idea_id}")
async def get_idea(idea_id: str):
    """
    Get a specific trade idea by ID.

    Note: Requires database implementation.
    """
    # TODO: Implement with database
    raise HTTPException(
        status_code=501,
        detail="Trade idea persistence not yet implemented",
    )


@router.post("/ideas/{idea_id}/execute")
async def mark_executed(idea_id: str):
    """
    Mark a trade idea as executed by the user.

    This is for tracking purposes only - actual execution
    happens on the broker platform by the human.

    Note: Requires database implementation.
    """
    # TODO: Implement with database
    raise HTTPException(
        status_code=501,
        detail="Trade idea persistence not yet implemented",
    )


@router.post("/ideas/{idea_id}/skip")
async def mark_skipped(idea_id: str, reason: Optional[str] = None):
    """
    Mark a trade idea as skipped.

    Optionally include reason for feedback/learning.

    Note: Requires database implementation.
    """
    # TODO: Implement with database
    raise HTTPException(
        status_code=501,
        detail="Trade idea persistence not yet implemented",
    )


@router.get("/recommendations")
async def get_recommendations(
    count: int = 5,
    timeframe: Timeframe = Timeframe.D1,
):
    """
    Get AI-recommended stocks.

    Scans popular stocks and returns top recommendations
    with APPROVED status (passed risk validation).

    Returns list of trade suggestions sorted by confidence.
    """
    from app.services.data_ingestion.stock_list import get_popular_stocks
    from app.schemas.risk import ValidationStatus
    import asyncio
    import logging

    logger = logging.getLogger(__name__)
    strategy_service = get_strategy_service()

    # Get popular stocks to analyze
    popular = get_popular_stocks(15)  # Analyze more to find approved ones

    recommendations = []

    for stock in popular:
        try:
            # Quick analysis for each stock
            portfolio_state = PortfolioState(
                user_id="scanner",
                portfolio_id="default",
                positions=[],
                metrics=PortfolioMetrics(
                    total_value=1_000_000.0,
                    cash_available=1_000_000.0,
                    invested_amount=0.0,
                    unrealized_pnl=0.0,
                    realized_pnl_today=0.0,
                    exposure_percent=0.0,
                    today_trades=0,
                    today_loss_percent=0.0,
                    max_drawdown=0.0,
                    current_drawdown=0.0,
                ),
                last_updated=datetime.now(IST),
            )

            risk_config = RiskConfig(
                max_position_percent=5.0,
                max_daily_loss_percent=2.0,
                max_daily_trades=10,
                min_risk_reward_ratio=1.5,
                max_portfolio_exposure_percent=50.0,
                max_drawdown_percent=10.0,
                allowed_timeframes=["INTRADAY", "SWING", "POSITIONAL"],
            )

            strategy_request = StrategyRequest(
                symbol=stock["symbol"],
                timeframe=timeframe,
                portfolio_state=portfolio_state,
                risk_config=risk_config,
            )

            response = await strategy_service.execute(strategy_request)

            # Add to recommendations
            recommendations.append({
                "symbol": stock["symbol"],
                "name": stock["name"],
                "sector": stock["sector"],
                "direction": response.idea.direction.value,
                "confidence": response.idea.confidence_band.mid,
                "status": response.risk_plan.validation_status.value,
                "entry_price": response.idea.suggested_entry.entry_price,
                "stop_loss": response.risk_plan.approved_plan.stop_loss if response.risk_plan.approved_plan else None,
                "reasoning": response.idea.reasoning.primary_factors[:2],  # Top 2 reasons
                "concerns": response.idea.reasoning.concerns[:1],  # Top concern
            })

        except Exception as e:
            logger.warning(f"Failed to analyze {stock['symbol']}: {e}")
            continue

        # Limit to requested count of approved ones
        approved = [r for r in recommendations if r["status"] == "APPROVED"]
        if len(approved) >= count:
            break

    # Sort by confidence (highest first)
    recommendations.sort(key=lambda x: x["confidence"], reverse=True)

    # Separate approved and rejected
    approved = [r for r in recommendations if r["status"] == "APPROVED"]
    rejected = [r for r in recommendations if r["status"] == "REJECTED"]

    return {
        "timestamp": datetime.now(IST).isoformat(),
        "timeframe": timeframe.value,
        "approved": approved[:count],
        "rejected": rejected[:3],  # Show a few rejected for comparison
        "total_scanned": len(recommendations),
    }
