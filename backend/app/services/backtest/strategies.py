"""
Trading Strategies for Backtesting

Each strategy implements entry/exit logic based on technical indicators.
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from app.services.indicators.calculations import (
    ema,
    sma,
    rsi,
    macd,
    atr,
    bollinger_bands,
)


class SignalType(str, Enum):
    """Trading signal types."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Signal:
    """Trading signal from strategy."""
    signal_type: SignalType
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""


class Strategy(ABC):
    """Base class for trading strategies."""

    def __init__(self, params: Dict[str, Any] = None):
        self.params = params or {}
        self.name = self.__class__.__name__

    @abstractmethod
    def generate_signal(
        self,
        idx: int,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        position: int,  # 1=long, -1=short, 0=flat
    ) -> Signal:
        """
        Generate trading signal at index idx.

        Args:
            idx: Current bar index
            opens, highs, lows, closes, volumes: Price data arrays
            position: Current position (1=long, -1=short, 0=flat)

        Returns:
            Signal with BUY, SELL, or HOLD
        """
        pass

    def get_params(self) -> Dict[str, Any]:
        """Get strategy parameters."""
        return self.params


class EMACrossoverStrategy(Strategy):
    """
    EMA Crossover Strategy

    Buy when fast EMA crosses above slow EMA.
    Sell when fast EMA crosses below slow EMA.
    """

    def __init__(self, fast_period: int = 9, slow_period: int = 21, atr_multiplier: float = 2.0):
        super().__init__({
            "fast_period": fast_period,
            "slow_period": slow_period,
            "atr_multiplier": atr_multiplier,
        })
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.atr_multiplier = atr_multiplier

    def generate_signal(
        self,
        idx: int,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        position: int,
    ) -> Signal:
        if idx < self.slow_period + 1:
            return Signal(SignalType.HOLD, closes[idx], reason="Insufficient data")

        # Calculate EMAs
        fast_ema = ema(closes[:idx + 1], self.fast_period)
        slow_ema = ema(closes[:idx + 1], self.slow_period)

        current_fast = fast_ema[-1]
        current_slow = slow_ema[-1]
        prev_fast = fast_ema[-2]
        prev_slow = slow_ema[-2]

        # Calculate ATR for stop loss
        atr_values = atr(highs[:idx + 1], lows[:idx + 1], closes[:idx + 1], period=14)
        current_atr = atr_values[-1] if not np.isnan(atr_values[-1]) else (highs[idx] - lows[idx])

        current_price = closes[idx]
        stop_loss = current_price - (current_atr * self.atr_multiplier)
        take_profit = current_price + (current_atr * self.atr_multiplier * 2)

        # Golden cross - buy signal
        if prev_fast <= prev_slow and current_fast > current_slow and position <= 0:
            return Signal(
                SignalType.BUY,
                current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f"Golden cross: EMA{self.fast_period} crossed above EMA{self.slow_period}",
            )

        # Death cross - sell signal
        if prev_fast >= prev_slow and current_fast < current_slow and position >= 0:
            return Signal(
                SignalType.SELL,
                current_price,
                stop_loss=current_price + (current_atr * self.atr_multiplier),
                take_profit=current_price - (current_atr * self.atr_multiplier * 2),
                reason=f"Death cross: EMA{self.fast_period} crossed below EMA{self.slow_period}",
            )

        return Signal(SignalType.HOLD, current_price, reason="No crossover")


class RSIReversalStrategy(Strategy):
    """
    RSI Reversal Strategy

    Buy when RSI crosses above oversold level (30).
    Sell when RSI crosses below overbought level (70).
    """

    def __init__(
        self,
        period: int = 14,
        overbought: float = 70,
        oversold: float = 30,
        atr_multiplier: float = 1.5,
    ):
        super().__init__({
            "period": period,
            "overbought": overbought,
            "oversold": oversold,
            "atr_multiplier": atr_multiplier,
        })
        self.period = period
        self.overbought = overbought
        self.oversold = oversold
        self.atr_multiplier = atr_multiplier

    def generate_signal(
        self,
        idx: int,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        position: int,
    ) -> Signal:
        if idx < self.period + 2:
            return Signal(SignalType.HOLD, closes[idx], reason="Insufficient data")

        # Calculate RSI
        rsi_values = rsi(closes[:idx + 1], self.period)
        current_rsi = rsi_values[-1]
        prev_rsi = rsi_values[-2]

        # Calculate ATR for stop loss
        atr_values = atr(highs[:idx + 1], lows[:idx + 1], closes[:idx + 1], period=14)
        current_atr = atr_values[-1] if not np.isnan(atr_values[-1]) else (highs[idx] - lows[idx])

        current_price = closes[idx]
        stop_loss = current_price - (current_atr * self.atr_multiplier)
        take_profit = current_price + (current_atr * self.atr_multiplier * 2)

        # Oversold reversal - buy
        if prev_rsi < self.oversold and current_rsi >= self.oversold and position <= 0:
            return Signal(
                SignalType.BUY,
                current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason=f"RSI crossed above oversold ({self.oversold}): {current_rsi:.1f}",
            )

        # Overbought reversal - sell
        if prev_rsi > self.overbought and current_rsi <= self.overbought and position >= 0:
            return Signal(
                SignalType.SELL,
                current_price,
                stop_loss=current_price + (current_atr * self.atr_multiplier),
                take_profit=current_price - (current_atr * self.atr_multiplier * 2),
                reason=f"RSI crossed below overbought ({self.overbought}): {current_rsi:.1f}",
            )

        return Signal(SignalType.HOLD, current_price, reason=f"RSI: {current_rsi:.1f}")


