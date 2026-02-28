"""
Backtesting API Endpoints

Run and analyze trading strategy backtests.
"""

import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from app.services.backtest import get_backtest_engine, StrategyType
from app.schemas.market import Timeframe

logger = logging.getLogger(__name__)

router = APIRouter()


class BacktestRequest(BaseModel):
    """Request body for running a backtest."""
    symbol: str = Field(..., description="Stock symbol to backtest")
    strategy: str = Field(..., description="Strategy type: ema_crossover, rsi_reversal, breakout, macd")
    strategy_params: Optional[Dict[str, Any]] = Field(None, description="Strategy parameters")
    timeframe: str = Field("1d", description="Timeframe: 1m, 5m, 15m, 1h, 1d")
    initial_capital: float = Field(100000, ge=1000, description="Initial capital")
    position_size_percent: float = Field(100, ge=1, le=100, description="Position size as % of capital")
    stop_loss_enabled: bool = Field(True, description="Enable stop loss")
    take_profit_enabled: bool = Field(True, description="Enable take profit")
    lookback: int = Field(365, ge=30, le=1000, description="Number of bars to backtest")


@router.post("/run")
async def run_backtest(request: BacktestRequest):
    """
    Run a backtest with the specified strategy.

    Returns detailed performance metrics and trade history.

    Example request:
    ```json
    {
        "symbol": "RELIANCE",
        "strategy": "ema_crossover",
        "strategy_params": {"fast_period": 9, "slow_period": 21},
        "timeframe": "1d",
        "initial_capital": 100000
    }
    ```
    """
    engine = get_backtest_engine()

    # Validate strategy
    try:
        strategy_type = StrategyType(request.strategy.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy: {request.strategy}. Valid options: {[s.value for s in StrategyType]}",
        )

    # Parse timeframe
    tf_map = {
        "1m": Timeframe.M1,
        "5m": Timeframe.M5,
        "15m": Timeframe.M15,
        "1h": Timeframe.H1,
        "1d": Timeframe.D1,
        "1w": Timeframe.W1,
    }
    tf = tf_map.get(request.timeframe.lower(), Timeframe.D1)

    result = await engine.run(
        symbol=request.symbol.upper(),
        strategy_type=strategy_type,
        strategy_params=request.strategy_params,
        timeframe=tf,
        initial_capital=request.initial_capital,
        position_size_percent=request.position_size_percent,
        stop_loss_enabled=request.stop_loss_enabled,
        take_profit_enabled=request.take_profit_enabled,
        lookback=request.lookback,
    )

    if not result:
        raise HTTPException(status_code=400, detail=f"Backtest failed for {request.symbol}")

    return result.to_dict()


@router.get("/run/{symbol}")
async def run_quick_backtest(
    symbol: str,
    strategy: str = Query("ema_crossover", description="Strategy type"),
    timeframe: str = Query("1d", description="Timeframe"),
    capital: float = Query(100000, ge=1000, description="Initial capital"),
    lookback: int = Query(365, ge=30, le=1000, description="Lookback period"),
):
    """
    Quick backtest endpoint with URL parameters.

    Example:
    `/backtest/run/RELIANCE?strategy=ema_crossover&timeframe=1d&capital=100000`
    """
    engine = get_backtest_engine()

    try:
        strategy_type = StrategyType(strategy.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy: {strategy}",
        )

    tf_map = {
        "1m": Timeframe.M1,
        "5m": Timeframe.M5,
        "15m": Timeframe.M15,
        "1h": Timeframe.H1,
        "1d": Timeframe.D1,
    }
    tf = tf_map.get(timeframe.lower(), Timeframe.D1)

    result = await engine.run(
        symbol=symbol.upper(),
        strategy_type=strategy_type,
        timeframe=tf,
        initial_capital=capital,
        lookback=lookback,
    )

    if not result:
        raise HTTPException(status_code=400, detail=f"Backtest failed for {symbol}")

    return result.to_dict()


