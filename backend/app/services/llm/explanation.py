"""
Explanation Service Implementation

Uses LLM (Claude Haiku / GPT-3.5) to generate human-readable explanations.
Cheaper and faster model for high-volume explanation tasks.

Generates:
- Plain English summaries
- Risk disclosures
- "What could go wrong" scenarios
- Human verification checklists
"""

import json
import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from app.schemas.trade import TradeIdea
from app.schemas.risk import RiskPlan, ValidationStatus
from app.schemas.explanation import (
    TradeExplanation,
    AlternativeScenario,
    ValidatedTrade,
)
from app.services.llm.interface import ExplanationServiceInterface
from app.services.llm.client import LLMClient, ModelTier, get_llm_client
from app.services.llm.prompts import (
    EXPLANATION_SYSTEM_PROMPT,
    format_explanation_prompt,
)

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


class ExplanationService(ExplanationServiceInterface):
    """
    Explanation Service using LLM for human-readable output.

    Uses cheaper models (Haiku/GPT-3.5) for cost-effective explanations.
    Falls back to template-based explanations if LLM is unavailable.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self._llm_client = llm_client

    @property
    def llm_client(self) -> LLMClient:
        """Lazy initialization of LLM client."""
        if self._llm_client is None:
            self._llm_client = get_llm_client()
        return self._llm_client

    @property
    def name(self) -> str:
        return "ExplanationService"

    async def execute(self, input_data: ValidatedTrade) -> TradeExplanation:
        """
        Generate human-readable explanation.

        Falls back to template-based explanation if LLM fails.
        """
        try:
            return await self._llm_explanation(input_data)
        except Exception as e:
            logger.warning(f"LLM explanation failed: {e}, falling back to template")
            return self._template_explanation(input_data)

    async def _llm_explanation(self, validated_trade: ValidatedTrade) -> TradeExplanation:
        """Generate explanation using LLM."""
        idea = validated_trade.idea
        risk_plan = validated_trade.risk_plan

        # Format prompt
        user_prompt = format_explanation_prompt(
            trade_idea=idea.model_dump(),
            risk_plan=risk_plan.model_dump(),
        )

        # Call LLM (cheaper model)
        response = await self.llm_client.generate(
            system_prompt=EXPLANATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model_tier=ModelTier.EXPLANATION,
            temperature=0.4,  # Slightly more creative for explanations
        )

        # Parse JSON response
        try:
            content = response.content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            llm_output = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse explanation response: {e}")
            raise ValueError("LLM returned invalid JSON for explanation")

        return self._build_explanation(idea, llm_output)

    def _build_explanation(
        self,
        idea: TradeIdea,
        llm_output: dict,
    ) -> TradeExplanation:
        """Build TradeExplanation from LLM output."""

        # Parse alternative scenarios
        scenarios = []
        for scenario_data in llm_output.get("alternative_scenarios", []):
            scenarios.append(
                AlternativeScenario(
                    scenario=scenario_data.get("scenario", "Market moves sideways"),
                    probability=str(scenario_data.get("probability", "Unknown")),
                    outcome=scenario_data.get("outcome", "Trade outcome uncertain"),
                    action=scenario_data.get("action", "Monitor and adjust as needed"),
                )
            )

        # Ensure at least one scenario
        if not scenarios:
            scenarios.append(
                AlternativeScenario(
                    scenario="Trade does not work as expected",
                    probability="30-40%",
                    outcome="Stop loss hit, loss incurred",
                    action="Accept the loss and move on. Do not average down.",
                )
            )

        return TradeExplanation(
            trade_id=idea.id,
            timestamp=datetime.now(IST),
            summary=llm_output.get(
                "summary",
                f"{idea.symbol} shows {idea.direction.value.lower()} setup with moderate confidence.",
            ),
            rationale=llm_output.get(
                "rationale",
                "The technical analysis suggests this trade idea based on the provided indicators.",
            ),
            risk_disclosure=llm_output.get(
                "risk_disclosure",
                "Trading involves substantial risk of loss. Past performance does not guarantee future results. Only trade with money you can afford to lose.",
            ),
            what_could_go_wrong=llm_output.get(
                "what_could_go_wrong",
                [
                    "Market conditions could change suddenly",
                    "Unexpected news could impact the stock",
                    "Technical patterns may not work as expected",
                ],
            ),
            alternative_scenarios=scenarios,
            confidence_statement=llm_output.get(
                "confidence_statement",
                f"Based on the technical setup, there is a {idea.confidence_band.low*100:.0f}-{idea.confidence_band.high*100:.0f}% estimated probability of success. This is not a guarantee.",
            ),
            human_checklist=llm_output.get(
                "human_checklist",
                [
                    "Verify current price is still in the entry zone",
                    "Check for any recent news about the company",
                    "Ensure you have sufficient capital",
                    "Set stop loss immediately after entry",
                    "Don't exceed your risk limits",
                ],
            ),
        )

    def _template_explanation(self, validated_trade: ValidatedTrade) -> TradeExplanation:
        """
        Generate template-based explanation when LLM is unavailable.

        Uses simple templates and rule-based logic.
        """
        idea = validated_trade.idea
        risk_plan = validated_trade.risk_plan
        approved = risk_plan.approved_plan

        now = datetime.now(IST)

        # Build summary based on direction
        if idea.direction.value == "LONG":
            direction_text = "bullish (long)"
            action_text = "buying"
        elif idea.direction.value == "SHORT":
            direction_text = "bearish (short)"
            action_text = "shorting"
        else:
            direction_text = "neutral"
            action_text = "observing"

        summary = f"{idea.symbol} shows a {direction_text} setup based on technical analysis. "
        if approved:
            summary += f"Consider {action_text} with defined risk of ₹{approved.max_loss_amount:,.0f}."
        else:
            summary += "However, the trade was not approved by risk validation."

        # Build rationale from reasoning
        reasoning = idea.reasoning
        rationale_parts = []

        if reasoning.primary_factors:
            rationale_parts.append(
                f"The main reasons supporting this idea are: {'; '.join(reasoning.primary_factors)}."
            )

        if reasoning.confluences:
            rationale_parts.append(
                f"Additional supporting factors include: {'; '.join(reasoning.confluences)}."
            )

        if reasoning.concerns:
            rationale_parts.append(
                f"However, there are concerns to consider: {'; '.join(reasoning.concerns)}."
            )

        rationale = " ".join(rationale_parts) if rationale_parts else (
            "This trade idea is based on technical indicator analysis. "
            "The specific setup shows certain patterns that historically have had some predictive value, "
            "though no pattern guarantees future results."
        )

        # Risk disclosure
        if approved:
            risk_disclosure = (
                f"RISK WARNING: This is a trade SUGGESTION, not financial advice. "
                f"If you take this trade and it hits the stop loss, you will lose approximately "
                f"₹{approved.max_loss_amount:,.0f} ({approved.max_loss_percent:.2f}% of your portfolio). "
                f"Only trade with money you can afford to lose. Past patterns do not guarantee future results."
            )
        else:
            risk_disclosure = (
                "RISK WARNING: This trade was NOT approved by the risk system. "
                "Taking this trade would violate your risk management rules. "
                "Do not override risk controls. Protect your capital."
            )

        # What could go wrong
        what_could_go_wrong = [
            f"The stock could reverse direction and hit your stop loss at ₹{approved.stop_loss if approved else 0:,.2f}",
            "Broader market conditions could change suddenly (e.g., global events, FII selling)",
            "Company-specific news (earnings, management changes) could impact the stock",
            "Technical patterns have historical win rates of 50-70%, meaning 30-50% fail",
            "Liquidity conditions could change, making it difficult to exit at desired prices",
        ]

        # Alternative scenarios
        alternative_scenarios = [
            AlternativeScenario(
                scenario="Trade works quickly",
                probability="30-40%",
                outcome="Price moves to first target within expected timeframe",
                action="Book partial profits at TP1, trail stop loss for remaining position",
            ),
            AlternativeScenario(
                scenario="Trade goes sideways",
                probability="25-35%",
                outcome="Price consolidates without reaching target or stop loss",
                action="Consider time-based exit if no movement after several days",
            ),
            AlternativeScenario(
                scenario="Trade fails",
                probability="25-40%",
                outcome="Price reverses and hits stop loss",
                action="Accept the loss, do not average down or move stop loss",
            ),
        ]

        # Confidence statement
        conf = idea.confidence_band
        confidence_statement = (
            f"Based on historical patterns in similar technical setups, there is an estimated "
            f"{conf.low*100:.0f}% to {conf.high*100:.0f}% probability of this trade reaching its first target "
            f"(base estimate: {conf.mid*100:.0f}%). This is a statistical estimate, not a guarantee. "
            f"Each trade should be treated as having independent probability."
        )

        # Human checklist
        human_checklist = [
            f"Verify the current price is still near ₹{idea.suggested_entry.entry_price or 'entry zone'}",
            "Check for any company announcements or earnings dates",
            "Confirm you have not exceeded your daily/weekly trade limits",
            f"Ensure taking this trade keeps portfolio exposure under your max ({risk_plan.portfolio_impact.new_exposure_percent:.1f}% after)",
            "Set the stop loss order IMMEDIATELY after entering the trade",
            "Do not move the stop loss to increase risk - only tighten it",
            "Have a plan for partial profit booking",
            "Avoid trading if you're emotional, tired, or distracted",
        ]

        return TradeExplanation(
            trade_id=idea.id,
            timestamp=now,
            summary=summary,
            rationale=rationale,
            risk_disclosure=risk_disclosure,
            what_could_go_wrong=what_could_go_wrong,
            alternative_scenarios=alternative_scenarios,
            confidence_statement=confidence_statement,
            human_checklist=human_checklist,
        )

    async def health_check(self) -> bool:
        """Check LLM API connectivity."""
        try:
            return await self.llm_client.health_check()
        except Exception:
            return False


# Singleton instance
_service_instance: Optional[ExplanationService] = None


def get_explanation_service() -> ExplanationService:
    """Get or create explanation service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ExplanationService()
    return _service_instance
