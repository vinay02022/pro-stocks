"""
LLM Service Interfaces

Defines contracts for reasoning and explanation layers.
"""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Optional

from app.services.base import BaseService
from app.schemas.indicators import IndicatorOutput
from app.schemas.trade import TradeIdea, MarketContext
from app.schemas.explanation import TradeExplanation, ValidatedTrade


@dataclass
class ReasoningInput:
    """Input for the reasoning layer."""

    indicator_output: IndicatorOutput
    market_context: Optional[MarketContext] = None


class ReasoningServiceInterface(BaseService[ReasoningInput, TradeIdea]):
    """
    Reasoning Service Contract (LLM Layer 1).

    Uses: GPT-5 / Claude Opus (expensive, powerful)

    INPUT: ReasoningInput
        - indicator_output: Complete indicator analysis from Indicator Engine
        - market_context: Optional additional context (news sentiment, etc.)

    OUTPUT: TradeIdea
        - direction: LONG / SHORT / NEUTRAL
        - confidence_band: Probability range (NOT certainty)
        - reasoning: Why this trade makes sense + concerns
        - entry_plan: How to enter
        - invalidation: What would prove us wrong

    RULES:
        - NEVER do math - all numbers are from indicator_output
        - ALWAYS include concerns (nothing is certain)
        - ALWAYS express confidence as a range
        - NEVER claim certainty or guaranteed profits
    """

    @property
    def name(self) -> str:
        return "ReasoningService"

    @abstractmethod
    async def execute(self, input_data: ReasoningInput) -> TradeIdea:
        """Generate trade idea using LLM reasoning."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check LLM API connectivity."""
        pass


class ExplanationServiceInterface(BaseService[ValidatedTrade, TradeExplanation]):
    """
    Explanation Service Contract (LLM Layer 2).

    Uses: GPT-3.5 / Claude Haiku (cheaper, faster)

    INPUT: ValidatedTrade
        - idea: The trade idea from Reasoning Service
        - risk_plan: Risk validation from Risk Engine

    OUTPUT: TradeExplanation
        - summary: 1-2 sentence summary
        - rationale: Detailed reasoning in plain English
        - risk_disclosure: Mandatory risk warning
        - what_could_go_wrong: List of risks
        - alternative_scenarios: What else could happen
        - human_checklist: Things for human to verify

    RULES:
        - Keep language simple and accessible
        - ALWAYS include risk disclosure
        - ALWAYS include "what could go wrong"
        - NEVER promise or guarantee outcomes
    """

    @property
    def name(self) -> str:
        return "ExplanationService"

    @abstractmethod
    async def execute(self, input_data: ValidatedTrade) -> TradeExplanation:
        """Generate human-readable explanation."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check LLM API connectivity."""
        pass
