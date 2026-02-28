"""
Market Data API Endpoints

Endpoints for fetching market data.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from app.schemas.market import (
    DataRequest,
    MarketSnapshot,
    Timeframe,
)
from app.services.data_ingestion import get_data_ingestion_service
from app.services.data_ingestion.stock_list import (
    search_stocks,
    get_popular_stocks,
    get_stocks_by_sector,
)
from app.core.market_hours import get_market_status, get_upcoming_expiries

router = APIRouter()


@router.post("/snapshot", response_model=MarketSnapshot)
async def get_market_snapshot(request: DataRequest):
    """
    Fetch market data snapshot.

    Returns OHLCV data, optionally with options chain and news.
    """
    service = get_data_ingestion_service()
    result = await service.execute(request)

    if result.errors and not result.snapshot.symbols:
        raise HTTPException(
            status_code=500,
            detail={"message": "Failed to fetch data", "errors": result.errors},
        )

    return result.snapshot


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """
    Get quick quote for a single symbol.

    Returns current price, change, and basic info.
    """
    service = get_data_ingestion_service()
    quote = await service.get_quote(symbol.upper())

    if quote is None:
        raise HTTPException(status_code=404, detail=f"Quote not found for {symbol}")

    return quote


@router.get("/quotes")
async def get_quotes(symbols: str = Query(..., description="Comma-separated symbols")):
    """
    Get quotes for multiple symbols.
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    service = get_data_ingestion_service()

    quotes = []
    for symbol in symbol_list:
        quote = await service.get_quote(symbol)
        if quote:
            quotes.append(quote)

    return {"quotes": quotes}


@router.get("/ohlcv/{symbol}")
async def get_ohlcv(
    symbol: str,
    timeframe: Timeframe = Timeframe.M15,
    lookback: int = Query(default=100, ge=1, le=1000),
):
    """
    Get OHLCV candles for a symbol.
    """
    service = get_data_ingestion_service()
    request = DataRequest(
        symbols=[symbol.upper()],
        timeframe=timeframe,
        lookback=lookback,
    )
    result = await service.execute(request)

    if not result.snapshot.symbols:
        raise HTTPException(status_code=404, detail=f"Data not found for {symbol}")

    symbol_data = result.snapshot.symbols[0]
    return {
        "symbol": symbol_data.symbol,
        "timeframe": symbol_data.timeframe,
        "candles": [c.model_dump() for c in symbol_data.ohlcv],
        "current_price": symbol_data.current_price,
        "day_change_percent": symbol_data.day_change_percent,
    }


@router.get("/options/{underlying}")
async def get_options_chain(
    underlying: str,
    expiry: Optional[str] = Query(default=None, description="Expiry date YYYY-MM-DD"),
):
    """
    Get options chain for an underlying.
    """
    service = get_data_ingestion_service()
    request = DataRequest(
        symbols=[underlying.upper()],
        include_options=True,
        options_expiry=expiry,
        lookback=1,  # Minimal OHLCV needed
    )
    result = await service.execute(request)

    if not result.snapshot.options_chain:
        raise HTTPException(
            status_code=404, detail=f"Options chain not found for {underlying}"
        )

    return result.snapshot.options_chain.model_dump()


