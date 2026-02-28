"""
Data Ingestion Service Implementation

Fetches and normalizes market data from multiple sources with cross-validation.
Primary: Yahoo Finance (free, real data)
Secondary: Angel One (real-time when connected)
Fallback: Mock data (only if all sources fail)
"""

from datetime import datetime
from typing import Optional
import logging

from app.core.config import settings
from app.core.market_hours import get_market_status, get_upcoming_expiries
from app.schemas.market import (
    DataRequest,
    MarketSnapshot,
    MarketMetadata,
    MarketPhase,
    SymbolData,
    OptionsChainData,
    NewsItem,
)

# Map MarketSession values to MarketPhase values
SESSION_TO_PHASE = {
    "PRE_OPEN": MarketPhase.PRE_OPEN,
    "OPENING": MarketPhase.PRE_OPEN,
    "NORMAL": MarketPhase.OPEN,
    "CLOSING": MarketPhase.CLOSING,
    "CLOSED": MarketPhase.CLOSED,
}
from app.services.data_ingestion.interface import (
    DataIngestionServiceInterface,
    DataIngestionResult,
)
from app.services.data_ingestion.yahoo_adapter import (
    fetch_yahoo_data,
    get_stock_info,
    validate_symbol,
)
from app.services.data_ingestion.multi_source import (
    fetch_multi_source_data,
    validate_data_sources,
)
from app.services.data_ingestion.mock_data import (
    generate_mock_symbol_data,
    generate_mock_options_chain,
    generate_mock_news,
)

logger = logging.getLogger(__name__)


