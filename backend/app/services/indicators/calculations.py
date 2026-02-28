"""
Technical Indicator Calculations

Pure Python/NumPy implementations of technical indicators.
NO LLM INVOLVEMENT - All math is deterministic.
"""

import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class OHLCVData:
    """OHLCV data arrays for calculations."""

    timestamps: np.ndarray
    opens: np.ndarray
    highs: np.ndarray
    lows: np.ndarray
    closes: np.ndarray
    volumes: np.ndarray


# =============================================================================
# MOVING AVERAGES
# =============================================================================


def sma(data: np.ndarray, period: int) -> np.ndarray:
    """Simple Moving Average."""
    if len(data) < period:
        return np.full(len(data), np.nan)

    result = np.full(len(data), np.nan)
    for i in range(period - 1, len(data)):
        result[i] = np.mean(data[i - period + 1 : i + 1])
    return result


def ema(data: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    if len(data) < period:
        return np.full(len(data), np.nan)

    result = np.full(len(data), np.nan)
    multiplier = 2 / (period + 1)

    # Start with SMA
    result[period - 1] = np.mean(data[:period])

    # Calculate EMA
    for i in range(period, len(data)):
        result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]

    return result


def wma(data: np.ndarray, period: int) -> np.ndarray:
    """Weighted Moving Average."""
    if len(data) < period:
        return np.full(len(data), np.nan)

    weights = np.arange(1, period + 1)
    result = np.full(len(data), np.nan)

    for i in range(period - 1, len(data)):
        result[i] = np.sum(data[i - period + 1 : i + 1] * weights) / np.sum(weights)

    return result


# =============================================================================
# MOMENTUM INDICATORS
# =============================================================================


def rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    """Relative Strength Index."""
    if len(closes) < period + 1:
        return np.full(len(closes), np.nan)

    # Calculate price changes
    deltas = np.diff(closes)

    # Separate gains and losses
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    # First average
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    result = np.full(len(closes), np.nan)

    # First RSI
    if avg_loss == 0:
        result[period] = 100
    else:
        rs = avg_gain / avg_loss
        result[period] = 100 - (100 / (1 + rs))

    # Subsequent RSI values using smoothed averages
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            result[i + 1] = 100
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100 - (100 / (1 + rs))

    return result


def macd(
    closes: np.ndarray,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    MACD (Moving Average Convergence Divergence).

    Returns: (macd_line, signal_line, histogram)
    """
    fast_ema = ema(closes, fast_period)
    slow_ema = ema(closes, slow_period)

    macd_line = fast_ema - slow_ema

    # Signal line is EMA of MACD line
    signal_line = ema(macd_line, signal_period)

    # Histogram
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def stochastic(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    k_period: int = 14,
    d_period: int = 3,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Stochastic Oscillator.

    Returns: (k, d)
    """
    if len(closes) < k_period:
        return np.full(len(closes), np.nan), np.full(len(closes), np.nan)

    k = np.full(len(closes), np.nan)

    for i in range(k_period - 1, len(closes)):
        highest_high = np.max(highs[i - k_period + 1 : i + 1])
        lowest_low = np.min(lows[i - k_period + 1 : i + 1])

        if highest_high == lowest_low:
            k[i] = 50
        else:
            k[i] = ((closes[i] - lowest_low) / (highest_high - lowest_low)) * 100

    d = sma(k, d_period)

    return k, d


def cci(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 20
) -> np.ndarray:
    """Commodity Channel Index."""
    typical_price = (highs + lows + closes) / 3
    tp_sma = sma(typical_price, period)

    # Mean deviation
    mean_dev = np.full(len(closes), np.nan)
    for i in range(period - 1, len(closes)):
        mean_dev[i] = np.mean(
            np.abs(typical_price[i - period + 1 : i + 1] - tp_sma[i])
        )

    result = (typical_price - tp_sma) / (0.015 * mean_dev)
    return result


def williams_r(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14
) -> np.ndarray:
    """Williams %R."""
    if len(closes) < period:
        return np.full(len(closes), np.nan)

    result = np.full(len(closes), np.nan)

    for i in range(period - 1, len(closes)):
        highest_high = np.max(highs[i - period + 1 : i + 1])
        lowest_low = np.min(lows[i - period + 1 : i + 1])

        if highest_high == lowest_low:
            result[i] = -50
        else:
            result[i] = ((highest_high - closes[i]) / (highest_high - lowest_low)) * -100

    return result


def mfi(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    period: int = 14,
) -> np.ndarray:
    """Money Flow Index."""
    typical_price = (highs + lows + closes) / 3
    raw_money_flow = typical_price * volumes

    # Positive and negative money flow
    pos_flow = np.zeros(len(closes))
    neg_flow = np.zeros(len(closes))

    for i in range(1, len(closes)):
        if typical_price[i] > typical_price[i - 1]:
            pos_flow[i] = raw_money_flow[i]
        elif typical_price[i] < typical_price[i - 1]:
            neg_flow[i] = raw_money_flow[i]

    result = np.full(len(closes), np.nan)

    for i in range(period, len(closes)):
        pos_sum = np.sum(pos_flow[i - period + 1 : i + 1])
        neg_sum = np.sum(neg_flow[i - period + 1 : i + 1])

        if neg_sum == 0:
            result[i] = 100
        else:
            money_ratio = pos_sum / neg_sum
            result[i] = 100 - (100 / (1 + money_ratio))

    return result


# =============================================================================
# VOLATILITY INDICATORS
# =============================================================================


def atr(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14
) -> np.ndarray:
    """Average True Range."""
    if len(closes) < 2:
        return np.full(len(closes), np.nan)

    # True Range
    tr = np.zeros(len(closes))
    tr[0] = highs[0] - lows[0]

    for i in range(1, len(closes)):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )

    # ATR is EMA of TR
    return ema(tr, period)


