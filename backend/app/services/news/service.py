"""
News Service

Fetches market news from free sources and performs basic sentiment analysis.
"""

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum
from zoneinfo import ZoneInfo
import aiohttp
from urllib.parse import quote_plus

from app.core.config import settings
from app.services.cache.redis_client import get_price_cache

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


class NewsSentiment(str, Enum):
    """News sentiment classification."""
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


@dataclass
class NewsArticle:
    """A news article."""
    title: str
    source: str
    url: str
    published_at: str
    summary: Optional[str] = None
    sentiment: NewsSentiment = NewsSentiment.NEUTRAL
    sentiment_score: float = 0.0  # -1 to 1
    related_symbols: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["sentiment"] = self.sentiment.value
        return d


# Keywords for sentiment analysis
BULLISH_KEYWORDS = [
    "surge", "surges", "surging", "soar", "soars", "soaring",
    "rally", "rallies", "rallying", "gain", "gains", "gaining",
    "rise", "rises", "rising", "jump", "jumps", "jumping",
    "breakout", "breakthrough", "upgrade", "upgrades", "upgraded",
    "outperform", "buy", "bullish", "positive", "strong",
    "growth", "profit", "profits", "profitable", "beat", "beats",
    "record", "high", "highs", "all-time", "boom", "booming",
    "expand", "expansion", "exceeds", "exceeded", "optimistic",
]

BEARISH_KEYWORDS = [
    "fall", "falls", "falling", "drop", "drops", "dropping",
    "decline", "declines", "declining", "crash", "crashes", "crashing",
    "plunge", "plunges", "plunging", "sink", "sinks", "sinking",
    "sell", "sells", "selling", "selloff", "downgrade", "downgrades",
    "underperform", "bearish", "negative", "weak", "weakness",
    "loss", "losses", "losing", "miss", "misses", "missed",
    "low", "lows", "slump", "slumps", "warning", "warns",
    "concern", "concerns", "worried", "fear", "fears", "risk",
    "cut", "cuts", "cutting", "layoff", "layoffs", "shutdown",
]

# Stock symbol to company name mapping for search
SYMBOL_NAMES = {
    "RELIANCE": "Reliance Industries",
    "TCS": "TCS Tata Consultancy",
    "HDFCBANK": "HDFC Bank",
    "INFY": "Infosys",
    "ICICIBANK": "ICICI Bank",
    "HINDUNILVR": "Hindustan Unilever",
    "SBIN": "State Bank of India SBI",
    "BHARTIARTL": "Bharti Airtel",
    "ITC": "ITC Limited",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "LT": "Larsen Toubro",
    "AXISBANK": "Axis Bank",
    "ASIANPAINT": "Asian Paints",
    "MARUTI": "Maruti Suzuki",
    "TITAN": "Titan Company",
    "SUNPHARMA": "Sun Pharma",
    "BAJFINANCE": "Bajaj Finance",
    "WIPRO": "Wipro",
    "HCLTECH": "HCL Technologies",
    "TATAMOTORS": "Tata Motors",
    "TATASTEEL": "Tata Steel",
    "ADANIENT": "Adani Enterprises",
    "ADANIPORTS": "Adani Ports",
}


