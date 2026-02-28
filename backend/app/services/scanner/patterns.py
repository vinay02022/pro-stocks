"""
Pattern Detection Algorithms

Detects various technical patterns in stock data.
"""

import numpy as np
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from app.services.indicators.calculations import (
    ema,
    sma,
    rsi,
    macd,
    atr,
    bollinger_bands,
    adx,
    obv,
    find_support_resistance,
)


class SignalStrength(str, Enum):
    """Signal strength levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class PatternResult:
    """Result of pattern detection."""
    detected: bool
    pattern_type: str
    signal: str  # BULLISH, BEARISH, NEUTRAL
    strength: SignalStrength
    score: float  # 0-100
    details: Dict[str, Any]
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target: Optional[float] = None


def _calculate_strength(score: float) -> SignalStrength:
    """Convert score to signal strength."""
    if score >= 80:
        return SignalStrength.VERY_STRONG
    elif score >= 60:
        return SignalStrength.STRONG
    elif score >= 40:
        return SignalStrength.MODERATE
    return SignalStrength.WEAK


def detect_breakout(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    lookback: int = 20,
) -> PatternResult:
    """
    Detect price breakout patterns.

    Looks for:
    - Price breaking above resistance with volume
    - Price breaking below support with volume
    """
    if len(closes) < lookback + 5:
        return PatternResult(
            detected=False,
            pattern_type="breakout",
            signal="NEUTRAL",
            strength=SignalStrength.WEAK,
            score=0,
            details={"error": "Insufficient data"},
        )

    current_price = closes[-1]
    current_volume = volumes[-1]

    # Find recent high and low (excluding last few candles)
    recent_high = np.max(highs[-lookback:-3])
    recent_low = np.min(lows[-lookback:-3])
    avg_volume = np.mean(volumes[-lookback:-1])

    # ATR for stop loss calculation
    atr_values = atr(highs, lows, closes, period=14)
    current_atr = atr_values[-1] if not np.isnan(atr_values[-1]) else (highs[-1] - lows[-1])

    # Check for bullish breakout (price above recent high with volume)
    bullish_breakout = current_price > recent_high and current_volume > avg_volume * 1.5

    # Check for bearish breakdown (price below recent low with volume)
    bearish_breakdown = current_price < recent_low and current_volume > avg_volume * 1.5

    if bullish_breakout:
        volume_ratio = current_volume / avg_volume
        price_extension = (current_price - recent_high) / recent_high * 100

        # Score based on volume and price extension
        score = min(100, 50 + (volume_ratio - 1.5) * 20 + price_extension * 10)

        return PatternResult(
            detected=True,
            pattern_type="breakout",
            signal="BULLISH",
            strength=_calculate_strength(score),
            score=score,
            details={
                "breakout_level": round(recent_high, 2),
                "current_price": round(current_price, 2),
                "volume_ratio": round(volume_ratio, 2),
                "price_extension_percent": round(price_extension, 2),
            },
            entry_price=current_price,
            stop_loss=round(recent_high - current_atr, 2),
            target=round(current_price + (current_price - recent_high) * 2, 2),
        )

    elif bearish_breakdown:
        volume_ratio = current_volume / avg_volume
        price_extension = (recent_low - current_price) / recent_low * 100

        score = min(100, 50 + (volume_ratio - 1.5) * 20 + price_extension * 10)

        return PatternResult(
            detected=True,
            pattern_type="breakout",
            signal="BEARISH",
            strength=_calculate_strength(score),
            score=score,
            details={
                "breakdown_level": round(recent_low, 2),
                "current_price": round(current_price, 2),
                "volume_ratio": round(volume_ratio, 2),
                "price_extension_percent": round(price_extension, 2),
            },
            entry_price=current_price,
            stop_loss=round(recent_low + current_atr, 2),
            target=round(current_price - (recent_low - current_price) * 2, 2),
        )

    return PatternResult(
        detected=False,
        pattern_type="breakout",
        signal="NEUTRAL",
        strength=SignalStrength.WEAK,
        score=0,
        details={
            "recent_high": round(recent_high, 2),
            "recent_low": round(recent_low, 2),
            "current_price": round(current_price, 2),
        },
    )


def detect_momentum(
    closes: np.ndarray,
    volumes: np.ndarray,
    lookback: int = 14,
) -> PatternResult:
    """
    Detect momentum patterns using RSI, price change, and volume.
    """
    if len(closes) < lookback + 10:
        return PatternResult(
            detected=False,
            pattern_type="momentum",
            signal="NEUTRAL",
            strength=SignalStrength.WEAK,
            score=0,
            details={"error": "Insufficient data"},
        )

    current_price = closes[-1]

    # Calculate RSI
    rsi_values = rsi(closes, period=14)
    current_rsi = rsi_values[-1]

    # Price momentum (rate of change)
    roc_5 = (closes[-1] - closes[-6]) / closes[-6] * 100  # 5-day ROC
    roc_10 = (closes[-1] - closes[-11]) / closes[-11] * 100  # 10-day ROC

    # Volume trend
    recent_vol = np.mean(volumes[-5:])
    older_vol = np.mean(volumes[-10:-5])
    vol_increase = recent_vol > older_vol * 1.2

    # ADX for trend strength
    # Note: Need highs/lows for ADX, using closes as proxy
    adx_values, plus_di, minus_di = adx(closes, closes, closes, period=14)
    current_adx = adx_values[-1] if not np.isnan(adx_values[-1]) else 20

    # Determine momentum direction and strength
    bullish_momentum = roc_5 > 2 and roc_10 > 3 and current_rsi > 50 and current_rsi < 80
    bearish_momentum = roc_5 < -2 and roc_10 < -3 and current_rsi < 50 and current_rsi > 20

    if bullish_momentum:
        score = min(100, 40 + roc_5 * 3 + (current_adx / 2) + (10 if vol_increase else 0))

        return PatternResult(
            detected=True,
            pattern_type="momentum",
            signal="BULLISH",
            strength=_calculate_strength(score),
            score=score,
            details={
                "rsi": round(current_rsi, 2),
                "roc_5d": round(roc_5, 2),
                "roc_10d": round(roc_10, 2),
                "adx": round(current_adx, 2),
                "volume_increasing": vol_increase,
            },
            entry_price=current_price,
        )

    elif bearish_momentum:
        score = min(100, 40 + abs(roc_5) * 3 + (current_adx / 2) + (10 if vol_increase else 0))

        return PatternResult(
            detected=True,
            pattern_type="momentum",
            signal="BEARISH",
            strength=_calculate_strength(score),
            score=score,
            details={
                "rsi": round(current_rsi, 2),
                "roc_5d": round(roc_5, 2),
                "roc_10d": round(roc_10, 2),
                "adx": round(current_adx, 2),
                "volume_increasing": vol_increase,
            },
            entry_price=current_price,
        )

    return PatternResult(
        detected=False,
        pattern_type="momentum",
        signal="NEUTRAL",
        strength=SignalStrength.WEAK,
        score=0,
        details={
            "rsi": round(current_rsi, 2) if not np.isnan(current_rsi) else None,
            "roc_5d": round(roc_5, 2),
            "roc_10d": round(roc_10, 2),
        },
    )


def detect_volume_spike(
    closes: np.ndarray,
    volumes: np.ndarray,
    lookback: int = 20,
    spike_threshold: float = 2.0,
) -> PatternResult:
    """
    Detect unusual volume spikes that may indicate institutional activity.
    """
    if len(volumes) < lookback + 1:
        return PatternResult(
            detected=False,
            pattern_type="volume_spike",
            signal="NEUTRAL",
            strength=SignalStrength.WEAK,
            score=0,
            details={"error": "Insufficient data"},
        )

    current_volume = volumes[-1]
    current_price = closes[-1]
    prev_price = closes[-2]

    avg_volume = np.mean(volumes[-lookback:-1])
    std_volume = np.std(volumes[-lookback:-1])

    volume_ratio = current_volume / avg_volume
    z_score = (current_volume - avg_volume) / std_volume if std_volume > 0 else 0

    price_change = (current_price - prev_price) / prev_price * 100

    # Volume spike detected
    if volume_ratio >= spike_threshold:
        signal = "BULLISH" if price_change > 0.5 else "BEARISH" if price_change < -0.5 else "NEUTRAL"

        score = min(100, 30 + (volume_ratio - 2) * 15 + abs(price_change) * 5)

        return PatternResult(
            detected=True,
            pattern_type="volume_spike",
            signal=signal,
            strength=_calculate_strength(score),
            score=score,
            details={
                "volume_ratio": round(volume_ratio, 2),
                "z_score": round(z_score, 2),
                "current_volume": int(current_volume),
                "avg_volume": int(avg_volume),
                "price_change_percent": round(price_change, 2),
            },
            entry_price=current_price if signal != "NEUTRAL" else None,
        )

    return PatternResult(
        detected=False,
        pattern_type="volume_spike",
        signal="NEUTRAL",
        strength=SignalStrength.WEAK,
        score=0,
        details={
            "volume_ratio": round(volume_ratio, 2),
            "avg_volume": int(avg_volume),
        },
    )


def detect_ema_crossover(
    closes: np.ndarray,
    fast_period: int = 9,
    slow_period: int = 21,
) -> PatternResult:
    """
    Detect EMA crossover patterns.

    Golden cross: fast EMA crosses above slow EMA
    Death cross: fast EMA crosses below slow EMA
    """
    if len(closes) < slow_period + 5:
        return PatternResult(
            detected=False,
            pattern_type="ema_crossover",
            signal="NEUTRAL",
            strength=SignalStrength.WEAK,
            score=0,
            details={"error": "Insufficient data"},
        )

    fast_ema = ema(closes, fast_period)
    slow_ema = ema(closes, slow_period)

    current_fast = fast_ema[-1]
    current_slow = slow_ema[-1]
    prev_fast = fast_ema[-2]
    prev_slow = slow_ema[-2]

    current_price = closes[-1]

    # Golden cross (bullish)
    golden_cross = prev_fast <= prev_slow and current_fast > current_slow

    # Death cross (bearish)
    death_cross = prev_fast >= prev_slow and current_fast < current_slow

    # Calculate separation for strength
    separation = abs(current_fast - current_slow) / current_slow * 100

    if golden_cross:
        score = min(100, 60 + separation * 10)

        return PatternResult(
            detected=True,
            pattern_type="ema_crossover",
            signal="BULLISH",
            strength=_calculate_strength(score),
            score=score,
            details={
                "crossover_type": "golden_cross",
                "fast_ema": round(current_fast, 2),
                "slow_ema": round(current_slow, 2),
                "separation_percent": round(separation, 2),
                "fast_period": fast_period,
                "slow_period": slow_period,
            },
            entry_price=current_price,
            stop_loss=round(current_slow * 0.98, 2),  # 2% below slow EMA
        )

    elif death_cross:
        score = min(100, 60 + separation * 10)

        return PatternResult(
            detected=True,
            pattern_type="ema_crossover",
            signal="BEARISH",
            strength=_calculate_strength(score),
            score=score,
            details={
                "crossover_type": "death_cross",
                "fast_ema": round(current_fast, 2),
                "slow_ema": round(current_slow, 2),
                "separation_percent": round(separation, 2),
                "fast_period": fast_period,
                "slow_period": slow_period,
            },
            entry_price=current_price,
            stop_loss=round(current_slow * 1.02, 2),  # 2% above slow EMA
        )

    # Check if price is above/below EMAs (trend following)
    trend = "BULLISH" if current_price > current_fast > current_slow else \
            "BEARISH" if current_price < current_fast < current_slow else "NEUTRAL"

    return PatternResult(
        detected=False,
        pattern_type="ema_crossover",
        signal=trend,
        strength=SignalStrength.WEAK,
        score=0,
        details={
            "fast_ema": round(current_fast, 2),
            "slow_ema": round(current_slow, 2),
            "price_vs_emas": trend,
        },
    )


def detect_rsi_extreme(
    closes: np.ndarray,
    period: int = 14,
    overbought: float = 70,
    oversold: float = 30,
) -> PatternResult:
    """
    Detect RSI extreme conditions (overbought/oversold).
    """
    if len(closes) < period + 5:
        return PatternResult(
            detected=False,
            pattern_type="rsi_extreme",
            signal="NEUTRAL",
            strength=SignalStrength.WEAK,
            score=0,
            details={"error": "Insufficient data"},
        )

    rsi_values = rsi(closes, period)
    current_rsi = rsi_values[-1]
    prev_rsi = rsi_values[-2]

    current_price = closes[-1]

    # Check for RSI turning from extreme
    rsi_turning_up = prev_rsi < oversold and current_rsi > prev_rsi
    rsi_turning_down = prev_rsi > overbought and current_rsi < prev_rsi

    if current_rsi <= oversold or rsi_turning_up:
        # Oversold - potential bullish reversal
        extreme_level = max(0, oversold - current_rsi)  # How oversold
        turning_bonus = 15 if rsi_turning_up else 0
        score = min(100, 50 + extreme_level * 2 + turning_bonus)

        return PatternResult(
            detected=True,
            pattern_type="rsi_extreme",
            signal="BULLISH",
            strength=_calculate_strength(score),
            score=score,
            details={
                "rsi": round(current_rsi, 2),
                "condition": "oversold",
                "turning_up": rsi_turning_up,
                "threshold": oversold,
            },
            entry_price=current_price,
        )

    elif current_rsi >= overbought or rsi_turning_down:
        # Overbought - potential bearish reversal
        extreme_level = max(0, current_rsi - overbought)
        turning_bonus = 15 if rsi_turning_down else 0
        score = min(100, 50 + extreme_level * 2 + turning_bonus)

        return PatternResult(
            detected=True,
            pattern_type="rsi_extreme",
            signal="BEARISH",
            strength=_calculate_strength(score),
            score=score,
            details={
                "rsi": round(current_rsi, 2),
                "condition": "overbought",
                "turning_down": rsi_turning_down,
                "threshold": overbought,
            },
            entry_price=current_price,
        )

    return PatternResult(
        detected=False,
        pattern_type="rsi_extreme",
        signal="NEUTRAL",
        strength=SignalStrength.WEAK,
        score=0,
        details={
            "rsi": round(current_rsi, 2),
            "condition": "neutral",
        },
    )


def detect_macd_crossover(
    closes: np.ndarray,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> PatternResult:
    """
    Detect MACD crossover signals.
    """
    if len(closes) < slow + signal_period + 5:
        return PatternResult(
            detected=False,
            pattern_type="macd_crossover",
            signal="NEUTRAL",
            strength=SignalStrength.WEAK,
            score=0,
            details={"error": "Insufficient data"},
        )

    macd_line, signal_line, histogram = macd(closes, fast, slow, signal_period)

    current_macd = macd_line[-1]
    current_signal = signal_line[-1]
    prev_macd = macd_line[-2]
    prev_signal = signal_line[-2]
    current_histogram = histogram[-1]
    prev_histogram = histogram[-2]

    current_price = closes[-1]

    # Bullish crossover
    bullish_cross = prev_macd <= prev_signal and current_macd > current_signal

    # Bearish crossover
    bearish_cross = prev_macd >= prev_signal and current_macd < current_signal

    # Histogram momentum
    histogram_expanding = abs(current_histogram) > abs(prev_histogram)

    if bullish_cross:
        # Stronger if crossing above zero line
        zero_cross_bonus = 15 if current_macd > 0 else 0
        momentum_bonus = 10 if histogram_expanding else 0
        score = min(100, 55 + zero_cross_bonus + momentum_bonus)

        return PatternResult(
            detected=True,
            pattern_type="macd_crossover",
            signal="BULLISH",
            strength=_calculate_strength(score),
            score=score,
            details={
                "macd": round(current_macd, 4),
                "signal": round(current_signal, 4),
                "histogram": round(current_histogram, 4),
                "above_zero": current_macd > 0,
                "histogram_expanding": histogram_expanding,
            },
            entry_price=current_price,
        )

    elif bearish_cross:
        zero_cross_bonus = 15 if current_macd < 0 else 0
        momentum_bonus = 10 if histogram_expanding else 0
        score = min(100, 55 + zero_cross_bonus + momentum_bonus)

        return PatternResult(
            detected=True,
            pattern_type="macd_crossover",
            signal="BEARISH",
            strength=_calculate_strength(score),
            score=score,
            details={
                "macd": round(current_macd, 4),
                "signal": round(current_signal, 4),
                "histogram": round(current_histogram, 4),
                "below_zero": current_macd < 0,
                "histogram_expanding": histogram_expanding,
            },
            entry_price=current_price,
        )

    return PatternResult(
        detected=False,
        pattern_type="macd_crossover",
        signal="NEUTRAL",
        strength=SignalStrength.WEAK,
        score=0,
        details={
            "macd": round(current_macd, 4) if not np.isnan(current_macd) else None,
            "signal": round(current_signal, 4) if not np.isnan(current_signal) else None,
            "histogram": round(current_histogram, 4) if not np.isnan(current_histogram) else None,
        },
    )


def detect_support_resistance_bounce(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    lookback: int = 50,
    tolerance: float = 0.02,  # 2% tolerance
) -> PatternResult:
    """
    Detect price bouncing off support or resistance levels.
    """
    if len(closes) < lookback + 5:
        return PatternResult(
            detected=False,
            pattern_type="sr_bounce",
            signal="NEUTRAL",
            strength=SignalStrength.WEAK,
            score=0,
            details={"error": "Insufficient data"},
        )

    current_price = closes[-1]
    current_low = lows[-1]
    current_high = highs[-1]

    # Find support and resistance levels
    support_levels, resistance_levels = find_support_resistance(
        highs, lows, closes, lookback
    )

    if not support_levels and not resistance_levels:
        return PatternResult(
            detected=False,
            pattern_type="sr_bounce",
            signal="NEUTRAL",
            strength=SignalStrength.WEAK,
            score=0,
            details={"message": "No clear S/R levels found"},
        )

    # Check for support bounce
    for support in support_levels:
        distance = abs(current_low - support) / support
        if distance <= tolerance and closes[-1] > closes[-2]:  # Bouncing up
            score = min(100, 70 - (distance * 100 * 10))  # Closer = higher score

            return PatternResult(
                detected=True,
                pattern_type="sr_bounce",
                signal="BULLISH",
                strength=_calculate_strength(score),
                score=score,
                details={
                    "bounce_type": "support_bounce",
                    "level": round(support, 2),
                    "distance_percent": round(distance * 100, 2),
                    "current_price": round(current_price, 2),
                },
                entry_price=current_price,
                stop_loss=round(support * 0.98, 2),  # 2% below support
                target=round(resistance_levels[0] if resistance_levels else current_price * 1.05, 2),
            )

    # Check for resistance rejection
    for resistance in resistance_levels:
        distance = abs(current_high - resistance) / resistance
        if distance <= tolerance and closes[-1] < closes[-2]:  # Rejecting down
            score = min(100, 70 - (distance * 100 * 10))

            return PatternResult(
                detected=True,
                pattern_type="sr_bounce",
                signal="BEARISH",
                strength=_calculate_strength(score),
                score=score,
                details={
                    "bounce_type": "resistance_rejection",
                    "level": round(resistance, 2),
                    "distance_percent": round(distance * 100, 2),
                    "current_price": round(current_price, 2),
                },
                entry_price=current_price,
                stop_loss=round(resistance * 1.02, 2),  # 2% above resistance
                target=round(support_levels[0] if support_levels else current_price * 0.95, 2),
            )

    return PatternResult(
        detected=False,
        pattern_type="sr_bounce",
        signal="NEUTRAL",
        strength=SignalStrength.WEAK,
        score=0,
        details={
            "support_levels": support_levels[:3] if support_levels else [],
            "resistance_levels": resistance_levels[:3] if resistance_levels else [],
            "current_price": round(current_price, 2),
        },
    )


def detect_bollinger_squeeze(
    closes: np.ndarray,
    period: int = 20,
    std_dev: float = 2.0,
) -> PatternResult:
    """
    Detect Bollinger Band squeeze (low volatility before big move).
    """
    if len(closes) < period + 10:
        return PatternResult(
            detected=False,
            pattern_type="bb_squeeze",
            signal="NEUTRAL",
            strength=SignalStrength.WEAK,
            score=0,
            details={"error": "Insufficient data"},
        )

    upper, middle, lower, bandwidth, percent_b = bollinger_bands(closes, period, std_dev)

    current_bandwidth = bandwidth[-1]
    avg_bandwidth = np.nanmean(bandwidth[-50:])

    current_price = closes[-1]
    current_percent_b = percent_b[-1]

    # Squeeze: bandwidth is significantly below average
    is_squeeze = current_bandwidth < avg_bandwidth * 0.7

    if is_squeeze:
        # Direction hint from %B
        signal = "BULLISH" if current_percent_b > 0.5 else "BEARISH" if current_percent_b < 0.5 else "NEUTRAL"

        squeeze_intensity = (1 - (current_bandwidth / avg_bandwidth)) * 100
        score = min(100, 50 + squeeze_intensity)

        return PatternResult(
            detected=True,
            pattern_type="bb_squeeze",
            signal=signal,
            strength=_calculate_strength(score),
            score=score,
            details={
                "bandwidth": round(current_bandwidth, 4),
                "avg_bandwidth": round(avg_bandwidth, 4),
                "squeeze_intensity": round(squeeze_intensity, 2),
                "percent_b": round(current_percent_b, 2),
                "upper_band": round(upper[-1], 2),
                "lower_band": round(lower[-1], 2),
            },
            entry_price=current_price,
        )

    return PatternResult(
        detected=False,
        pattern_type="bb_squeeze",
        signal="NEUTRAL",
        strength=SignalStrength.WEAK,
        score=0,
        details={
            "bandwidth": round(current_bandwidth, 4) if not np.isnan(current_bandwidth) else None,
            "avg_bandwidth": round(avg_bandwidth, 4),
        },
    )
