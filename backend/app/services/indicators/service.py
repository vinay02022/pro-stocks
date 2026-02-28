"""
Indicator Engine Service Implementation

Calculates all technical indicators from OHLCV data.
NO LLM INVOLVEMENT - Pure Python/NumPy calculations.
"""

from datetime import datetime
from typing import Optional
import numpy as np

from app.schemas.market import MarketSnapshot, SymbolData, OHLCV
from app.schemas.indicators import (
    IndicatorOutput,
    PriceData,
    TrendIndicators,
    MomentumIndicators,
    VolatilityIndicators,
    VolumeIndicators,
    Levels,
    RiskMetrics,
    MACDData,
    StochasticData,
    BollingerBandsData,
    PivotPoints,
    PositionSizing,
    PositionSizingMethod,
    TrendDirection,
    VolatilityZone,
    SignalType,
)
from app.services.indicators.interface import IndicatorServiceInterface
from app.services.indicators.calculations import (
    sma,
    ema,
    rsi,
    macd,
    stochastic,
    cci,
    williams_r,
    mfi,
    atr,
    bollinger_bands,
    vwap,
    obv,
    adx,
    find_pivot_points,
    find_support_resistance,
    get_last_valid,
    detect_divergence,
)


def _ohlcv_to_arrays(candles: list[OHLCV]) -> tuple:
    """Convert OHLCV list to numpy arrays."""
    opens = np.array([c.open for c in candles])
    highs = np.array([c.high for c in candles])
    lows = np.array([c.low for c in candles])
    closes = np.array([c.close for c in candles])
    volumes = np.array([c.volume for c in candles])
    return opens, highs, lows, closes, volumes


