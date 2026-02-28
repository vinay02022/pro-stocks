"""
News API Endpoints

Get market news with sentiment analysis.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from app.services.news import get_news_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/market")
async def get_market_news(
    limit: int = Query(15, ge=1, le=50, description="Number of articles"),
):
    """
    Get general market news for Indian stock market.

    Returns news with sentiment analysis (bullish/bearish/neutral).
    """
    news_service = get_news_service()

    try:
        result = await news_service.get_trending_news(limit)
        return result

    except Exception as e:
        logger.error(f"Error fetching market news: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch news")


@router.get("/symbol/{symbol}")
async def get_symbol_news(
    symbol: str,
    limit: int = Query(10, ge=1, le=30, description="Number of articles"),
):
    """
    Get news for a specific stock symbol.

    Example: `/news/symbol/RELIANCE`
    """
    news_service = get_news_service()

    try:
        articles = await news_service.get_symbol_news(symbol.upper(), limit)

        # Calculate sentiment summary
        if articles:
            bullish = sum(1 for a in articles if a.sentiment.value in ["bullish", "very_bullish"])
            bearish = sum(1 for a in articles if a.sentiment.value in ["bearish", "very_bearish"])
            avg_score = sum(a.sentiment_score for a in articles) / len(articles)
        else:
            bullish = bearish = 0
            avg_score = 0

        return {
            "symbol": symbol.upper(),
            "count": len(articles),
            "sentiment_summary": {
                "bullish_count": bullish,
                "bearish_count": bearish,
                "neutral_count": len(articles) - bullish - bearish,
                "avg_score": round(avg_score, 2),
            },
            "articles": [a.to_dict() for a in articles],
        }

    except Exception as e:
        logger.error(f"Error fetching news for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch news")


@router.get("/sector/{sector}")
async def get_sector_news(
    sector: str,
    limit: int = Query(10, ge=1, le=30, description="Number of articles"),
):
    """
    Get news for a specific sector.

    Available sectors: banking, it, pharma, auto, fmcg, energy, metals
    """
    news_service = get_news_service()

    valid_sectors = ["banking", "it", "pharma", "auto", "fmcg", "energy", "metals"]

    if sector.lower() not in valid_sectors:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sector. Valid options: {valid_sectors}",
        )

    try:
        articles = await news_service.get_sector_news(sector.lower(), limit)

        if articles:
            bullish = sum(1 for a in articles if a.sentiment.value in ["bullish", "very_bullish"])
            bearish = sum(1 for a in articles if a.sentiment.value in ["bearish", "very_bearish"])
            avg_score = sum(a.sentiment_score for a in articles) / len(articles)
        else:
            bullish = bearish = 0
            avg_score = 0

        return {
            "sector": sector.lower(),
            "count": len(articles),
            "sentiment_summary": {
                "bullish_count": bullish,
                "bearish_count": bearish,
                "neutral_count": len(articles) - bullish - bearish,
                "avg_score": round(avg_score, 2),
            },
            "articles": [a.to_dict() for a in articles],
        }

    except Exception as e:
        logger.error(f"Error fetching news for sector {sector}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch news")


@router.get("/trending")
async def get_trending_news(
    limit: int = Query(20, ge=1, le=50, description="Number of articles"),
):
    """
    Get trending market news with overall market sentiment.

    Returns aggregated sentiment analysis across all news.
    """
    news_service = get_news_service()

    try:
        result = await news_service.get_trending_news(limit)
        return result

    except Exception as e:
        logger.error(f"Error fetching trending news: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch news")


@router.get("/sectors")
async def get_available_sectors():
    """
    Get list of available news sectors.
    """
    return {
        "sectors": [
            {"id": "banking", "name": "Banking & Finance", "description": "HDFC, ICICI, SBI, Axis, Kotak"},
            {"id": "it", "name": "Information Technology", "description": "TCS, Infosys, Wipro, HCL Tech"},
            {"id": "pharma", "name": "Pharmaceuticals", "description": "Sun Pharma, Cipla, Dr Reddy's"},
            {"id": "auto", "name": "Automobile", "description": "Maruti, Tata Motors, M&M, Hero"},
            {"id": "fmcg", "name": "FMCG", "description": "HUL, ITC, Nestle, Britannia"},
            {"id": "energy", "name": "Energy & Oil", "description": "Reliance, ONGC, BPCL, IOC"},
            {"id": "metals", "name": "Metals & Mining", "description": "Tata Steel, JSW, Hindalco"},
        ],
    }
