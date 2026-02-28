"""
Market Scanner Service

Scans stocks for technical patterns and trading signals.
"""

from app.services.scanner.scanner import (
    MarketScanner,
    get_scanner,
    ScanResult,
    PatternType,
)
from app.services.scanner.patterns import (
    detect_breakout,
    detect_momentum,
    detect_volume_spike,
    detect_ema_crossover,
    detect_rsi_extreme,
    detect_macd_crossover,
    detect_support_resistance_bounce,
)

__all__ = [
    "MarketScanner",
    "get_scanner",
    "ScanResult",
    "PatternType",
    "detect_breakout",
    "detect_momentum",
    "detect_volume_spike",
    "detect_ema_crossover",
    "detect_rsi_extreme",
    "detect_macd_crossover",
    "detect_support_resistance_bounce",
]
