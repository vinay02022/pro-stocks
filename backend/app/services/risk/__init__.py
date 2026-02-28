"""
Risk Validation Engine

CONTRACT:
    Input:  TradeIdea + PortfolioState + RiskConfig
    Output: RiskPlan

RESPONSIBILITIES:
    - Validate trade against risk rules
    - Calculate position sizing
    - Check portfolio exposure limits
    - Check daily/weekly loss limits
    - Check correlation with existing positions
    - APPROVE, REJECT, or MODIFY trades

PURE PYTHON - No LLM involvement.
All rules are deterministic and auditable.

CRITICAL: Risk rules are NON-NEGOTIABLE.
If a trade is REJECTED, it cannot proceed.
"""

from app.services.risk.interface import RiskServiceInterface, RiskValidationInput
from app.services.risk.service import RiskValidationService, get_risk_service

__all__ = [
    "RiskServiceInterface",
    "RiskValidationInput",
    "RiskValidationService",
    "get_risk_service",
]
