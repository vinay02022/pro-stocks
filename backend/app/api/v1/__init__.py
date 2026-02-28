"""
API v1 Router

All API endpoints for the frontend.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import market, indicators, strategy, portfolio, stream, auth, scanner, backtest, news

router = APIRouter()

# Include all endpoint routers
router.include_router(market.router, prefix="/market", tags=["Market Data"])
router.include_router(indicators.router, prefix="/indicators", tags=["Indicators"])
router.include_router(strategy.router, prefix="/strategy", tags=["Strategy"])
router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
router.include_router(stream.router, prefix="/stream", tags=["Real-Time Streaming"])
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(scanner.router, prefix="/scanner", tags=["Market Scanner"])
router.include_router(backtest.router, prefix="/backtest", tags=["Backtesting"])
router.include_router(news.router, prefix="/news", tags=["News & Sentiment"])
