"""
Risk Validation Service Interface

Defines the contract for the risk validation layer.
"""

from abc import abstractmethod
from dataclasses import dataclass

from app.services.base import BaseService
from app.schemas.trade import TradeIdea
from app.schemas.risk import RiskPlan, PortfolioState, RiskConfig


@dataclass
class RiskValidationInput:
    """Input for risk validation."""

    trade_idea: TradeIdea
    portfolio_state: PortfolioState
    risk_config: RiskConfig


class RiskServiceInterface(BaseService[RiskValidationInput, RiskPlan]):
    """
    Risk Validation Service Contract.

    INPUT: RiskValidationInput
        - trade_idea: From Reasoning Service
        - portfolio_state: Current portfolio positions and metrics
        - risk_config: User's risk rules and limits

    OUTPUT: RiskPlan
        - validation_status: APPROVED / REJECTED / MODIFIED
        - rejection_reasons: Why rejected (if applicable)
        - approved_plan: Position size, SL, TP (if approved)
        - portfolio_impact: How this affects portfolio risk
        - risk_warnings: Mandatory warnings for human

    VALIDATION RULES (in order):
        1. Max position size check
        2. Max sector exposure check
        3. Max portfolio exposure check
        4. Max daily trades check
        5. Daily loss limit check
        6. Drawdown limit check
        7. Min risk-reward ratio check
        8. Correlation check (if existing positions)
        9. Market hours check
        10. Liquidity check

    If ANY rule fails, trade is REJECTED (no exceptions).
    """

    @property
    def name(self) -> str:
        return "RiskService"

    @abstractmethod
    async def execute(self, input_data: RiskValidationInput) -> RiskPlan:
        """Validate trade against risk rules."""
        pass

    @abstractmethod
    async def validate_position_size(
        self,
        trade_value: float,
        portfolio_value: float,
        max_percent: float,
    ) -> tuple[bool, str]:
        """Check if position size is within limits."""
        pass

    @abstractmethod
    async def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        risk_amount: float,
    ) -> int:
        """Calculate optimal position size given risk parameters."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Risk service is always healthy (pure computation)."""
        pass
