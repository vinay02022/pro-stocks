"""
Data Ingestion Service Interface

Defines the contract for the data ingestion layer.
"""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.services.base import BaseService
from app.schemas.market import DataRequest, MarketSnapshot


@dataclass
class DataIngestionResult:
    """Result from data ingestion including any warnings/errors."""

    snapshot: MarketSnapshot
    errors: list[str]
    warnings: list[str]


class DataIngestionServiceInterface(BaseService[DataRequest, DataIngestionResult]):
    """
    Data Ingestion Service Contract.

    INPUT: DataRequest
        - symbols: List of symbols to fetch
        - data_types: What data to fetch (OHLCV, options, news)
        - timeframe: Candle timeframe
        - lookback: Number of candles

    OUTPUT: DataIngestionResult
        - snapshot: MarketSnapshot with all requested data
        - errors: Any errors during fetch
        - warnings: Non-fatal warnings
    """

    @property
    def name(self) -> str:
        return "DataIngestionService"

    @abstractmethod
    async def execute(self, input_data: DataRequest) -> DataIngestionResult:
        """Fetch and normalize market data."""
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> Optional[dict]:
        """Get quick quote for a single symbol."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check connectivity to all data sources."""
        pass
