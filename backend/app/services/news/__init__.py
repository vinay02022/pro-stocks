"""
News Integration Service

Fetches and analyzes market news from various sources.
"""

from app.services.news.service import (
    NewsService,
    get_news_service,
    NewsArticle,
    NewsSentiment,
)

__all__ = [
    "NewsService",
    "get_news_service",
    "NewsArticle",
    "NewsSentiment",
]
