"""
Database connection and session management.

Uses SQLite with aiosqlite for async support.
"""

import os
import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.db.models import Base
from app.core.config import settings

logger = logging.getLogger(__name__)

# Database path - create data directory if needed
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# SQLite database URL
SQLITE_PATH = getattr(settings, "sqlite_path", None) or os.path.join(DATA_DIR, "stockpro.db")
DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_PATH}"

# Create async engine
# Note: SQLite requires check_same_thread=False for async
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Recommended for SQLite
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """
    Initialize the database - create all tables.
    Called on application startup.
    """
    try:
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"Database initialized at: {SQLITE_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db() -> None:
    """
    Close database connections.
    Called on application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides a database session.
    Use with FastAPI Depends().
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions.
    Use when not in a FastAPI route.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# CRUD helper functions

async def add_tick(session: AsyncSession, symbol: str, price: float, volume: int, timestamp, source: str = "unknown"):
    """Add a price tick to the database."""
    from app.db.models import Tick
    tick = Tick(
        symbol=symbol.upper(),
        price=price,
        volume=volume,
        timestamp=timestamp,
        source=source,
    )
    session.add(tick)
    await session.flush()
    return tick


async def get_portfolio(session: AsyncSession, user_id: str = "default"):
    """Get all portfolio holdings for a user."""
    from sqlalchemy import select
    from app.db.models import Portfolio

    result = await session.execute(
        select(Portfolio).where(Portfolio.user_id == user_id)
    )
    return result.scalars().all()


async def add_trade_idea(session: AsyncSession, idea_data: dict):
    """Store an AI trade idea."""
    from app.db.models import TradeIdea
    idea = TradeIdea(**idea_data)
    session.add(idea)
    await session.flush()
    return idea


async def get_recent_trade_ideas(session: AsyncSession, limit: int = 20):
    """Get recent trade ideas."""
    from sqlalchemy import select
    from app.db.models import TradeIdea

    result = await session.execute(
        select(TradeIdea)
        .order_by(TradeIdea.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def mark_idea_executed(session: AsyncSession, idea_id: str):
    """Mark a trade idea as executed."""
    from datetime import datetime
    from sqlalchemy import select
    from app.db.models import TradeIdea

    result = await session.execute(
        select(TradeIdea).where(TradeIdea.id == idea_id)
    )
    idea = result.scalar_one_or_none()
    if idea:
        idea.status = "EXECUTED"
        idea.executed_at = datetime.utcnow()
        await session.flush()
    return idea


async def mark_idea_skipped(session: AsyncSession, idea_id: str, reason: str = None):
    """Mark a trade idea as skipped."""
    from datetime import datetime
    from sqlalchemy import select
    from app.db.models import TradeIdea

    result = await session.execute(
        select(TradeIdea).where(TradeIdea.id == idea_id)
    )
    idea = result.scalar_one_or_none()
    if idea:
        idea.status = "SKIPPED"
        idea.skipped_at = datetime.utcnow()
        idea.skip_reason = reason
        await session.flush()
    return idea