@router.get("/strategies")
async def get_available_strategies():
    """
    Get list of available backtesting strategies with their parameters.
    """
    return {
        "strategies": [
            {
                "id": "ema_crossover",
                "name": "EMA Crossover",
                "description": "Buy when fast EMA crosses above slow EMA. Sell on opposite cross.",
                "params": [
                    {"name": "fast_period", "type": "int", "default": 9, "description": "Fast EMA period"},
                    {"name": "slow_period", "type": "int", "default": 21, "description": "Slow EMA period"},
                    {"name": "atr_multiplier", "type": "float", "default": 2.0, "description": "ATR multiplier for stop loss"},
                ],
            },
            {
                "id": "rsi_reversal",
                "name": "RSI Reversal",
                "description": "Buy when RSI crosses above oversold. Sell when RSI crosses below overbought.",
                "params": [
                    {"name": "period", "type": "int", "default": 14, "description": "RSI period"},
                    {"name": "overbought", "type": "float", "default": 70, "description": "Overbought level"},
                    {"name": "oversold", "type": "float", "default": 30, "description": "Oversold level"},
                    {"name": "atr_multiplier", "type": "float", "default": 1.5, "description": "ATR multiplier for stop loss"},
                ],
            },
            {
                "id": "breakout",
                "name": "Breakout",
                "description": "Buy on breakout above resistance with volume. Sell on breakdown below support.",
                "params": [
                    {"name": "lookback", "type": "int", "default": 20, "description": "Lookback period for high/low"},
                    {"name": "volume_threshold", "type": "float", "default": 1.5, "description": "Volume spike threshold"},
                    {"name": "atr_multiplier", "type": "float", "default": 2.0, "description": "ATR multiplier for stop loss"},
                ],
            },
            {
                "id": "macd",
                "name": "MACD Crossover",
                "description": "Buy when MACD crosses above signal line. Sell on opposite cross.",
                "params": [
                    {"name": "fast_period", "type": "int", "default": 12, "description": "Fast EMA period"},
                    {"name": "slow_period", "type": "int", "default": 26, "description": "Slow EMA period"},
                    {"name": "signal_period", "type": "int", "default": 9, "description": "Signal line period"},
                    {"name": "atr_multiplier", "type": "float", "default": 2.0, "description": "ATR multiplier for stop loss"},
                ],
            },
        ],
    }


@router.get("/compare")
async def compare_strategies(
    symbol: str = Query(..., description="Stock symbol"),
    timeframe: str = Query("1d", description="Timeframe"),
    capital: float = Query(100000, description="Initial capital"),
    lookback: int = Query(365, description="Lookback period"),
):
    """
    Compare all strategies on a single symbol.

    Returns performance comparison across all available strategies.
    """
    engine = get_backtest_engine()

    tf_map = {
        "1m": Timeframe.M1,
        "5m": Timeframe.M5,
        "15m": Timeframe.M15,
        "1h": Timeframe.H1,
        "1d": Timeframe.D1,
    }
    tf = tf_map.get(timeframe.lower(), Timeframe.D1)

    results = []

    for strategy_type in StrategyType:
        result = await engine.run(
            symbol=symbol.upper(),
            strategy_type=strategy_type,
            timeframe=tf,
            initial_capital=capital,
            lookback=lookback,
        )

        if result:
            results.append({
                "strategy": strategy_type.value,
                "total_return_percent": result.total_return_percent,
                "win_rate": result.win_rate,
                "profit_factor": result.profit_factor,
                "max_drawdown_percent": result.max_drawdown_percent,
                "sharpe_ratio": result.sharpe_ratio,
                "total_trades": result.total_trades,
            })

    # Sort by total return
    results.sort(key=lambda x: x["total_return_percent"], reverse=True)

    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "initial_capital": capital,
        "comparison": results,
    }
