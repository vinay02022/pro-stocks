"""
Strategy Evaluation Service Implementation

Orchestrates the complete trade suggestion pipeline:
    Data Ingestion → Indicators → Reasoning LLM → Risk Engine → Explanation LLM

This is the main entry point for generating trade suggestions.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from app.schemas.market import DataRequest, Timeframe
from app.schemas.risk import RiskConfig, PortfolioState, PortfolioMetrics, Position
from app.schemas.explanation import TradeSuggestionResponse, ValidatedTrade
from app.schemas.trade import MarketContext
from app.services.strategy.interface import StrategyServiceInterface, StrategyRequest
from app.services.data_ingestion import get_data_ingestion_service
from app.services.indicators import get_indicator_service
from app.services.risk import get_risk_service, RiskValidationInput
from app.services.llm import (
    get_reasoning_service,
    get_explanation_service,
    ReasoningInput,
)

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


def _get_default_portfolio_state() -> PortfolioState:
    """Get default portfolio state for users without configured portfolios."""
    from datetime import datetime
    return PortfolioState(
        user_id="default",
        portfolio_id="default",
        positions=[],  # No existing positions
        metrics=PortfolioMetrics(
            total_value=1_000_000.0,  # Default 10L portfolio
            cash_available=1_000_000.0,  # Full cash available
            invested_amount=0.0,  # No investments yet
            unrealized_pnl=0.0,
            realized_pnl_today=0.0,
            exposure_percent=0.0,  # 0% exposure (consistent with no positions)
            today_trades=0,
            today_loss_percent=0.0,
            max_drawdown=0.0,
            current_drawdown=0.0,
        ),
        last_updated=datetime.now(IST),
    )


def _get_default_risk_config() -> RiskConfig:
    """Get default risk configuration."""
    from app.core.config import settings

    return RiskConfig(
        max_position_percent=settings.default_max_position_percent,
        max_daily_loss_percent=settings.default_max_daily_loss_percent,
        max_daily_trades=settings.default_max_daily_trades,
        min_risk_reward_ratio=settings.default_min_risk_reward,
        max_portfolio_exposure_percent=50.0,
        max_drawdown_percent=10.0,
        allowed_timeframes=["INTRADAY", "SWING", "POSITIONAL"],  # Trade timeframes, not data timeframes
    )


class StrategyService(StrategyServiceInterface):
    """
    Strategy Evaluation Service.

    Orchestrates the complete trade suggestion pipeline.
    Handles errors at each stage with graceful degradation.
    """

    def __init__(self):
        self._data_service = None
        self._indicator_service = None
        self._risk_service = None
        self._reasoning_service = None
        self._explanation_service = None

    @property
    def data_service(self):
        """Lazy load data ingestion service."""
        if self._data_service is None:
            self._data_service = get_data_ingestion_service()
        return self._data_service

    @property
    def indicator_service(self):
        """Lazy load indicator service."""
        if self._indicator_service is None:
            self._indicator_service = get_indicator_service()
        return self._indicator_service

    @property
    def risk_service(self):
        """Lazy load risk service."""
        if self._risk_service is None:
            self._risk_service = get_risk_service()
        return self._risk_service

    @property
    def reasoning_service(self):
        """Lazy load reasoning service."""
        if self._reasoning_service is None:
            self._reasoning_service = get_reasoning_service()
        return self._reasoning_service

    @property
    def explanation_service(self):
        """Lazy load explanation service."""
        if self._explanation_service is None:
            self._explanation_service = get_explanation_service()
        return self._explanation_service

    @property
    def name(self) -> str:
        return "StrategyService"

    async def execute(self, input_data: StrategyRequest) -> TradeSuggestionResponse:
        """
        Run the complete trade suggestion pipeline.

        Pipeline:
            1. Data Ingestion → MarketSnapshot
            2. Indicator Engine → IndicatorOutput
            3. Reasoning LLM → TradeIdea
            4. Risk Engine → RiskPlan
            5. Explanation LLM → TradeExplanation
        """
        now = datetime.now(IST)
        symbol = input_data.symbol.upper()
        timeframe = input_data.timeframe
        portfolio = input_data.portfolio_state or _get_default_portfolio_state()
        risk_config = input_data.risk_config or _get_default_risk_config()

        logger.info(f"Starting strategy pipeline for {symbol} ({timeframe.value})")

        # =================================================================
        # STAGE 1: Data Ingestion
        # =================================================================
        logger.info("Stage 1: Data Ingestion")
        data_request = DataRequest(
            symbols=[symbol],
            timeframe=timeframe,
            lookback=100,  # Need sufficient data for indicators
        )
        data_result = await self.data_service.execute(data_request)

        if not data_result.snapshot.symbols:
            raise ValueError(f"No data available for {symbol}")

        symbol_data = data_result.snapshot.symbols[0]
        logger.info(f"Stage 1 complete: Got {len(symbol_data.ohlcv)} candles")

        # =================================================================
        # STAGE 2: Indicator Engine
        # =================================================================
        logger.info("Stage 2: Indicator Calculation")
        indicator_output = await self.indicator_service.calculate_for_symbol(
            symbol_data,
            portfolio_value=portfolio.metrics.total_value,
            risk_percent=1.0,  # Default 1% risk per trade
        )
        logger.info(f"Stage 2 complete: Price={indicator_output.price.current}")

        # =================================================================
        # STAGE 3: Reasoning LLM → TradeIdea
        # =================================================================
        logger.info("Stage 3: Reasoning (LLM)")
        market_context = None
        if input_data.include_news:
            # TODO: Fetch news context
            market_context = MarketContext(
                global_sentiment="Market sentiment not available",
            )

        reasoning_input = ReasoningInput(
            indicator_output=indicator_output,
            market_context=market_context,
        )
        trade_idea = await self.reasoning_service.execute(reasoning_input)
        logger.info(f"Stage 3 complete: Direction={trade_idea.direction.value}")

        # =================================================================
        # STAGE 4: Risk Validation Engine → RiskPlan
        # =================================================================
        logger.info("Stage 4: Risk Validation")
        risk_input = RiskValidationInput(
            trade_idea=trade_idea,
            portfolio_state=portfolio,
            risk_config=risk_config,
        )
        risk_plan = await self.risk_service.execute(risk_input)
        logger.info(f"Stage 4 complete: Status={risk_plan.validation_status.value}")

        # =================================================================
        # STAGE 5: Explanation LLM → TradeExplanation
        # =================================================================
        logger.info("Stage 5: Explanation Generation (LLM)")
        validated_trade = ValidatedTrade(idea=trade_idea, risk_plan=risk_plan)
        explanation = await self.explanation_service.execute(validated_trade)
        logger.info("Stage 5 complete: Explanation generated")

        # =================================================================
        # Build Final Response
        # =================================================================
        # Determine expiration
        if trade_idea.timeframe.value == "INTRADAY":
            expires_at = now.replace(hour=15, minute=30, second=0, microsecond=0)
            if expires_at < now:
                expires_at = expires_at + timedelta(days=1)
        else:
            expires_at = now + timedelta(days=3)

        response = TradeSuggestionResponse(
            idea=trade_idea,
            risk_plan=risk_plan,
            explanation=explanation,
            generated_at=now,
            expires_at=expires_at,
        )

        logger.info(f"Pipeline complete for {symbol}")
        return response

    async def health_check(self) -> bool:
        """Check health of all dependent services."""
        try:
            # Check core services (required)
            data_healthy = await self.data_service.health_check()
            indicator_healthy = await self.indicator_service.health_check()
            risk_healthy = await self.risk_service.health_check()

            if not all([data_healthy, indicator_healthy, risk_healthy]):
                return False

            # Check LLM services (optional - can fallback)
            # Don't fail health check if LLM is unavailable
            reasoning_healthy = await self.reasoning_service.health_check()
            explanation_healthy = await self.explanation_service.health_check()

            if not reasoning_healthy or not explanation_healthy:
                logger.warning("LLM services unavailable - will use fallback")

            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Singleton instance
_service_instance: Optional[StrategyService] = None


def get_strategy_service() -> StrategyService:
    """Get or create strategy service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = StrategyService()
    return _service_instance