class NewsService:
    """
    Service for fetching and analyzing market news.

    Sources:
    - Google News RSS (free, no API key needed)
    - Can be extended with NewsAPI, etc.
    """

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache_ttl = 300  # 5 minutes cache

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an active HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _analyze_sentiment(self, text: str) -> tuple[NewsSentiment, float]:
        """
        Analyze sentiment of text using keyword matching.

        Returns (sentiment, score) where score is -1 to 1.
        """
        text_lower = text.lower()

        bullish_count = sum(1 for kw in BULLISH_KEYWORDS if kw in text_lower)
        bearish_count = sum(1 for kw in BEARISH_KEYWORDS if kw in text_lower)

        total = bullish_count + bearish_count
        if total == 0:
            return NewsSentiment.NEUTRAL, 0.0

        # Calculate score (-1 to 1)
        score = (bullish_count - bearish_count) / total

        # Classify sentiment
        if score >= 0.5:
            sentiment = NewsSentiment.VERY_BULLISH
        elif score >= 0.2:
            sentiment = NewsSentiment.BULLISH
        elif score <= -0.5:
            sentiment = NewsSentiment.VERY_BEARISH
        elif score <= -0.2:
            sentiment = NewsSentiment.BEARISH
        else:
            sentiment = NewsSentiment.NEUTRAL

        return sentiment, round(score, 2)

    async def _fetch_google_news(self, query: str, num_results: int = 10) -> List[NewsArticle]:
        """
        Fetch news from Google News RSS.
        """
        session = await self._ensure_session()

        # Google News RSS URL
        encoded_query = quote_plus(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Google News returned status {response.status}")
                    return []

                content = await response.text()

            # Parse RSS XML
            root = ET.fromstring(content)
            articles = []

            for item in root.findall(".//item")[:num_results]:
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubDate")
                source = item.find("source")

                if title is None or link is None:
                    continue

                title_text = title.text or ""
                link_text = link.text or ""

                # Parse publication date
                pub_date_text = pub_date.text if pub_date is not None else None
                if pub_date_text:
                    try:
                        # Format: "Sat, 04 Feb 2026 10:30:00 GMT"
                        dt = datetime.strptime(pub_date_text, "%a, %d %b %Y %H:%M:%S %Z")
                        pub_date_text = dt.isoformat()
                    except:
                        pub_date_text = datetime.now(IST).isoformat()

                # Get source name
                source_text = source.text if source is not None else "Google News"

                # Analyze sentiment
                sentiment, score = self._analyze_sentiment(title_text)

                articles.append(NewsArticle(
                    title=title_text,
                    source=source_text,
                    url=link_text,
                    published_at=pub_date_text,
                    sentiment=sentiment,
                    sentiment_score=score,
                ))

            return articles

        except Exception as e:
            logger.error(f"Error fetching Google News: {e}")
            return []

    async def get_symbol_news(
        self,
        symbol: str,
        num_results: int = 10,
    ) -> List[NewsArticle]:
        """
        Get news for a specific stock symbol.
        """
        symbol = symbol.upper()

        # Build search query
        company_name = SYMBOL_NAMES.get(symbol, symbol)
        query = f"{company_name} stock NSE"

        articles = await self._fetch_google_news(query, num_results)

        # Tag articles with symbol
        for article in articles:
            article.related_symbols = [symbol]

        return articles

    async def get_market_news(self, num_results: int = 15) -> List[NewsArticle]:
        """
        Get general market news for Indian stock market.
        """
        queries = [
            "NSE Nifty stock market",
            "Indian stock market today",
            "Sensex BSE market",
        ]

        all_articles = []

        for query in queries:
            articles = await self._fetch_google_news(query, num_results // len(queries) + 1)
            all_articles.extend(articles)

        # Remove duplicates by URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique_articles.append(article)

        # Sort by sentiment score (most bullish/bearish first for relevance)
        unique_articles.sort(key=lambda a: abs(a.sentiment_score), reverse=True)

        return unique_articles[:num_results]

    async def get_sector_news(
        self,
        sector: str,
        num_results: int = 10,
    ) -> List[NewsArticle]:
        """
        Get news for a specific sector.
        """
        sector_queries = {
            "banking": "Indian banking sector stocks HDFC ICICI SBI",
            "it": "Indian IT sector stocks TCS Infosys Wipro",
            "pharma": "Indian pharma sector stocks Sun Pharma Cipla",
            "auto": "Indian auto sector stocks Maruti Tata Motors",
            "fmcg": "Indian FMCG sector stocks HUL ITC",
            "energy": "Indian energy sector stocks Reliance ONGC",
            "metals": "Indian metals sector stocks Tata Steel JSW",
        }

        query = sector_queries.get(sector.lower(), f"Indian {sector} sector stocks")
        return await self._fetch_google_news(query, num_results)

    async def get_trending_news(self, num_results: int = 20) -> Dict[str, Any]:
        """
        Get trending market news with overall sentiment analysis.
        """
        articles = await self.get_market_news(num_results)

        if not articles:
            return {
                "articles": [],
                "overall_sentiment": NewsSentiment.NEUTRAL.value,
                "sentiment_score": 0,
                "bullish_count": 0,
                "bearish_count": 0,
                "neutral_count": 0,
            }

        # Calculate overall sentiment
        bullish = sum(1 for a in articles if a.sentiment in [NewsSentiment.BULLISH, NewsSentiment.VERY_BULLISH])
        bearish = sum(1 for a in articles if a.sentiment in [NewsSentiment.BEARISH, NewsSentiment.VERY_BEARISH])
        neutral = sum(1 for a in articles if a.sentiment == NewsSentiment.NEUTRAL)

        avg_score = sum(a.sentiment_score for a in articles) / len(articles)

        if avg_score >= 0.3:
            overall = NewsSentiment.BULLISH
        elif avg_score >= 0.1:
            overall = NewsSentiment.BULLISH
        elif avg_score <= -0.3:
            overall = NewsSentiment.VERY_BEARISH
        elif avg_score <= -0.1:
            overall = NewsSentiment.BEARISH
        else:
            overall = NewsSentiment.NEUTRAL

        return {
            "articles": [a.to_dict() for a in articles],
            "overall_sentiment": overall.value,
            "sentiment_score": round(avg_score, 2),
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
        }


# Singleton instance
_news_service: Optional[NewsService] = None


def get_news_service() -> NewsService:
    """Get the news service singleton."""
    global _news_service
    if _news_service is None:
        _news_service = NewsService()
    return _news_service
