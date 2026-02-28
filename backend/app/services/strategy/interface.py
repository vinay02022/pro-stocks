"""
Strategy Evaluation Service Interface

Orchestrates the complete trade suggestion pipeline.
"""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.services.base import BaseService
from app.schemas.market import Timeframe
from app.schemas.risk import RiskConfig, PortfolioState
from app.schemas.explanation import TradeSuggestionResponse


@dataclass
class StrategyRequest:
    """Request for trade suggestion."""

    symbol: str
    timeframe: Timeframe = Timeframe.M15
    portfolio_state: Optional[PortfolioState] = None
    risk_config: Optional[RiskConfig] = None
    include_news: bool = False
    include_options: bool = False


class StrategyServiceInterface(BaseService[StrategyRequest, TradeSuggestionResponse]):
    """
    Strategy Evaluation Service Contract.

    This is the MAIN ORCHESTRATOR that runs the full pipeline.

    INPUT: StrategyRequest
        - symbol: Stock to analyze
        - timeframe: Analysis timeframe
        - portfolio_state: Current portfolio (for risk validation)
        - risk_config: User's risk rules

    OUTPUT: TradeSuggestionResponse
        - idea: TradeIdea from Reasoning LLM
        - risk_plan: RiskPlan from Risk Engine
        - explanation: TradeExplanation from Explanation LLM

    PIPELINE:
        ┌─────────────────┐
        │ StrategyRequest │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Data Ingestion  │ → MarketSnapshot
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Indicator Engine│ → IndicatorOutput
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Reasoning LLM   │ → TradeIdea
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Risk Engine     │ → RiskPlan
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Explanation LLM │ → TradeExplanation
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────────┐
        │TradeSuggestionResponse│
        └─────────────────────┘
    """

    @property
    def name(self) -> str:
        return "StrategyService"

    @abstractmethod
    async def execute(self, input_data: StrategyRequest) -> TradeSuggestionResponse:
        """Run the complete trade suggestion pipeline."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check health of all dependent services."""
        pass
