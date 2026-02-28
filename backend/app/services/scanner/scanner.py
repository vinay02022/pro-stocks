"""
Market Scanner Service

Scans multiple stocks for technical patterns and generates trading signals.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from zoneinfo import ZoneInfo
import numpy as np

from app.services.scanner.patterns import (
    PatternResult,
    SignalStrength,
    detect_breakout,
    detect_momentum,
    detect_volume_spike,
    detect_ema_crossover,
    detect_rsi_extreme,
    detect_macd_crossover,
    detect_support_resistance_bounce,
    detect_bollinger_squeeze,
)
from app.services.data_ingestion.stock_list import get_nifty50_stocks, get_all_stocks
from app.services.data_ingestion.service import DataIngestionService
from app.schemas.market import Timeframe

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


class PatternType(str, Enum):
    """Available pattern types for scanning."""
    BREAKOUT = "breakout"
    MOMENTUM = "momentum"
    VOLUME_SPIKE = "volume_spike"
    EMA_CROSSOVER = "ema_crossover"
    RSI_EXTREME = "rsi_extreme"
    MACD_CROSSOVER = "macd_crossover"
    SR_BOUNCE = "sr_bounce"
    BB_SQUEEZE = "bb_squeeze"
    ALL = "all"


@dataclass
class ScanResult:
    """Result of scanning a single stock."""
    symbol: str
    current_price: float
    day_change_percent: float
    patterns_found: List[Dict[str, Any]]
    total_score: float
    dominant_signal: str  # BULLISH, BEARISH, NEUTRAL
    scan_time: str = field(default_factory=lambda: datetime.now(IST).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketScanner:
    """
    Scans stocks for technical patterns.

    Usage:
        scanner = MarketScanner()
        results = await scanner.scan_all(patterns=[PatternType.BREAKOUT, PatternType.MOMENTUM])
    """

    def __init__(self):
        self._data_service = DataIngestionService()
        self._cache: Dict[str, ScanResult] = {}
        self._last_scan_time: Optional[datetime] = None

    async def scan_symbol(
        self,
        symbol: str,
        patterns: List[PatternType] = None,
        timeframe: Timeframe = Timeframe.D1,
    ) -> Optional[ScanResult]:
        """
        Scan a single symbol for patterns.
        """
        if patterns is None or PatternType.ALL in patterns:
            patterns = [
                PatternType.BREAKOUT,
                PatternType.MOMENTUM,
                PatternType.VOLUME_SPIKE,
                PatternType.EMA_CROSSOVER,
                PatternType.RSI_EXTREME,
                PatternType.MACD_CROSSOVER,
                PatternType.SR_BOUNCE,
                PatternType.BB_SQUEEZE,
            ]

        try:
            # Fetch data
            data = await self._data_service.get_symbol_data(
                symbol=symbol,
                timeframe=timeframe,
                lookback=100,
            )

            if not data or len(data.ohlcv) < 50:
                logger.debug(f"Insufficient data for {symbol}")
                return None

            # Convert to numpy arrays
            closes = np.array([c.close for c in data.ohlcv])
            highs = np.array([c.high for c in data.ohlcv])
            lows = np.array([c.low for c in data.ohlcv])
            volumes = np.array([c.volume for c in data.ohlcv])

            # Run pattern detections
            patterns_found = []

            pattern_detectors = {
                PatternType.BREAKOUT: lambda: detect_breakout(highs, lows, closes, volumes),
                PatternType.MOMENTUM: lambda: detect_momentum(closes, volumes),
                PatternType.VOLUME_SPIKE: lambda: detect_volume_spike(closes, volumes),
                PatternType.EMA_CROSSOVER: lambda: detect_ema_crossover(closes),
                PatternType.RSI_EXTREME: lambda: detect_rsi_extreme(closes),
                PatternType.MACD_CROSSOVER: lambda: detect_macd_crossover(closes),
                PatternType.SR_BOUNCE: lambda: detect_support_resistance_bounce(highs, lows, closes),
                PatternType.BB_SQUEEZE: lambda: detect_bollinger_squeeze(closes),
            }

            for pattern_type in patterns:
                if pattern_type in pattern_detectors:
                    try:
                        result = pattern_detectors[pattern_type]()
                        if result.detected:
                            patterns_found.append({
                                "type": result.pattern_type,
                                "signal": result.signal,
                                "strength": result.strength.value,
                                "score": result.score,
                                "details": result.details,
                                "entry_price": result.entry_price,
                                "stop_loss": result.stop_loss,
                                "target": result.target,
                            })
                    except Exception as e:
                        logger.debug(f"Pattern detection error for {symbol} - {pattern_type}: {e}")

            # Calculate total score and dominant signal
            total_score = sum(p["score"] for p in patterns_found) if patterns_found else 0
            bullish_count = sum(1 for p in patterns_found if p["signal"] == "BULLISH")
            bearish_count = sum(1 for p in patterns_found if p["signal"] == "BEARISH")

            dominant_signal = "BULLISH" if bullish_count > bearish_count else \
                             "BEARISH" if bearish_count > bullish_count else "NEUTRAL"

            return ScanResult(
                symbol=symbol,
                current_price=data.current_price,
                day_change_percent=data.day_change_percent,
                patterns_found=patterns_found,
                total_score=total_score,
                dominant_signal=dominant_signal,
            )

        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            return None

    async def scan_multiple(
        self,
        symbols: List[str],
        patterns: List[PatternType] = None,
        timeframe: Timeframe = Timeframe.D1,
        min_score: float = 0,
        signal_filter: Optional[str] = None,  # BULLISH, BEARISH, or None for all
    ) -> List[ScanResult]:
        """
        Scan multiple symbols concurrently.
        """
        # Scan all symbols concurrently
        tasks = [
            self.scan_symbol(symbol, patterns, timeframe)
            for symbol in symbols
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter and sort results
        valid_results = []
        for result in results:
            if isinstance(result, ScanResult):
                # Apply filters
                if result.total_score >= min_score:
                    if signal_filter is None or result.dominant_signal == signal_filter:
                        if result.patterns_found:  # Only include if patterns found
                            valid_results.append(result)

        # Sort by total score descending
        valid_results.sort(key=lambda x: x.total_score, reverse=True)

        self._last_scan_time = datetime.now(IST)
        return valid_results

    async def scan_nifty50(
        self,
        patterns: List[PatternType] = None,
        timeframe: Timeframe = Timeframe.D1,
        min_score: float = 40,
        signal_filter: Optional[str] = None,
    ) -> List[ScanResult]:
        """
        Scan all Nifty 50 stocks.
        """
        nifty50 = get_nifty50_stocks()
        symbols = [s["symbol"] for s in nifty50]
        return await self.scan_multiple(symbols, patterns, timeframe, min_score, signal_filter)

    async def scan_all_stocks(
        self,
        patterns: List[PatternType] = None,
        timeframe: Timeframe = Timeframe.D1,
        min_score: float = 50,
        signal_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[ScanResult]:
        """
        Scan all available stocks (limited to prevent overload).
        """
        all_stocks = get_all_stocks()
        symbols = [s["symbol"] for s in all_stocks[:limit]]
        return await self.scan_multiple(symbols, patterns, timeframe, min_score, signal_filter)

    async def get_top_bullish(
        self,
        limit: int = 10,
        timeframe: Timeframe = Timeframe.D1,
    ) -> List[ScanResult]:
        """
        Get top bullish stocks from Nifty 50.
        """
        results = await self.scan_nifty50(
            patterns=[PatternType.ALL],
            timeframe=timeframe,
            min_score=30,
            signal_filter="BULLISH",
        )
        return results[:limit]

    async def get_top_bearish(
        self,
        limit: int = 10,
        timeframe: Timeframe = Timeframe.D1,
    ) -> List[ScanResult]:
        """
        Get top bearish stocks from Nifty 50.
        """
        results = await self.scan_nifty50(
            patterns=[PatternType.ALL],
            timeframe=timeframe,
            min_score=30,
            signal_filter="BEARISH",
        )
        return results[:limit]

    async def get_breakouts(
        self,
        timeframe: Timeframe = Timeframe.D1,
    ) -> List[ScanResult]:
        """
        Get stocks with breakout patterns.
        """
        return await self.scan_nifty50(
            patterns=[PatternType.BREAKOUT],
            timeframe=timeframe,
            min_score=50,
        )

    async def get_momentum_stocks(
        self,
        timeframe: Timeframe = Timeframe.D1,
    ) -> List[ScanResult]:
        """
        Get stocks with strong momentum.
        """
        return await self.scan_nifty50(
            patterns=[PatternType.MOMENTUM],
            timeframe=timeframe,
            min_score=50,
        )

    async def get_volume_spikes(
        self,
        timeframe: Timeframe = Timeframe.D1,
    ) -> List[ScanResult]:
        """
        Get stocks with unusual volume.
        """
        return await self.scan_nifty50(
            patterns=[PatternType.VOLUME_SPIKE],
            timeframe=timeframe,
            min_score=40,
        )


# Singleton instance
_scanner: Optional[MarketScanner] = None


def get_scanner() -> MarketScanner:
    """Get the scanner singleton."""
    global _scanner
    if _scanner is None:
        _scanner = MarketScanner()
    return _scanner