def bollinger_bands(
    closes: np.ndarray, period: int = 20, std_dev: float = 2.0
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Bollinger Bands.

    Returns: (upper, middle, lower, bandwidth, percent_b)
    """
    middle = sma(closes, period)

    # Standard deviation
    std = np.full(len(closes), np.nan)
    for i in range(period - 1, len(closes)):
        std[i] = np.std(closes[i - period + 1 : i + 1])

    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)

    # Bandwidth
    bandwidth = (upper - lower) / middle

    # %B (position within bands)
    percent_b = (closes - lower) / (upper - lower)

    return upper, middle, lower, bandwidth, percent_b


# =============================================================================
# VOLUME INDICATORS
# =============================================================================


def vwap(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray
) -> np.ndarray:
    """Volume Weighted Average Price."""
    typical_price = (highs + lows + closes) / 3
    cumulative_tpv = np.cumsum(typical_price * volumes)
    cumulative_volume = np.cumsum(volumes)

    # Avoid division by zero
    with np.errstate(divide="ignore", invalid="ignore"):
        result = cumulative_tpv / cumulative_volume
        result[cumulative_volume == 0] = typical_price[cumulative_volume == 0]

    return result


def obv(closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
    """On-Balance Volume."""
    result = np.zeros(len(closes))
    result[0] = volumes[0]

    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            result[i] = result[i - 1] + volumes[i]
        elif closes[i] < closes[i - 1]:
            result[i] = result[i - 1] - volumes[i]
        else:
            result[i] = result[i - 1]

    return result


# =============================================================================
# TREND INDICATORS
# =============================================================================


def adx(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Average Directional Index.

    Returns: (adx, plus_di, minus_di)
    """
    if len(closes) < period + 1:
        nan_arr = np.full(len(closes), np.nan)
        return nan_arr, nan_arr, nan_arr

    # Calculate +DM and -DM
    plus_dm = np.zeros(len(closes))
    minus_dm = np.zeros(len(closes))

    for i in range(1, len(closes)):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]

        if up_move > down_move and up_move > 0:
            plus_dm[i] = up_move
        if down_move > up_move and down_move > 0:
            minus_dm[i] = down_move

    # True Range
    tr = np.zeros(len(closes))
    tr[0] = highs[0] - lows[0]
    for i in range(1, len(closes)):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )

    # Smooth the values
    smoothed_plus_dm = ema(plus_dm, period)
    smoothed_minus_dm = ema(minus_dm, period)
    smoothed_tr = ema(tr, period)

    # +DI and -DI
    with np.errstate(divide="ignore", invalid="ignore"):
        plus_di = 100 * (smoothed_plus_dm / smoothed_tr)
        minus_di = 100 * (smoothed_minus_dm / smoothed_tr)

    plus_di = np.nan_to_num(plus_di, nan=0)
    minus_di = np.nan_to_num(minus_di, nan=0)

    # DX
    with np.errstate(divide="ignore", invalid="ignore"):
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    dx = np.nan_to_num(dx, nan=0)

    # ADX is smoothed DX
    adx_result = ema(dx, period)

    return adx_result, plus_di, minus_di


