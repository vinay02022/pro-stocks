"""
Strategy Evaluation Service

CONTRACT:
    Input:  Symbol + User Preferences
    Output: TradeSuggestionResponse (complete pipeline output)

RESPONSIBILITIES:
    - Orchestrate the full pipeline:
        1. Data Ingestion -> MarketSnapshot
        2. Indicator Engine -> IndicatorOutput
        3. Reasoning LLM -> TradeIdea
        4. Risk Engine -> RiskPlan
        5. Explanation LLM -> TradeExplanation
    - Handle errors at each stage
    - Provide fallbacks and graceful degradation

This is the main entry point for generating trade suggestions.
"""

from app.services.strategy.interface import (
    StrategyServiceInterface,
    StrategyRequest,
)
from app.services.strategy.service import StrategyService, get_strategy_service

__all__ = [
    "StrategyServiceInterface",
    "StrategyRequest",
    "StrategyService",
    "get_strategy_service",
]