class BreakoutStrategy(Strategy):
    """
    Breakout Strategy

    Buy when price breaks above recent high with volume.
    Sell when price breaks below recent low with volume.
    """

    def __init__(
        self,
        lookback: int = 20,
        volume_threshold: float = 1.5,
        atr_multiplier: float = 2.0,
    ):
        super().__init__({
            "lookback": lookback,
            "volume_threshold": volume_threshold,
            "atr_multiplier": atr_multiplier,
        })
        self.lookback = lookback
        self.volume_threshold = volume_threshold
        self.atr_multiplier = atr_multiplier

    def generate_signal(
        self,
        idx: int,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        position: int,
    ) -> Signal:
        if idx < self.lookback + 5:
            return Signal(SignalType.HOLD, closes[idx], reason="Insufficient data")

        current_price = closes[idx]
        current_volume = volumes[idx]

        # Recent high/low (excluding last few bars)
        recent_high = np.max(highs[idx - self.lookback:idx - 2])
        recent_low = np.min(lows[idx - self.lookback:idx - 2])
        avg_volume = np.mean(volumes[idx - self.lookback:idx - 1])

        # Calculate ATR for stop loss
        atr_values = atr(highs[:idx + 1], lows[:idx + 1], closes[:idx + 1], period=14)
        current_atr = atr_values[-1] if not np.isnan(atr_values[-1]) else (highs[idx] - lows[idx])

        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

        # Bullish breakout
        if current_price > recent_high and volume_ratio >= self.volume_threshold and position <= 0:
            return Signal(
                SignalType.BUY,
                current_price,
                stop_loss=recent_high - current_atr,
                take_profit=current_price + (current_price - recent_high) * 2,
                reason=f"Bullish breakout above {recent_high:.2f} with {volume_ratio:.1f}x volume",
            )

        # Bearish breakdown
        if current_price < recent_low and volume_ratio >= self.volume_threshold and position >= 0:
            return Signal(
                SignalType.SELL,
                current_price,
                stop_loss=recent_low + current_atr,
                take_profit=current_price - (recent_low - current_price) * 2,
                reason=f"Bearish breakdown below {recent_low:.2f} with {volume_ratio:.1f}x volume",
            )

        return Signal(SignalType.HOLD, current_price, reason="No breakout")


class MACDStrategy(Strategy):
    """
    MACD Crossover Strategy

    Buy when MACD crosses above signal line.
    Sell when MACD crosses below signal line.
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
        atr_multiplier: float = 2.0,
    ):
        super().__init__({
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period,
            "atr_multiplier": atr_multiplier,
        })
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.atr_multiplier = atr_multiplier

    def generate_signal(
        self,
        idx: int,
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        position: int,
    ) -> Signal:
        min_data = self.slow_period + self.signal_period + 2
        if idx < min_data:
            return Signal(SignalType.HOLD, closes[idx], reason="Insufficient data")

        # Calculate MACD
        macd_line, signal_line, histogram = macd(
            closes[:idx + 1],
            self.fast_period,
            self.slow_period,
            self.signal_period,
        )

        current_macd = macd_line[-1]
        current_signal = signal_line[-1]
        prev_macd = macd_line[-2]
        prev_signal = signal_line[-2]

        # Calculate ATR for stop loss
        atr_values = atr(highs[:idx + 1], lows[:idx + 1], closes[:idx + 1], period=14)
        current_atr = atr_values[-1] if not np.isnan(atr_values[-1]) else (highs[idx] - lows[idx])

        current_price = closes[idx]
        stop_loss = current_price - (current_atr * self.atr_multiplier)
        take_profit = current_price + (current_atr * self.atr_multiplier * 2)

        # Bullish crossover
        if prev_macd <= prev_signal and current_macd > current_signal and position <= 0:
            return Signal(
                SignalType.BUY,
                current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason="MACD bullish crossover",
            )

        # Bearish crossover
        if prev_macd >= prev_signal and current_macd < current_signal and position >= 0:
            return Signal(
                SignalType.SELL,
                current_price,
                stop_loss=current_price + (current_atr * self.atr_multiplier),
                take_profit=current_price - (current_atr * self.atr_multiplier * 2),
                reason="MACD bearish crossover",
            )

        return Signal(SignalType.HOLD, current_price, reason="No MACD crossover")


# Strategy factory
def get_strategy(strategy_type: str, params: Dict[str, Any] = None) -> Strategy:
    """Get strategy by type name."""
    strategies = {
        "ema_crossover": EMACrossoverStrategy,
        "rsi_reversal": RSIReversalStrategy,
        "breakout": BreakoutStrategy,
        "macd": MACDStrategy,
    }

    if strategy_type not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_type}")

    strategy_class = strategies[strategy_type]
    return strategy_class(**params) if params else strategy_class()