# =============================================================================
# SUPPORT/RESISTANCE
# =============================================================================


def find_pivot_points(
    high: float, low: float, close: float, pivot_type: str = "standard"
) -> dict:
    """
    Calculate pivot points.

    Types: standard, fibonacci, camarilla
    """
    if pivot_type == "standard":
        pivot = (high + low + close) / 3
        r1 = (2 * pivot) - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        s1 = (2 * pivot) - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)

    elif pivot_type == "fibonacci":
        pivot = (high + low + close) / 3
        diff = high - low
        r1 = pivot + (0.382 * diff)
        r2 = pivot + (0.618 * diff)
        r3 = pivot + diff
        s1 = pivot - (0.382 * diff)
        s2 = pivot - (0.618 * diff)
        s3 = pivot - diff

    elif pivot_type == "camarilla":
        pivot = (high + low + close) / 3
        diff = high - low
        r1 = close + (diff * 1.1 / 12)
        r2 = close + (diff * 1.1 / 6)
        r3 = close + (diff * 1.1 / 4)
        s1 = close - (diff * 1.1 / 12)
        s2 = close - (diff * 1.1 / 6)
        s3 = close - (diff * 1.1 / 4)

    else:
        raise ValueError(f"Unknown pivot type: {pivot_type}")

    return {
        "pivot": round(pivot, 2),
        "r1": round(r1, 2),
        "r2": round(r2, 2),
        "r3": round(r3, 2),
        "s1": round(s1, 2),
        "s2": round(s2, 2),
        "s3": round(s3, 2),
        "type": pivot_type,
    }


def find_support_resistance(
    highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, lookback: int = 50
) -> tuple[list[float], list[float]]:
    """
    Find support and resistance levels using local minima/maxima.

    Returns: (support_levels, resistance_levels)
    """
    if len(closes) < lookback:
        return [], []

    recent_highs = highs[-lookback:]
    recent_lows = lows[-lookback:]
    current_price = closes[-1]

    # Find local maxima (resistance)
    resistance = []
    for i in range(2, len(recent_highs) - 2):
        if (
            recent_highs[i] > recent_highs[i - 1]
            and recent_highs[i] > recent_highs[i - 2]
            and recent_highs[i] > recent_highs[i + 1]
            and recent_highs[i] > recent_highs[i + 2]
        ):
            if recent_highs[i] > current_price:
                resistance.append(round(recent_highs[i], 2))

    # Find local minima (support)
    support = []
    for i in range(2, len(recent_lows) - 2):
        if (
            recent_lows[i] < recent_lows[i - 1]
            and recent_lows[i] < recent_lows[i - 2]
            and recent_lows[i] < recent_lows[i + 1]
            and recent_lows[i] < recent_lows[i + 2]
        ):
            if recent_lows[i] < current_price:
                support.append(round(recent_lows[i], 2))

    # Sort by proximity to current price
    resistance = sorted(set(resistance))[:5]  # Top 5
    support = sorted(set(support), reverse=True)[:5]  # Top 5

    return support, resistance


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


def get_last_valid(arr: np.ndarray) -> Optional[float]:
    """Get last non-NaN value from array."""
    valid = arr[~np.isnan(arr)]
    return float(valid[-1]) if len(valid) > 0 else None


def detect_divergence(
    prices: np.ndarray, indicator: np.ndarray, lookback: int = 14
) -> Optional[str]:
    """
    Detect bullish or bearish divergence.

    Returns: 'BULLISH', 'BEARISH', or None
    """
    if len(prices) < lookback or len(indicator) < lookback:
        return None

    recent_prices = prices[-lookback:]
    recent_indicator = indicator[-lookback:]

    # Find price trend
    price_trend = recent_prices[-1] - recent_prices[0]

    # Find indicator trend
    valid_indicator = recent_indicator[~np.isnan(recent_indicator)]
    if len(valid_indicator) < 2:
        return None

    indicator_trend = valid_indicator[-1] - valid_indicator[0]

    # Bullish divergence: price making lower lows, indicator making higher lows
    if price_trend < 0 and indicator_trend > 0:
        return "BULLISH"

    # Bearish divergence: price making higher highs, indicator making lower highs
    if price_trend > 0 and indicator_trend < 0:
        return "BEARISH"

    return None
