"""
Indicator Engine Service

CONTRACT:
    Input:  MarketSnapshot (with OHLCV data)
    Output: IndicatorOutput

RESPONSIBILITIES:
    - Calculate all technical indicators (RSI, MACD, EMA, etc.)
    - Detect support/resistance levels
    - Calculate volatility metrics (ATR, Bollinger Bands)
    - Generate position sizing recommendations
    - Compute risk metrics (stop loss, take profit levels)

PURE PYTHON - No LLM involvement.
Uses NumPy for calculations.
All math is deterministic and reproducible.
"""

from app.services.indicators.interface import IndicatorServiceInterface
from app.services.indicators.service import IndicatorService, get_indicator_service

__all__ = [
    "IndicatorServiceInterface",
    "IndicatorService",
    "get_indicator_service",
]
