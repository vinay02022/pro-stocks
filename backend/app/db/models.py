"""
SQLAlchemy models for StockPro database.

Uses SQLite for local persistence of:
- Price ticks (for historical analysis)
- User portfolios
- Trade journal
- AI trade ideas
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Tick(Base):
    """
    Store price ticks from WebSocket stream.
    Used for historical analysis and building OHLC candles.
    """
    __tablename__ = "ticks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Float, nullable=False)
    volume = Column(Integer, default=0)
    timestamp = Column(DateTime, nullable=False, index=True)
    source = Column(String(20), default="unknown")  # angel_one, upstox, yahoo

    # Composite index for efficient time-range queries
    __table_args__ = (
        Index("ix_ticks_symbol_timestamp", "symbol", "timestamp"),
    )


class Portfolio(Base):
    """
    User's stock holdings.
    Tracks entry prices, quantities, and calculated P&L.
    """
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, default="default", index=True)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(10), default="NSE")
    quantity = Column(Integer, nullable=False)
    avg_entry_price = Column(Float, nullable=False)
    entry_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Calculated fields (updated periodically)
    current_price = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, nullable=True)
    unrealized_pnl_percent = Column(Float, nullable=True)

    __table_args__ = (
        Index("ix_portfolio_user_symbol", "user_id", "symbol"),
    )


class Trade(Base):
    """
    Trade journal - records executed trades.
    Links to AI trade ideas that suggested them.
    """
    __tablename__ = "trades"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(50), nullable=False, default="default", index=True)
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), default="NSE")

    # Trade direction
    direction = Column(String(10), nullable=False)  # LONG, SHORT

    # Entry
    entry_price = Column(Float, nullable=False)
    entry_quantity = Column(Integer, nullable=False)
    entry_time = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Exit (null if still open)
    exit_price = Column(Float, nullable=True)
    exit_quantity = Column(Integer, nullable=True)
    exit_time = Column(DateTime, nullable=True)

    # Risk management
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)

    # Status
    status = Column(String(20), default="OPEN")  # OPEN, CLOSED, CANCELLED

    # Results (calculated on close)
    realized_pnl = Column(Float, nullable=True)
    realized_pnl_percent = Column(Float, nullable=True)

    # Link to AI suggestion (if any)
    trade_idea_id = Column(String(36), ForeignKey("trade_ideas.id"), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    trade_idea = relationship("TradeIdea", back_populates="trades")


class TradeIdea(Base):
    """
    AI-generated trade suggestions.
    Stored for analytics and model feedback.
    """
    __tablename__ = "trade_ideas"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    symbol = Column(String(20), nullable=False, index=True)
    exchange = Column(String(10), default="NSE")

    # Direction and timeframe
    direction = Column(String(10), nullable=False)  # LONG, SHORT, NEUTRAL
    timeframe = Column(String(20), nullable=False)  # INTRADAY, SWING, POSITIONAL

    # Confidence (stored as JSON for low/mid/high)
    confidence_band = Column(JSON, nullable=False)  # {"low": 0.55, "mid": 0.65, "high": 0.72}

    # Market regime
    regime = Column(JSON, nullable=True)  # {"trend": "BULLISH", "volatility": "NORMAL", ...}

    # Entry plan
    entry_type = Column(String(20), nullable=True)  # MARKET, LIMIT, STOP_LIMIT
    entry_price = Column(Float, nullable=True)
    entry_zone_low = Column(Float, nullable=True)
    entry_zone_high = Column(Float, nullable=True)

    # Risk management
    stop_loss = Column(Float, nullable=True)
    take_profit_1 = Column(Float, nullable=True)
    take_profit_2 = Column(Float, nullable=True)
    take_profit_3 = Column(Float, nullable=True)

    # AI reasoning (stored as JSON)
    reasoning = Column(JSON, nullable=True)  # {"primary_factors": [...], "concerns": [...]}

    # Invalidation condition
    invalidation = Column(Text, nullable=True)

    # Explanation
    summary = Column(Text, nullable=True)
    risk_disclosure = Column(Text, nullable=True)

    # User action
    status = Column(String(20), default="PENDING")  # PENDING, EXECUTED, SKIPPED, EXPIRED
    executed_at = Column(DateTime, nullable=True)
    skipped_at = Column(DateTime, nullable=True)
    skip_reason = Column(Text, nullable=True)

    # Outcome tracking (if executed)
    outcome_pnl = Column(Float, nullable=True)
    outcome_pnl_percent = Column(Float, nullable=True)
    outcome_hit_target = Column(Boolean, nullable=True)
    outcome_hit_stoploss = Column(Boolean, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship to trades
    trades = relationship("Trade", back_populates="trade_idea")


class CachedCandle(Base):
    """
    Aggregated OHLC candles cached from tick data.
    Used for fast chart loading.
    """
    __tablename__ = "cached_candles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)  # 1m, 5m, 15m, 1h, 1d
    timestamp = Column(DateTime, nullable=False)

    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_candles_symbol_tf_ts", "symbol", "timeframe", "timestamp"),
    )
