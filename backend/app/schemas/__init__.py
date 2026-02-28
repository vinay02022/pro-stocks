"""
StockPro Schema Contracts

This module defines all JSON contracts between system components.
These are the authoritative interfaces - all modules must conform to these schemas.
"""

from app.schemas.market import (
    DataRequest,
    MarketSnapshot,
    SymbolData,
    OHLCV,
    OptionsChainData,
    NewsItem,
)
from app.schemas.indicators import (
    IndicatorRequest,
    IndicatorOutput,
    TrendIndicators,
    MomentumIndicators,
    VolatilityIndicators,
    VolumeIndicators,
    RiskMetrics,
)
from app.schemas.trade import (
    TradeIdea,
    ConfidenceBand,
    MarketRegime,
    TradeReasoning,
    EntryPlan,
)
from app.schemas.risk import (
    RiskPlan,
    ApprovedPlan,
    PortfolioImpact,
    PortfolioState,
    RiskConfig,
)
from app.schemas.explanation import (
    TradeExplanation,
    AlternativeScenario,
    ValidatedTrade,
)

__all__ = [
    # Market
    "DataRequest",
    "MarketSnapshot",
    "SymbolData",
    "OHLCV",
    "OptionsChainData",
    "NewsItem",
    # Indicators
    "IndicatorRequest",
    "IndicatorOutput",
    "TrendIndicators",
    "MomentumIndicators",
    "VolatilityIndicators",
    "VolumeIndicators",
    "RiskMetrics",
    # Trade
    "TradeIdea",
    "ConfidenceBand",
    "MarketRegime",
    "TradeReasoning",
    "EntryPlan",
    # Risk
    "RiskPlan",
    "ApprovedPlan",
    "PortfolioImpact",
    "PortfolioState",
    "RiskConfig",
    # Explanation
    "TradeExplanation",
    "AlternativeScenario",
    "ValidatedTrade",
]