@router.get("/news")
async def get_news(
    symbols: Optional[str] = Query(default=None, description="Comma-separated symbols"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Get market news, optionally filtered by symbols.
    """
    symbol_list = (
        [s.strip().upper() for s in symbols.split(",")] if symbols else []
    )

    service = get_data_ingestion_service()
    request = DataRequest(
        symbols=symbol_list or ["NIFTY"],  # Default to market news
        include_news=True,
        lookback=1,
    )
    result = await service.execute(request)

    news = result.snapshot.news or []
    return {"news": [n.model_dump() for n in news[:limit]]}


@router.get("/status")
async def get_market_status_endpoint():
    """
    Get current market status (open/closed, session, next open time).
    """
    status = get_market_status()
    status["upcoming_expiries"] = get_upcoming_expiries(4)
    return status


@router.get("/health")
async def check_data_health():
    """
    Check health of data ingestion service.
    """
    service = get_data_ingestion_service()
    is_healthy = await service.health_check()

    return {
        "service": "DataIngestionService",
        "healthy": is_healthy,
        "multi_source_enabled": service._use_multi_source,
        "mock_fallback_enabled": service._use_mock_fallback,
    }


@router.get("/sources")
async def get_data_sources():
    """
    Get status of all data sources (Yahoo Finance, Angel One, etc.).

    Returns detailed connectivity info for each source.
    """
    service = get_data_ingestion_service()
    status = await service.get_data_sources_status()
    return status


@router.get("/search")
async def search_stocks_endpoint(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=10, ge=1, le=50),
):
    """
    Search stocks by symbol or name.

    Returns matching stocks for autocomplete.
    """
    results = search_stocks(q, limit)
    return {"query": q, "results": results, "count": len(results)}


@router.get("/popular")
async def get_popular_stocks_endpoint(
    count: int = Query(default=10, ge=1, le=20),
):
    """
    Get popular stocks with live quotes.

    Returns top stocks with current prices.
    """
    stocks = get_popular_stocks(count)
    service = get_data_ingestion_service()

    # Enrich with live quotes
    enriched = []
    for stock in stocks:
        try:
            quote = await service.get_quote(stock["symbol"])
            if quote:
                enriched.append({
                    **stock,
                    "price": quote.get("price", 0),
                    "change_percent": quote.get("change_percent", 0),
                    "volume": quote.get("volume", 0),
                })
            else:
                enriched.append(stock)
        except Exception:
            enriched.append(stock)

    return {"stocks": enriched}


@router.get("/sectors")
async def get_sectors():
    """Get list of available sectors."""
    from app.services.data_ingestion.stock_list import NSE_STOCKS

    sectors = list(set(s["sector"] for s in NSE_STOCKS if s["sector"] != "Index"))
    return {"sectors": sorted(sectors)}


@router.get("/sector/{sector}")
async def get_stocks_by_sector_endpoint(sector: str):
    """Get all stocks in a specific sector."""
    stocks = get_stocks_by_sector(sector)
    if not stocks:
        raise HTTPException(status_code=404, detail=f"Sector '{sector}' not found")
    return {"sector": sector, "stocks": stocks, "count": len(stocks)}


@router.get("/movers")
async def get_top_movers(
    count: int = Query(default=10, ge=1, le=20),
):
    """
    Get top gainers and losers with live data.

    Much faster than recommendations - just fetches quotes, no AI analysis.
    Use this to pre-filter before running full analysis.
    """
    import asyncio

    stocks = get_popular_stocks(15)
    service = get_data_ingestion_service()

    movers = []

    # Fetch quotes in parallel for speed
    async def fetch_quote(stock):
        try:
            quote = await service.get_quote(stock["symbol"])
            if quote:
                return {
                    **stock,
                    "price": quote.get("price", 0),
                    "change_percent": quote.get("change_percent", 0),
                    "volume": quote.get("volume", 0),
                    "previous_close": quote.get("previous_close", 0),
                }
        except Exception:
            pass
        return None

    # Fetch all quotes concurrently
    results = await asyncio.gather(*[fetch_quote(s) for s in stocks])
    movers = [r for r in results if r is not None]

    # Sort by absolute change percent
    movers.sort(key=lambda x: abs(x.get("change_percent", 0)), reverse=True)

    # Separate gainers and losers
    gainers = [m for m in movers if m.get("change_percent", 0) > 0][:count]
    losers = [m for m in movers if m.get("change_percent", 0) < 0][:count]

    # Top by volume
    by_volume = sorted(movers, key=lambda x: x.get("volume", 0), reverse=True)[:count]

    return {
        "gainers": gainers,
        "losers": losers,
        "high_volume": by_volume,
        "all_movers": movers[:count],
    }
