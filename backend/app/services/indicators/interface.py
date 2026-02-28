"""
Indicator Engine Service Interface

Defines the contract for the indicator calculation layer.
"""

from abc import abstractmethod
from typing import Optional

from app.services.base import BaseService
from app.schemas.market import MarketSnapshot, SymbolData
from app.schemas.indicators import IndicatorOutput


class IndicatorServiceInterface(BaseService[MarketSnapshot, dict[str, IndicatorOutput]]):
    """
    Indicator Engine Service Contract.

    INPUT: MarketSnapshot
        - symbols: List of SymbolData with OHLCV candles

    OUTPUT: dict[str, IndicatorOutput]
        - Key: symbol name
        - Value: Complete indicator analysis for that symbol
    """

    @property
    def name(self) -> str:
        return "IndicatorService"

    @abstractmethod
    async def execute(
        self, input_data: MarketSnapshot
    ) -> dict[str, IndicatorOutput]:
        """Calculate indicators for all symbols in snapshot."""
        pass

    @abstractmethod
    async def calculate_for_symbol(
        self,
        symbol_data: SymbolData,
        portfolio_value: Optional[float] = None,
        risk_percent: float = 1.0,
    ) -> IndicatorOutput:
        """
        Calculate indicators for a single symbol.

        Args:
            symbol_data: OHLCV data for the symbol
            portfolio_value: Portfolio value for position sizing (optional)
            risk_percent: % of portfolio to risk per trade

        Returns:
            Complete indicator analysis
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Indicator service is always healthy (pure computation)."""
        pass