class DataIngestionService(DataIngestionServiceInterface):
    """
    Data Ingestion Service.

    Uses multi-source data fetching (Yahoo Finance + Angel One) with cross-validation.
    Falls back to mock data only if all real sources fail.
    """

    def __init__(self):
        self._use_mock_fallback = True  # Use mock if real data fails
        self._use_multi_source = True  # Enable multi-source cross-validation

    @property
    def name(self) -> str:
        return "DataIngestionService"

    async def execute(self, input_data: DataRequest) -> DataIngestionResult:
        """Fetch and normalize market data from multiple sources."""
        start_time = datetime.now()
        errors: list[str] = []
        warnings: list[str] = []

        # Get market status
        market_status = get_market_status()

        # Fetch symbol data
        symbols_data: list[SymbolData] = []
        data_source = "Multi-Source (Yahoo + Angel One)"
        total_confidence = 0.0

        for symbol in input_data.symbols:
            try:
                if self._use_multi_source:
                    # Use multi-source fetching with cross-validation
                    multi_data = await fetch_multi_source_data(
                        symbol=symbol,
                        timeframe=input_data.timeframe,
                        lookback=input_data.lookback,
                    )

                    if multi_data:
                        symbols_data.append(multi_data.primary_data)
                        total_confidence += multi_data.quality.confidence
                        data_source = f"Multi-Source ({', '.join(multi_data.sources_used)})"

                        # Log quality metrics
                        logger.info(
                            f"Got data for {symbol}: Rs.{multi_data.primary_data.current_price:.2f} "
                            f"(confidence: {multi_data.quality.confidence:.0%}, "
                            f"sources: {multi_data.quality.source_count})"
                        )

                        # Add quality warnings
                        if multi_data.quality.warnings:
                            warnings.extend(multi_data.quality.warnings)

                        if not multi_data.quality.is_reliable:
                            warnings.append(
                                f"Low confidence data for {symbol} "
                                f"({multi_data.quality.confidence:.0%})"
                            )
                        continue

                # Fallback to single source (Yahoo Finance)
                data = await fetch_yahoo_data(
                    symbol=symbol,
                    timeframe=input_data.timeframe,
                    lookback=input_data.lookback,
                )

                if data:
                    symbols_data.append(data)
                    total_confidence += 0.7  # Single source confidence
                    data_source = "Yahoo Finance"
                    logger.info(f"Got real data for {symbol}: Rs.{data.current_price:.2f}")
                elif self._use_mock_fallback:
                    # Fallback to mock if all sources fail
                    warnings.append(f"Using mock data for {symbol} (all sources failed)")
                    data = generate_mock_symbol_data(
                        symbol=symbol,
                        timeframe=input_data.timeframe,
                        lookback=input_data.lookback,
                    )
                    symbols_data.append(data)
                    total_confidence += 0.3  # Mock data low confidence
                    data_source = "Mock (fallback)"
                else:
                    errors.append(f"No data available for {symbol}")

            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")
                if self._use_mock_fallback:
                    warnings.append(f"Using mock data for {symbol}: {str(e)}")
                    data = generate_mock_symbol_data(
                        symbol=symbol,
                        timeframe=input_data.timeframe,
                        lookback=input_data.lookback,
                    )
                    symbols_data.append(data)
                    total_confidence += 0.3
                    data_source = "Mock (error fallback)"
                else:
                    errors.append(f"Failed to fetch data for {symbol}: {str(e)}")

        # Calculate average confidence
        avg_confidence = (
            total_confidence / len(symbols_data)
            if symbols_data
            else 0.0
        )

        # Fetch options chain if requested
        options_chain: Optional[OptionsChainData] = None
        if input_data.include_options and input_data.symbols:
            try:
                underlying = input_data.symbols[0]
                expiry = input_data.options_expiry or get_upcoming_expiries(1)[0]
                # TODO: Implement real options chain from Angel One
                options_chain = generate_mock_options_chain(underlying, expiry)
                warnings.append("Options chain using mock data (API not configured)")
            except Exception as e:
                warnings.append(f"Failed to fetch options chain: {str(e)}")

        # Fetch news if requested
        news: Optional[list[NewsItem]] = None
        if input_data.include_news:
            try:
                # TODO: Implement real news API
                news = generate_mock_news(input_data.symbols, count=15)
                warnings.append("News using mock data (API not configured)")
            except Exception as e:
                warnings.append(f"Failed to fetch news: {str(e)}")

        # Calculate latency
        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Add confidence info to warnings if low
        if avg_confidence < 0.6:
            warnings.append(
                f"Data quality below threshold: {avg_confidence:.0%} average confidence"
            )

        # Build metadata
        metadata = MarketMetadata(
            source=data_source,
            latency_ms=latency_ms,
            is_market_open=market_status["is_open"],
            market_phase=SESSION_TO_PHASE.get(market_status["session"], MarketPhase.CLOSED),
            next_market_open=(
                datetime.fromisoformat(market_status["next_open"])
                if "next_open" in market_status
                else None
            ),
            last_updated=datetime.now(),
        )

        # Build snapshot
        snapshot = MarketSnapshot(
            timestamp=datetime.now(),
            symbols=symbols_data,
            options_chain=options_chain,
            news=news,
            metadata=metadata,
        )

        return DataIngestionResult(
            snapshot=snapshot,
            errors=errors,
            warnings=warnings,
        )

    async def get_quote(self, symbol: str) -> Optional[dict]:
        """Get quick quote for a single symbol."""
        try:
            info = await get_stock_info(symbol)
            if "error" not in info:
                return {
                    "symbol": info["symbol"],
                    "name": info.get("name", symbol),
                    "price": info.get("current_price", 0),
                    "previous_close": info.get("previous_close", 0),
                    "change": info.get("current_price", 0) - info.get("previous_close", 0),
                    "change_percent": (
                        (info.get("current_price", 0) - info.get("previous_close", 0))
                        / info.get("previous_close", 1) * 100
                        if info.get("previous_close", 0) > 0
                        else 0
                    ),
                    "day_high": info.get("day_high", 0),
                    "day_low": info.get("day_low", 0),
                    "volume": info.get("volume", 0),
                    "source": "Yahoo Finance",
                }
            return None
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            return None

    async def health_check(self) -> bool:
        """Check connectivity to data sources."""
        try:
            status = await validate_data_sources()
            # Return True if at least one source is available
            return status.get("overall", {}).get("sources_available", 0) >= 1
        except Exception:
            # Fallback to simple Yahoo check
            try:
                is_valid = await validate_symbol("RELIANCE")
                return is_valid
            except Exception:
                return False

    async def get_data_sources_status(self) -> dict:
        """Get detailed status of all data sources."""
        return await validate_data_sources()


# Singleton instance
_service_instance: Optional[DataIngestionService] = None


def get_data_ingestion_service() -> DataIngestionService:
    """Get or create data ingestion service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DataIngestionService()
    return _service_instance
