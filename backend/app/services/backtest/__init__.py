"""
Backtesting Engine

Test trading strategies on historical data.
"""

from app.services.backtest.engine import (
    BacktestEngine,
    BacktestResult,
    Trade,
    StrategyType,
    get_backtest_engine,
)
from app.services.backtest.strategies import (
    Strategy,
    EMACrossoverStrategy,
    RSIReversalStrategy,
    BreakoutStrategy,
    MACDStrategy,
)

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "Trade",
    "StrategyType",
    "get_backtest_engine",
    "Strategy",
    "EMACrossoverStrategy",
    "RSIReversalStrategy",
    "BreakoutStrategy",
    "MACDStrategy",
]