class IndicatorService(IndicatorServiceInterface):
    """
    Indicator Engine Service.

    Calculates technical indicators for market analysis.
    All calculations are deterministic and reproducible.
    """

    @property
    def name(self) -> str:
        return "IndicatorService"

    async def execute(
        self, input_data: MarketSnapshot
    ) -> dict[str, IndicatorOutput]:
        """Calculate indicators for all symbols in snapshot."""
        results = {}

        for symbol_data in input_data.symbols:
            try:
                output = await self.calculate_for_symbol(symbol_data)
                results[symbol_data.symbol] = output
            except Exception as e:
                # Log error but continue with other symbols
                print(f"Error calculating indicators for {symbol_data.symbol}: {e}")

        return results

    async def calculate_for_symbol(
        self,
        symbol_data: SymbolData,
        portfolio_value: Optional[float] = None,
        risk_percent: float = 1.0,
    ) -> IndicatorOutput:
        """Calculate all indicators for a single symbol."""
        if not symbol_data.ohlcv or len(symbol_data.ohlcv) < 20:
            raise ValueError(f"Insufficient data for {symbol_data.symbol}")

        candles = symbol_data.ohlcv
        opens, highs, lows, closes, volumes = _ohlcv_to_arrays(candles)

        current = closes[-1]
        prev_close = closes[-2] if len(closes) > 1 else current

        # Calculate all indicators
        trend = self._calculate_trend_indicators(closes, highs, lows)
        momentum = self._calculate_momentum_indicators(closes, highs, lows, volumes)
        volatility = self._calculate_volatility_indicators(closes, highs, lows)
        volume = self._calculate_volume_indicators(highs, lows, closes, volumes)
        levels = self._calculate_levels(highs, lows, closes)
        risk_metrics = self._calculate_risk_metrics(
            current, highs, lows, closes, portfolio_value, risk_percent
        )

        # Build price data
        price_data = PriceData(
            current=current,
            open=opens[-1],
            high=highs[-1],
            low=lows[-1],
            previous_close=prev_close,
            change=current - prev_close,
            change_percent=((current - prev_close) / prev_close) * 100,
            volume=int(volumes[-1]),
            avg_volume=int(np.mean(volumes[-20:])) if len(volumes) >= 20 else None,
        )

        return IndicatorOutput(
            symbol=symbol_data.symbol,
            timestamp=datetime.now(),
            price=price_data,
            indicators={
                "trend": trend.model_dump(),
                "momentum": momentum.model_dump(),
                "volatility": volatility.model_dump(),
                "volume": volume.model_dump(),
            },
            levels=levels,
            risk_metrics=risk_metrics,
        )

    def _calculate_trend_indicators(
        self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray
    ) -> TrendIndicators:
        """Calculate trend indicators."""
        # Moving averages
        ema_9 = get_last_valid(ema(closes, 9)) or closes[-1]
        ema_21 = get_last_valid(ema(closes, 21)) or closes[-1]
        ema_50 = get_last_valid(ema(closes, 50)) or closes[-1]
        ema_200 = get_last_valid(ema(closes, 200)) or closes[-1]
        sma_20 = get_last_valid(sma(closes, 20)) or closes[-1]
        sma_50 = get_last_valid(sma(closes, 50)) or closes[-1]
        sma_200 = get_last_valid(sma(closes, 200)) or closes[-1]

        # ADX
        adx_arr, plus_di_arr, minus_di_arr = adx(highs, lows, closes, 14)
        adx_val = get_last_valid(adx_arr)
        plus_di = get_last_valid(plus_di_arr)
        minus_di = get_last_valid(minus_di_arr)

        # Determine trend direction
        current = closes[-1]
        if current > ema_21 and current > ema_50 and ema_21 > ema_50:
            direction = TrendDirection.BULLISH
        elif current < ema_21 and current < ema_50 and ema_21 < ema_50:
            direction = TrendDirection.BEARISH
        else:
            direction = TrendDirection.SIDEWAYS

        # Trend strength from ADX
        strength = adx_val if adx_val else 25.0

        return TrendIndicators(
            ema_9=round(ema_9, 2),
            ema_21=round(ema_21, 2),
            ema_50=round(ema_50, 2),
            ema_200=round(ema_200, 2),
            sma_20=round(sma_20, 2),
            sma_50=round(sma_50, 2),
            sma_200=round(sma_200, 2),
            trend_direction=direction,
            trend_strength=round(strength, 1),
            adx=round(adx_val, 2) if adx_val else None,
            plus_di=round(plus_di, 2) if plus_di else None,
            minus_di=round(minus_di, 2) if minus_di else None,
        )

    def _calculate_momentum_indicators(
        self,
        closes: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        volumes: np.ndarray,
    ) -> MomentumIndicators:
        """Calculate momentum indicators."""
        # RSI
        rsi_arr = rsi(closes, 14)
        rsi_val = get_last_valid(rsi_arr) or 50.0
        rsi_div = detect_divergence(closes, rsi_arr)
        # Map divergence to signal type: BULLISH->BUY, BEARISH->SELL
        if rsi_div == "BULLISH":
            rsi_divergence = SignalType.BUY
        elif rsi_div == "BEARISH":
            rsi_divergence = SignalType.SELL
        else:
            rsi_divergence = None

        # MACD
        macd_line, signal_line, histogram = macd(closes, 12, 26, 9)
        macd_val = get_last_valid(macd_line) or 0.0
        signal_val = get_last_valid(signal_line) or 0.0
        hist_val = get_last_valid(histogram) or 0.0

        # MACD crossover
        if len(histogram) >= 2:
            prev_hist = histogram[-2] if not np.isnan(histogram[-2]) else 0
            if hist_val > 0 and prev_hist <= 0:
                crossover = SignalType.BUY
            elif hist_val < 0 and prev_hist >= 0:
                crossover = SignalType.SELL
            else:
                crossover = SignalType.NEUTRAL
        else:
            crossover = None

        macd_data = MACDData(
            macd_line=round(macd_val, 2),
            signal_line=round(signal_val, 2),
            histogram=round(hist_val, 2),
            crossover=crossover,
        )

        # Stochastic
        k_arr, d_arr = stochastic(highs, lows, closes, 14, 3)
        k_val = get_last_valid(k_arr)
        d_val = get_last_valid(d_arr)

        if k_val is not None and d_val is not None:
            if k_val > 80:
                zone = "OVERBOUGHT"
            elif k_val < 20:
                zone = "OVERSOLD"
            else:
                zone = "NEUTRAL"

            stoch_data = StochasticData(
                k=round(k_val, 2), d=round(d_val, 2), zone=zone
            )
        else:
            stoch_data = None

        # Other momentum indicators
        cci_val = get_last_valid(cci(highs, lows, closes, 20))
        williams_val = get_last_valid(williams_r(highs, lows, closes, 14))
        mfi_val = get_last_valid(mfi(highs, lows, closes, volumes, 14))

        return MomentumIndicators(
            rsi_14=round(rsi_val, 2),
            rsi_divergence=rsi_divergence,
            macd=macd_data,
            stochastic=stoch_data,
            cci=round(cci_val, 2) if cci_val else None,
            mfi=round(mfi_val, 2) if mfi_val else None,
            williams_r=round(williams_val, 2) if williams_val else None,
        )

    def _calculate_volatility_indicators(
        self, closes: np.ndarray, highs: np.ndarray, lows: np.ndarray
    ) -> VolatilityIndicators:
        """Calculate volatility indicators."""
        # ATR
        atr_arr = atr(highs, lows, closes, 14)
        atr_val = get_last_valid(atr_arr) or 0.0
        atr_pct = (atr_val / closes[-1]) * 100 if closes[-1] > 0 else 0

        # Bollinger Bands
        upper, middle, lower, bandwidth, percent_b = bollinger_bands(closes, 20, 2.0)

        bb_data = BollingerBandsData(
            upper=round(get_last_valid(upper) or closes[-1], 2),
            middle=round(get_last_valid(middle) or closes[-1], 2),
            lower=round(get_last_valid(lower) or closes[-1], 2),
            bandwidth=round(get_last_valid(bandwidth) or 0, 4),
            percent_b=round(get_last_valid(percent_b) or 0.5, 4),
        )

        # Historical volatility (20-day)
        if len(closes) >= 20:
            returns = np.diff(np.log(closes[-21:]))
            hv = np.std(returns) * np.sqrt(252) * 100  # Annualized
        else:
            hv = None

        return VolatilityIndicators(
            atr_14=round(atr_val, 2),
            atr_percent=round(atr_pct, 2),
            bollinger_bands=bb_data,
            historical_volatility=round(hv, 2) if hv else None,
        )

    def _calculate_volume_indicators(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
    ) -> VolumeIndicators:
        """Calculate volume indicators."""
        current_vol = int(volumes[-1])
        avg_vol_20 = int(np.mean(volumes[-20:])) if len(volumes) >= 20 else current_vol

        vwap_arr = vwap(highs, lows, closes, volumes)
        vwap_val = get_last_valid(vwap_arr) or closes[-1]
        vwap_dev = ((closes[-1] - vwap_val) / vwap_val) * 100 if vwap_val > 0 else 0

        obv_arr = obv(closes, volumes)
        obv_val = int(get_last_valid(obv_arr) or 0)

        return VolumeIndicators(
            current_volume=current_vol,
            avg_volume_20=avg_vol_20,
            volume_ratio=round(current_vol / avg_vol_20, 2) if avg_vol_20 > 0 else 1.0,
            vwap=round(vwap_val, 2),
            vwap_deviation=round(vwap_dev, 2),
            obv=obv_val,
        )

    def _calculate_levels(
        self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray
    ) -> Levels:
        """Calculate support/resistance levels."""
        # Pivot points (using previous day's data)
        prev_high = highs[-2] if len(highs) > 1 else highs[-1]
        prev_low = lows[-2] if len(lows) > 1 else lows[-1]
        prev_close = closes[-2] if len(closes) > 1 else closes[-1]

        pivots = find_pivot_points(prev_high, prev_low, prev_close)

        # Support/resistance from local minima/maxima
        support, resistance = find_support_resistance(highs, lows, closes, 50)

        return Levels(
            support=support or [round(pivots["s1"], 2), round(pivots["s2"], 2)],
            resistance=resistance
            or [round(pivots["r1"], 2), round(pivots["r2"], 2)],
            pivot_points=PivotPoints(**pivots),
            day_high=round(float(highs[-1]), 2),
            day_low=round(float(lows[-1]), 2),
        )

    def _calculate_risk_metrics(
        self,
        current_price: float,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        portfolio_value: Optional[float],
        risk_percent: float,
    ) -> RiskMetrics:
        """Calculate risk metrics and position sizing."""
        # ATR for stop loss
        atr_arr = atr(highs, lows, closes, 14)
        atr_val = get_last_valid(atr_arr) or (current_price * 0.02)
        atr_pct = (atr_val / current_price) * 100

        # Suggested stop loss (1.5 * ATR below current)
        sl_distance = 1.5 * atr_val
        suggested_sl = current_price - sl_distance
        sl_percent = (sl_distance / current_price) * 100

        # Take profit targets (1:1.5, 1:2.5, 1:3.5 R:R)
        suggested_tp = [
            round(current_price + (sl_distance * 1.5), 2),
            round(current_price + (sl_distance * 2.5), 2),
            round(current_price + (sl_distance * 3.5), 2),
        ]
        rr_ratios = [1.5, 2.5, 3.5]

        # Position sizing
        if portfolio_value:
            risk_amount = portfolio_value * (risk_percent / 100)
            shares = int(risk_amount / sl_distance) if sl_distance > 0 else 0
            position_value = shares * current_price
        else:
            risk_amount = 0
            shares = 0
            position_value = 0

        position_sizing = PositionSizing(
            recommended_shares=shares,
            recommended_value=round(position_value, 2),
            risk_amount=round(risk_amount, 2),
            risk_percent=risk_percent,
            method=PositionSizingMethod.ATR,
        )

        # Volatility zone
        if atr_pct < 1.0:
            vol_zone = VolatilityZone.LOW
        elif atr_pct < 2.5:
            vol_zone = VolatilityZone.NORMAL
        elif atr_pct < 4.0:
            vol_zone = VolatilityZone.HIGH
        else:
            vol_zone = VolatilityZone.EXTREME

        return RiskMetrics(
            atr=round(atr_val, 2),
            atr_percent=round(atr_pct, 2),
            suggested_sl=round(suggested_sl, 2),
            suggested_sl_percent=round(sl_percent, 2),
            suggested_tp=suggested_tp,
            risk_reward_ratios=rr_ratios,
            position_sizing=position_sizing,
            volatility_zone=vol_zone,
        )

    async def health_check(self) -> bool:
        """Indicator service is always healthy (pure computation)."""
        return True


# Singleton instance
_service_instance: Optional[IndicatorService] = None


def get_indicator_service() -> IndicatorService:
    """Get or create indicator service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = IndicatorService()
    return _service_instance
