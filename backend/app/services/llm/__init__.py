"""
LLM Orchestration Service

CONTRACT:
    Reasoning Layer:
        Input:  IndicatorOutput + MarketContext
        Output: TradeIdea

    Explanation Layer:
        Input:  ValidatedTrade (TradeIdea + RiskPlan)
        Output: TradeExplanation

RESPONSIBILITIES:
    - Market regime detection (using LLM reasoning)
    - Trade suitability analysis
    - Strategy selection based on conditions
    - Confluence analysis
    - Human-readable explanation generation

LLM USAGE:
    - Reasoning: Claude Opus / GPT-4 (complex reasoning)
    - Explanation: Claude Haiku / GPT-3.5 (cheaper, faster)

CRITICAL RULES:
    - LLM does NO math - all numbers come from Indicator Engine
    - LLM interprets and reasons, never calculates
    - Must always express uncertainty (confidence bands)
    - Must always include concerns/risks

FALLBACK BEHAVIOR:
    - If LLM is unavailable, services fall back to rule-based/template outputs
    - System remains functional without LLM API keys
"""

from app.services.llm.interface import (
    ReasoningServiceInterface,
    ExplanationServiceInterface,
    ReasoningInput,
)
from app.services.llm.client import (
    LLMClient,
    LLMConfig,
    LLMProvider,
    ModelTier,
    get_llm_client,
)
from app.services.llm.reasoning import ReasoningService, get_reasoning_service
from app.services.llm.explanation import ExplanationService, get_explanation_service

__all__ = [
    # Interfaces
    "ReasoningServiceInterface",
    "ExplanationServiceInterface",
    "ReasoningInput",
    # Client
    "LLMClient",
    "LLMConfig",
    "LLMProvider",
    "ModelTier",
    "get_llm_client",
    # Services
    "ReasoningService",
    "get_reasoning_service",
    "ExplanationService",
    "get_explanation_service",
]
