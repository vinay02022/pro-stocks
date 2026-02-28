"""
Backtesting Engine

Simulates trading strategies on historical data and calculates performance metrics.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from zoneinfo import ZoneInfo
import numpy as np

from app.services.backtest.strategies import (
    Strategy,
    Signal,
    SignalType,
    get_strategy,
)
from app.services.data_ingestion.service import DataIngestionService
from app.schemas.market import Timeframe

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


class StrategyType(str, Enum):
    """Available strategy types."""
    EMA_CROSSOVER = "ema_crossover"
    RSI_REVERSAL = "rsi_reversal"
    BREAKOUT = "breakout"
    MACD = "macd"


@dataclass
class Trade:
    """A completed trade."""
    entry_date: str
    entry_price: float
    exit_date: str
    exit_price: float
    direction: str  # LONG or SHORT
    quantity: int
    pnl: float
    pnl_percent: float
    hold_duration: int  # in bars
    exit_reason: str


@dataclass
class BacktestResult:
    """Complete backtest results."""
    symbol: str
    strategy: str
    strategy_params: Dict[str, Any]
    timeframe: str
    start_date: str
    end_date: str

    # Performance metrics
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_percent: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_percent: float
    sharpe_ratio: float
    avg_trade_pnl: float
    avg_winning_trade: float
    avg_losing_trade: float
    largest_win: float
    largest_loss: float
    avg_hold_duration: float

    # Trade history
    trades: List[Dict[str, Any]]

    # Equity curve
    equity_curve: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BacktestEngine:
    """
    Backtesting engine for simulating trading strategies.

    Usage:
        engine = BacktestEngine()
        result = await engine.run(
            symbol="RELIANCE",
            strategy_type=StrategyType.EMA_CROSSOVER,
            strategy_params={"fast_period": 9, "slow_period": 21},
            timeframe=Timeframe.D1,
            initial_capital=100000,
        )
    """

    def __init__(self):
        self._data_service = DataIngestionService()

    async def run(
        self,
        symbol: str,
        strategy_type: StrategyType,
        strategy_params: Dict[str, Any] = None,
        timeframe: Timeframe = Timeframe.D1,
        initial_capital: float = 100000,
        position_size_percent: float = 100,  # % of capital per trade
        stop_loss_enabled: bool = True,
        take_profit_enabled: bool = True,
        lookback: int = 365,
    ) -> Optional[BacktestResult]:
        """
        Run backtest on a symbol with given strategy.
        """
        try:
            # Fetch historical data
            data = await self._data_service.get_symbol_data(
                symbol=symbol,
                timeframe=timeframe,
                lookback=lookback,
            )

            if not data or len(data.ohlcv) < 50:
                logger.error(f"Insufficient data for backtesting {symbol}")
                return None

            # Convert to numpy arrays
            timestamps = [c.timestamp.isoformat() for c in data.ohlcv]
            opens = np.array([c.open for c in data.ohlcv])
            highs = np.array([c.high for c in data.ohlcv])
            lows = np.array([c.low for c in data.ohlcv])
            closes = np.array([c.close for c in data.ohlcv])
            volumes = np.array([c.volume for c in data.ohlcv])

            # Initialize strategy
            strategy = get_strategy(strategy_type.value, strategy_params)

            # Run simulation
            trades, equity_curve = self._simulate(
                timestamps=timestamps,
                opens=opens,
                highs=highs,
                lows=lows,
                closes=closes,
                volumes=volumes,
                strategy=strategy,
                initial_capital=initial_capital,
                position_size_percent=position_size_percent,
                stop_loss_enabled=stop_loss_enabled,
                take_profit_enabled=take_profit_enabled,
            )

            # Calculate metrics
            metrics = self._calculate_metrics(trades, equity_curve, initial_capital)

            return BacktestResult(
                symbol=symbol,
                strategy=strategy.name,
                strategy_params=strategy.get_params(),
                timeframe=timeframe.value,
                start_date=timestamps[0],
                end_date=timestamps[-1],
                initial_capital=initial_capital,
                final_capital=equity_curve[-1]["equity"] if equity_curve else initial_capital,
                total_return=metrics["total_return"],
                total_return_percent=metrics["total_return_percent"],
                total_trades=metrics["total_trades"],
                winning_trades=metrics["winning_trades"],
                losing_trades=metrics["losing_trades"],
                win_rate=metrics["win_rate"],
                profit_factor=metrics["profit_factor"],
                max_drawdown=metrics["max_drawdown"],
                max_drawdown_percent=metrics["max_drawdown_percent"],
                sharpe_ratio=metrics["sharpe_ratio"],
                avg_trade_pnl=metrics["avg_trade_pnl"],
                avg_winning_trade=metrics["avg_winning_trade"],
                avg_losing_trade=metrics["avg_losing_trade"],
                largest_win=metrics["largest_win"],
                largest_loss=metrics["largest_loss"],
                avg_hold_duration=metrics["avg_hold_duration"],
                trades=[asdict(t) for t in trades],
                equity_curve=equity_curve,
            )

        except Exception as e:
            logger.error(f"Backtest error for {symbol}: {e}")
            return None

    def _simulate(
        self,
        timestamps: List[str],
        opens: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        volumes: np.ndarray,
        strategy: Strategy,
        initial_capital: float,
        position_size_percent: float,
        stop_loss_enabled: bool,
        take_profit_enabled: bool,
    ) -> tuple[List[Trade], List[Dict[str, Any]]]:
        """
        Simulate trading on historical data.
        """
        trades = []
        equity_curve = []

        capital = initial_capital
        position = 0  # 1=long, -1=short, 0=flat
        entry_price = 0.0
        entry_date = ""
        entry_idx = 0
        stop_loss = 0.0
        take_profit = 0.0
        quantity = 0

        for idx in range(len(closes)):
            current_price = closes[idx]
            current_date = timestamps[idx]

            # Check stop loss / take profit
            if position != 0:
                exit_triggered = False
                exit_reason = ""
                exit_price = current_price

                if position == 1:  # Long position
                    if stop_loss_enabled and lows[idx] <= stop_loss:
                        exit_triggered = True
                        exit_price = stop_loss
                        exit_reason = "Stop loss hit"
                    elif take_profit_enabled and highs[idx] >= take_profit:
                        exit_triggered = True
                        exit_price = take_profit
                        exit_reason = "Take profit hit"
                elif position == -1:  # Short position
                    if stop_loss_enabled and highs[idx] >= stop_loss:
                        exit_triggered = True
                        exit_price = stop_loss
                        exit_reason = "Stop loss hit"
                    elif take_profit_enabled and lows[idx] <= take_profit:
                        exit_triggered = True
                        exit_price = take_profit
                        exit_reason = "Take profit hit"

                if exit_triggered:
                    # Close position
                    if position == 1:
                        pnl = (exit_price - entry_price) * quantity
                    else:
                        pnl = (entry_price - exit_price) * quantity

                    pnl_percent = (pnl / (entry_price * quantity)) * 100

                    trades.append(Trade(
                        entry_date=entry_date,
                        entry_price=entry_price,
                        exit_date=current_date,
                        exit_price=exit_price,
                        direction="LONG" if position == 1 else "SHORT",
                        quantity=quantity,
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        hold_duration=idx - entry_idx,
                        exit_reason=exit_reason,
                    ))

                    capital += pnl
                    position = 0
                    quantity = 0

            # Generate signal if flat or looking for exit
            signal = strategy.generate_signal(idx, opens, highs, lows, closes, volumes, position)

            # Execute signal
            if signal.signal_type == SignalType.BUY and position <= 0:
                # Close short position if any
                if position == -1:
                    pnl = (entry_price - current_price) * quantity
                    pnl_percent = (pnl / (entry_price * quantity)) * 100

                    trades.append(Trade(
                        entry_date=entry_date,
                        entry_price=entry_price,
                        exit_date=current_date,
                        exit_price=current_price,
                        direction="SHORT",
                        quantity=quantity,
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        hold_duration=idx - entry_idx,
                        exit_reason=signal.reason,
                    ))
                    capital += pnl

                # Open long position
                position_value = capital * (position_size_percent / 100)
                quantity = int(position_value / current_price)
                if quantity > 0:
                    position = 1
                    entry_price = current_price
                    entry_date = current_date
                    entry_idx = idx
                    stop_loss = signal.stop_loss or (current_price * 0.95)
                    take_profit = signal.take_profit or (current_price * 1.10)

            elif signal.signal_type == SignalType.SELL and position >= 0:
                # Close long position if any
                if position == 1:
                    pnl = (current_price - entry_price) * quantity
                    pnl_percent = (pnl / (entry_price * quantity)) * 100

                    trades.append(Trade(
                        entry_date=entry_date,
                        entry_price=entry_price,
                        exit_date=current_date,
                        exit_price=current_price,
                        direction="LONG",
                        quantity=quantity,
                        pnl=pnl,
                        pnl_percent=pnl_percent,
                        hold_duration=idx - entry_idx,
                        exit_reason=signal.reason,
                    ))
                    capital += pnl

                # Open short position (if enabled)
                position_value = capital * (position_size_percent / 100)
                quantity = int(position_value / current_price)
                if quantity > 0:
                    position = -1
                    entry_price = current_price
                    entry_date = current_date
                    entry_idx = idx
                    stop_loss = signal.stop_loss or (current_price * 1.05)
                    take_profit = signal.take_profit or (current_price * 0.90)

            # Calculate current equity
            if position == 1:
                unrealized_pnl = (current_price - entry_price) * quantity
            elif position == -1:
                unrealized_pnl = (entry_price - current_price) * quantity
            else:
                unrealized_pnl = 0

            equity_curve.append({
                "date": current_date,
                "price": current_price,
                "equity": capital + unrealized_pnl,
                "position": position,
            })

        # Close any open position at the end
        if position != 0:
            current_price = closes[-1]
            current_date = timestamps[-1]

            if position == 1:
                pnl = (current_price - entry_price) * quantity
            else:
                pnl = (entry_price - current_price) * quantity

            pnl_percent = (pnl / (entry_price * quantity)) * 100 if entry_price > 0 else 0

            trades.append(Trade(
                entry_date=entry_date,
                entry_price=entry_price,
                exit_date=current_date,
                exit_price=current_price,
                direction="LONG" if position == 1 else "SHORT",
                quantity=quantity,
                pnl=pnl,
                pnl_percent=pnl_percent,
                hold_duration=len(closes) - 1 - entry_idx,
                exit_reason="End of backtest period",
            ))

        return trades, equity_curve

    def _calculate_metrics(
        self,
        trades: List[Trade],
        equity_curve: List[Dict[str, Any]],
        initial_capital: float,
    ) -> Dict[str, float]:
        """
        Calculate performance metrics from trades and equity curve.
        """
        if not trades:
            return {
                "total_return": 0,
                "total_return_percent": 0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "max_drawdown": 0,
                "max_drawdown_percent": 0,
                "sharpe_ratio": 0,
                "avg_trade_pnl": 0,
                "avg_winning_trade": 0,
                "avg_losing_trade": 0,
                "largest_win": 0,
                "largest_loss": 0,
                "avg_hold_duration": 0,
            }

        # Basic stats
        pnls = [t.pnl for t in trades]
        winning_pnls = [p for p in pnls if p > 0]
        losing_pnls = [p for p in pnls if p < 0]

        total_trades = len(trades)
        winning_trades = len(winning_pnls)
        losing_trades = len(losing_pnls)

        total_return = sum(pnls)
        total_return_percent = (total_return / initial_capital) * 100

        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

        # Profit factor
        gross_profit = sum(winning_pnls) if winning_pnls else 0
        gross_loss = abs(sum(losing_pnls)) if losing_pnls else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else gross_profit

        # Max drawdown
        equity_values = [e["equity"] for e in equity_curve]
        peak = equity_values[0]
        max_drawdown = 0
        max_drawdown_percent = 0

        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = peak - equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_percent = (drawdown / peak) * 100

        # Sharpe ratio (simplified, using daily returns)
        if len(equity_values) > 1:
            returns = np.diff(equity_values) / equity_values[:-1]
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = (avg_return / std_return) * np.sqrt(252) if std_return > 0 else 0
        else:
            sharpe_ratio = 0

        # Average stats
        avg_trade_pnl = np.mean(pnls) if pnls else 0
        avg_winning_trade = np.mean(winning_pnls) if winning_pnls else 0
        avg_losing_trade = np.mean(losing_pnls) if losing_pnls else 0
        largest_win = max(winning_pnls) if winning_pnls else 0
        largest_loss = min(losing_pnls) if losing_pnls else 0
        avg_hold_duration = np.mean([t.hold_duration for t in trades])

        return {
            "total_return": round(total_return, 2),
            "total_return_percent": round(total_return_percent, 2),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown": round(max_drawdown, 2),
            "max_drawdown_percent": round(max_drawdown_percent, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "avg_trade_pnl": round(avg_trade_pnl, 2),
            "avg_winning_trade": round(avg_winning_trade, 2),
            "avg_losing_trade": round(avg_losing_trade, 2),
            "largest_win": round(largest_win, 2),
            "largest_loss": round(largest_loss, 2),
            "avg_hold_duration": round(avg_hold_duration, 1),
        }


# Singleton instance
_engine: Optional[BacktestEngine] = None


def get_backtest_engine() -> BacktestEngine:
    """Get the backtest engine singleton."""
    global _engine
    if _engine is None:
        _engine = BacktestEngine()
    return _engine
