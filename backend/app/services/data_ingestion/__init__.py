"""
Data Ingestion Service

CONTRACT:
    Input:  DataRequest
    Output: MarketSnapshot

RESPONSIBILITIES:
    - Fetch OHLCV data from Groww API
    - Fetch options chain from Angel One API
    - Fetch news from News API
    - Normalize all data to standard schemas
    - Cache responses in Redis
    - Handle rate limiting

NO LLM INVOLVEMENT - Pure data fetching and transformation.
"""

from app.services.data_ingestion.interface import (
    DataIngestionServiceInterface,
    DataIngestionResult,
)
from app.services.data_ingestion.service import (
    DataIngestionService,
    get_data_ingestion_service,
)

__all__ = [
    "DataIngestionServiceInterface",
    "DataIngestionResult",
    "DataIngestionService",
    "get_data_ingestion_service",
]
