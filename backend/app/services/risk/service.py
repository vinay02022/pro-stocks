"""
Risk Validation Engine Implementation

Validates trades against risk rules.
PURE PYTHON - No LLM involvement.
All rules are deterministic and auditable.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from app.schemas.trade import TradeIdea, TradeDirection
from app.schemas.risk import (
    RiskPlan,
    ApprovedPlan,
    PortfolioImpact,
    PortfolioState,
    RiskConfig,
    TakeProfitTarget,
    TrailingStopConfig,
    ValidationStatus,
)
from app.services.risk.interface import RiskServiceInterface, RiskValidationInput


class RiskValidationService(RiskServiceInterface):
    """
    Risk Validation Engine.

    Validates trades against risk rules.
    Can APPROVE, REJECT, or MODIFY trades.
    Rules are NON-NEGOTIABLE.
    """

    @property
    def name(self) -> str:
        return "RiskValidationService"

    async def execute(self, input_data: RiskValidationInput) -> RiskPlan:
        """Validate trade against risk rules."""
        idea = input_data.trade_idea
        portfolio = input_data.portfolio_state
        config = input_data.risk_config

        rejection_reasons: list[str] = []
        risk_warnings: list[str] = []

        # Get current portfolio metrics
        current_exposure = portfolio.metrics.exposure_percent
        today_trades = portfolio.metrics.today_trades
        today_loss = portfolio.metrics.today_loss_percent
        current_drawdown = portfolio.metrics.current_drawdown

        # Calculate proposed trade details
        entry_price = (
            idea.suggested_entry.entry_price
            or (
                (idea.suggested_entry.entry_zone.low + idea.suggested_entry.entry_zone.high) / 2
                if idea.suggested_entry.entry_zone
                else None
            )
        )

        if not entry_price:
            rejection_reasons.append("No valid entry price specified")
            return self._create_rejected_plan(idea.id, rejection_reasons, portfolio, config)

        # Calculate stop loss and position size
        # For simplicity, using a 2% stop loss if not specified
        sl_percent = 2.0
        stop_loss = entry_price * (1 - sl_percent / 100) if idea.direction == TradeDirection.LONG else entry_price * (1 + sl_percent / 100)

        # Calculate position size based on risk
        risk_amount = portfolio.metrics.total_value * (config.max_daily_loss_percent / 100) / config.max_daily_trades
        position_size = await self.calculate_position_size(entry_price, stop_loss, risk_amount)
        position_value = position_size * entry_price
        position_percent = (position_value / portfolio.metrics.total_value) * 100

        # Cap position to max allowed percent
        max_position_value = portfolio.metrics.total_value * (config.max_position_percent / 100)
        if position_value > max_position_value:
            position_size = int(max_position_value / entry_price)
            position_value = position_size * entry_price
            position_percent = (position_value / portfolio.metrics.total_value) * 100

        # =============================================================================
        # VALIDATION RULES (in order of priority)
        # =============================================================================

        # Rule 1: Max position size
        is_valid, msg = await self.validate_position_size(
            position_value, portfolio.metrics.total_value, config.max_position_percent
        )
        if not is_valid:
            rejection_reasons.append(msg)

        # Rule 2: Max portfolio exposure
        new_exposure = current_exposure + position_percent
        if new_exposure > config.max_portfolio_exposure_percent:
            rejection_reasons.append(
                f"Would exceed max portfolio exposure: {new_exposure:.1f}% > {config.max_portfolio_exposure_percent}%"
            )

        # Rule 3: Max daily trades
        if today_trades >= config.max_daily_trades:
            rejection_reasons.append(
                f"Max daily trades reached: {today_trades} >= {config.max_daily_trades}"
            )

        # Rule 4: Daily loss limit
        if today_loss >= config.max_daily_loss_percent:
            rejection_reasons.append(
                f"Daily loss limit reached: {today_loss:.2f}% >= {config.max_daily_loss_percent}%"
            )

        # Rule 5: Drawdown limit
        if current_drawdown >= config.max_drawdown_percent:
            rejection_reasons.append(
                f"Max drawdown reached: {current_drawdown:.2f}% >= {config.max_drawdown_percent}%"
            )

        # Rule 6: Allowed timeframes
        if idea.timeframe.value not in config.allowed_timeframes:
            rejection_reasons.append(
                f"Timeframe {idea.timeframe.value} not allowed. Allowed: {config.allowed_timeframes}"
            )

        # Rule 7: Check sector concentration (simplified)
        # In real implementation, would check against existing positions
        risk_warnings.append("Verify sector concentration before executing")

        # Rule 8: Check correlation (simplified)
        # In real implementation, would check correlation with existing positions
        correlation_warning = self._check_correlation(idea.symbol, portfolio)
        if correlation_warning:
            risk_warnings.append(correlation_warning)

        # =============================================================================
        # BUILD RESULT
        # =============================================================================

        if rejection_reasons:
            return self._create_rejected_plan(idea.id, rejection_reasons, portfolio, config)

        # Calculate take profit targets
        sl_distance = abs(entry_price - stop_loss)
        take_profits = [
            TakeProfitTarget(
                price=round(entry_price + sl_distance * 1.5, 2) if idea.direction == TradeDirection.LONG else round(entry_price - sl_distance * 1.5, 2),
                exit_percent=33,
                label="TP1",
            ),
            TakeProfitTarget(
                price=round(entry_price + sl_distance * 2.5, 2) if idea.direction == TradeDirection.LONG else round(entry_price - sl_distance * 2.5, 2),
                exit_percent=33,
                label="TP2",
            ),
            TakeProfitTarget(
                price=round(entry_price + sl_distance * 3.5, 2) if idea.direction == TradeDirection.LONG else round(entry_price - sl_distance * 3.5, 2),
                exit_percent=34,
                label="TP3",
            ),
        ]

        # Trailing stop (activates at TP1)
        trailing_stop = TrailingStopConfig(
            activation_price=take_profits[0].price,
            trail_percent=2.0,
        )

        # Risk-reward ratio (using first TP)
        rr_ratio = (abs(take_profits[0].price - entry_price) / sl_distance) if sl_distance > 0 else 0

        # Validate minimum R:R (use small epsilon for floating point comparison)
        if rr_ratio < config.min_risk_reward_ratio - 0.01:
            rejection_reasons.append(
                f"Risk-reward ratio too low: {rr_ratio:.2f} < {config.min_risk_reward_ratio}"
            )
            return self._create_rejected_plan(idea.id, rejection_reasons, portfolio, config)

        # Calculate max loss
        max_loss_amount = position_size * sl_distance
        max_loss_percent = (max_loss_amount / portfolio.metrics.total_value) * 100

        approved_plan = ApprovedPlan(
            position_size=position_size,
            position_value=round(position_value, 2),
            max_loss_amount=round(max_loss_amount, 2),
            max_loss_percent=round(max_loss_percent, 2),
            risk_reward_ratio=round(rr_ratio, 2),
            stop_loss=round(stop_loss, 2),
            take_profit=take_profits,
            trailing_stop=trailing_stop,
        )

        # Portfolio impact
        portfolio_impact = PortfolioImpact(
            current_exposure_percent=round(current_exposure, 2),
            new_exposure_percent=round(new_exposure, 2),
            max_drawdown_if_all_sl_hit=round(
                current_drawdown + max_loss_percent, 2
            ),
        )

        # Add standard warnings
        risk_warnings.extend([
            "Set stop loss order immediately after entry",
            "Do not move stop loss to increase risk",
            f"Maximum loss on this trade: ₹{max_loss_amount:,.0f} ({max_loss_percent:.2f}%)",
        ])

        return RiskPlan(
            trade_id=idea.id,
            validation_status=ValidationStatus.APPROVED,
            approved_plan=approved_plan,
            portfolio_impact=portfolio_impact,
            risk_warnings=risk_warnings,
        )

    async def validate_position_size(
        self,
        trade_value: float,
        portfolio_value: float,
        max_percent: float,
    ) -> tuple[bool, str]:
        """Check if position size is within limits."""
        if portfolio_value <= 0:
            return False, "Invalid portfolio value"

        position_percent = (trade_value / portfolio_value) * 100

        if position_percent > max_percent:
            return False, f"Position too large: {position_percent:.1f}% > {max_percent}% max"

        return True, ""

    async def calculate_position_size(
        self,
        entry_price: float,
        stop_loss: float,
        risk_amount: float,
    ) -> int:
        """Calculate optimal position size given risk parameters."""
        sl_distance = abs(entry_price - stop_loss)

        if sl_distance <= 0:
            return 0

        # Number of shares = Risk Amount / (Entry - SL)
        shares = int(risk_amount / sl_distance)

        # Minimum 1 share
        return max(shares, 1) if shares > 0 else 0

    async def health_check(self) -> bool:
        """Risk service is always healthy (pure computation)."""
        return True

    def _create_rejected_plan(
        self,
        trade_id: UUID,
        reasons: list[str],
        portfolio: PortfolioState,
        config: RiskConfig,
    ) -> RiskPlan:
        """Create a rejected risk plan."""
        return RiskPlan(
            trade_id=trade_id,
            validation_status=ValidationStatus.REJECTED,
            rejection_reasons=reasons,
            portfolio_impact=PortfolioImpact(
                current_exposure_percent=portfolio.metrics.exposure_percent,
                new_exposure_percent=portfolio.metrics.exposure_percent,
                max_drawdown_if_all_sl_hit=portfolio.metrics.current_drawdown,
            ),
            risk_warnings=["Trade rejected - see rejection reasons"],
        )

    def _check_correlation(
        self, symbol: str, portfolio: PortfolioState
    ) -> Optional[str]:
        """Check correlation with existing positions."""
        # Simplified: check if same symbol exists
        for position in portfolio.positions:
            if position.symbol == symbol:
                return f"Already have position in {symbol}"

        # In real implementation, would check sector/correlation matrix
        return None


# Singleton instance
_service_instance: Optional[RiskValidationService] = None


def get_risk_service() -> RiskValidationService:
    """Get or create risk service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = RiskValidationService()
    return _service_instance
