"""
Reasoning Service Implementation

Uses LLM (Claude Opus / GPT-4) to analyze indicators and generate trade ideas.

CRITICAL: LLM does NO math. All numbers come from Indicator Engine.
LLM only provides reasoning and interpretation.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.schemas.indicators import IndicatorOutput
from app.schemas.trade import (
    TradeIdea,
    TradeDirection,
    TradeTimeframe,
    TrendType,
    VolatilityLevel,
    MomentumLevel,
    EntryType,
    ConfidenceBand,
    MarketRegime,
    TradeReasoning,
    EntryPlan,
    EntryZone,
    MarketContext,
    IdeaStatus,
)
from app.services.llm.interface import ReasoningServiceInterface, ReasoningInput
from app.services.llm.client import LLMClient, ModelTier, get_llm_client
from app.services.llm.prompts import (
    REASONING_SYSTEM_PROMPT,
    format_reasoning_prompt,
)

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


class ReasoningService(ReasoningServiceInterface):
    """
    Reasoning Service using LLM for trade idea generation.

    Uses expensive models (Opus/GPT-4) for complex analysis.
    Falls back to deterministic rules if LLM is unavailable.
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
        return "ReasoningService"

    async def execute(self, input_data: ReasoningInput) -> TradeIdea:
        """
        Generate trade idea using LLM reasoning.

        Falls back to rule-based analysis if LLM fails.
        """
        indicator_output = input_data.indicator_output
        market_context = input_data.market_context

        try:
            # Try LLM-based reasoning
            return await self._llm_reasoning(indicator_output, market_context)
        except Exception as e:
            logger.warning(f"LLM reasoning failed: {e}, falling back to rules")
            # Fallback to deterministic rule-based analysis
            return await self._rule_based_reasoning(indicator_output, market_context)

    async def _llm_reasoning(
        self,
        indicator_output: IndicatorOutput,
        market_context: Optional[MarketContext],
    ) -> TradeIdea:
        """Generate trade idea using LLM."""
        # Convert to dict for prompt formatting
        indicator_dict = indicator_output.model_dump()
        context_dict = market_context.model_dump() if market_context else None

        # Format prompt
        user_prompt = format_reasoning_prompt(
            symbol=indicator_output.symbol,
            indicator_output=indicator_dict,
            market_context=context_dict,
        )

        # Call LLM
        response = await self.llm_client.generate(
            system_prompt=REASONING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            model_tier=ModelTier.REASONING,
            temperature=0.3,  # Lower temperature for more consistent output
        )

        # Parse JSON response
        try:
            # Extract JSON from response (handle markdown code blocks)
            content = response.content.strip()
            if content.startswith("```"):
                # Remove markdown code block
                lines = content.split("\n")
                content = "\n".join(lines[1:-1])

            llm_output = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Response content: {response.content[:500]}")
            raise ValueError("LLM returned invalid JSON")

        # Build TradeIdea from LLM output
        return self._build_trade_idea(
            symbol=indicator_output.symbol,
            llm_output=llm_output,
            indicator_output=indicator_output,
        )

    def _build_trade_idea(
        self,
        symbol: str,
        llm_output: dict,
        indicator_output: IndicatorOutput,
    ) -> TradeIdea:
        """Build TradeIdea from LLM output."""
        now = datetime.now(IST)

        # Parse confidence band
        conf = llm_output.get("confidence_band", {})
        confidence_band = ConfidenceBand(
            low=max(0.0, min(1.0, conf.get("low", 0.5))),
            mid=max(0.0, min(1.0, conf.get("mid", 0.55))),
            high=max(0.0, min(1.0, conf.get("high", 0.6))),
        )

        # Parse regime
        regime_data = llm_output.get("regime", {})
        regime = MarketRegime(
            trend=TrendType(regime_data.get("trend", "SIDEWAYS")),
            volatility=VolatilityLevel(regime_data.get("volatility", "NORMAL")),
            momentum=MomentumLevel(regime_data.get("momentum", "MODERATE")),
        )

        # Parse reasoning
        reasoning_data = llm_output.get("reasoning", {})
        reasoning = TradeReasoning(
            primary_factors=reasoning_data.get("primary_factors", ["No factors provided"]),
            confluences=reasoning_data.get("confluences", []),
            concerns=reasoning_data.get("concerns", ["Market risk always present"]),
        )

        # Parse entry plan
        entry_data = llm_output.get("suggested_entry", {})
        entry_zone = None
        if entry_data.get("entry_zone"):
            zone = entry_data["entry_zone"]
            entry_zone = EntryZone(low=zone["low"], high=zone["high"])

        entry_plan = EntryPlan(
            entry_type=EntryType(entry_data.get("entry_type", "LIMIT")),
            entry_price=entry_data.get("entry_price"),
            entry_zone=entry_zone,
            trigger_condition=entry_data.get("trigger_condition"),
        )

        # If no entry price and no zone, use current price
        if not entry_plan.entry_price and not entry_plan.entry_zone:
            entry_plan.entry_price = indicator_output.price.current

        # Determine timeframe
        timeframe_str = llm_output.get("timeframe", "SWING")
        timeframe = TradeTimeframe(timeframe_str)

        # Set expiration based on timeframe
        if timeframe == TradeTimeframe.INTRADAY:
            expires_at = now.replace(hour=15, minute=30, second=0, microsecond=0)
        elif timeframe == TradeTimeframe.SWING:
            expires_at = now + timedelta(days=3)
        else:
            expires_at = now + timedelta(days=7)

        return TradeIdea(
            id=uuid4(),
            timestamp=now,
            symbol=symbol,
            exchange="NSE",
            direction=TradeDirection(llm_output.get("direction", "NEUTRAL")),
            confidence_band=confidence_band,
            timeframe=timeframe,
            regime=regime,
            reasoning=reasoning,
            suggested_entry=entry_plan,
            invalidation=llm_output.get("invalidation", "Trade setup no longer valid"),
            expires_at=expires_at,
            status=IdeaStatus.PENDING,
        )

    async def _rule_based_reasoning(
        self,
        indicator_output: IndicatorOutput,
        market_context: Optional[MarketContext],
    ) -> TradeIdea:
        """
        Fallback rule-based analysis when LLM is unavailable.

        Uses simple technical rules to generate trade ideas.
        """
        now = datetime.now(IST)
        symbol = indicator_output.symbol
        price = indicator_output.price
        indicators = indicator_output.indicators
        risk_metrics = indicator_output.risk_metrics

        trend = indicators.get("trend", {})
        momentum = indicators.get("momentum", {})

        # Determine direction based on simple rules
        rsi = momentum.get("rsi_14", 50)
        trend_dir = trend.get("trend_direction", "SIDEWAYS")
        ema_9 = trend.get("ema_9", price.current)
        ema_21 = trend.get("ema_21", price.current)

        primary_factors = []
        concerns = []

        # Direction logic
        if trend_dir == "BULLISH" and price.current > ema_21 and rsi < 70:
            direction = TradeDirection.LONG
            primary_factors.append("Price in bullish trend above EMAs")
            primary_factors.append(f"RSI at {rsi:.1f} - momentum positive without overbought")
            concerns.append("Trend could reverse at any time")
            concerns.append("Broader market conditions could change")
        elif trend_dir == "BEARISH" and price.current < ema_21 and rsi > 30:
            direction = TradeDirection.SHORT
            primary_factors.append("Price in bearish trend below EMAs")
            primary_factors.append(f"RSI at {rsi:.1f} - momentum negative without oversold")
            concerns.append("Counter-trend rallies possible")
            concerns.append("News events could trigger reversals")
        else:
            direction = TradeDirection.NEUTRAL
            primary_factors.append("No clear directional bias")
            concerns.append("Sideways markets are difficult to trade")
            concerns.append("Wait for clearer setup")

        # Confidence based on confluence
        if direction == TradeDirection.NEUTRAL:
            confidence = ConfidenceBand(low=0.40, mid=0.45, high=0.50)
        else:
            # Check for confluences
            confluences = []
            macd = momentum.get("macd", {})
            if macd.get("histogram", 0) > 0 and direction == TradeDirection.LONG:
                confluences.append("MACD histogram positive")
            elif macd.get("histogram", 0) < 0 and direction == TradeDirection.SHORT:
                confluences.append("MACD histogram negative")

            vol_ratio = indicators.get("volume", {}).get("volume_ratio", 1)
            if vol_ratio > 1.2:
                confluences.append("Above average volume confirming move")

            if len(confluences) >= 2:
                confidence = ConfidenceBand(low=0.55, mid=0.62, high=0.68)
            elif len(confluences) == 1:
                confidence = ConfidenceBand(low=0.52, mid=0.58, high=0.64)
            else:
                confidence = ConfidenceBand(low=0.50, mid=0.55, high=0.60)

        # Determine volatility level
        atr_pct = risk_metrics.atr_percent
        if atr_pct < 1.0:
            vol_level = VolatilityLevel.LOW
        elif atr_pct < 2.5:
            vol_level = VolatilityLevel.NORMAL
        elif atr_pct < 4.0:
            vol_level = VolatilityLevel.HIGH
        else:
            vol_level = VolatilityLevel.EXTREME

        # Build trade idea
        regime = MarketRegime(
            trend=TrendType(trend_dir),
            volatility=vol_level,
            momentum=MomentumLevel.MODERATE,
        )

        reasoning = TradeReasoning(
            primary_factors=primary_factors or ["Rule-based analysis"],
            confluences=confluences if 'confluences' in dir() and confluences else [],
            concerns=concerns or ["Market conditions can change rapidly"],
        )

        entry_plan = EntryPlan(
            entry_type=EntryType.LIMIT,
            entry_price=price.current,
        )

        # Invalidation based on direction
        if direction == TradeDirection.LONG:
            invalidation = f"Close below ₹{risk_metrics.suggested_sl:.2f} invalidates bullish thesis"
        elif direction == TradeDirection.SHORT:
            sl_price = price.current * 1.02  # Rough SL for short
            invalidation = f"Close above ₹{sl_price:.2f} invalidates bearish thesis"
        else:
            invalidation = "Wait for trend to establish before taking positions"

        return TradeIdea(
            id=uuid4(),
            timestamp=now,
            symbol=symbol,
            exchange="NSE",
            direction=direction,
            confidence_band=confidence,
            timeframe=TradeTimeframe.SWING,
            regime=regime,
            reasoning=reasoning,
            suggested_entry=entry_plan,
            invalidation=invalidation,
            expires_at=now + timedelta(days=3),
            status=IdeaStatus.PENDING,
        )

    async def health_check(self) -> bool:
        """Check LLM API connectivity."""
        try:
            return await self.llm_client.health_check()
        except Exception:
            return False


# Singleton instance
_service_instance: Optional[ReasoningService] = None


def get_reasoning_service() -> ReasoningService:
    """Get or create reasoning service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = ReasoningService()
    return _service_instance
