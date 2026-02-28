"""
LLM Prompt Templates

Structured prompts for reasoning and explanation layers.

CRITICAL RULES (enforced in all prompts):
- LLM does NO math - all numbers come from indicator data
- Always express uncertainty with probability ranges
- Always include concerns/risks
- Never claim certainty or guarantee profits
"""

# =============================================================================
# REASONING LAYER PROMPTS (Claude Opus / GPT-4)
# =============================================================================

REASONING_SYSTEM_PROMPT = """You are an expert technical analyst assistant for Indian stock markets (NSE/BSE).

YOUR ROLE:
- Analyze technical indicators and market data
- Generate trade ideas with probabilistic confidence
- Identify market regime (trend, volatility, momentum)
- Find confluence factors and express concerns

CRITICAL RULES:
1. NEVER do math - all numbers are provided to you. Do not calculate anything.
2. ALWAYS express confidence as a RANGE (low/mid/high), never a single number.
3. ALWAYS include concerns - no trade setup is certain.
4. NEVER claim certainty, guaranteed profits, or "sure thing".
5. Use probabilistic language: "likely", "suggests", "historical patterns indicate".
6. If data is insufficient or conflicting, say NEUTRAL with explanation.

OUTPUT FORMAT:
You must respond with valid JSON matching the TradeIdea schema.
Include all required fields: direction, confidence_band, timeframe, regime, reasoning, suggested_entry, invalidation.

CONFIDENCE BANDS:
- low: Conservative estimate (worst case if setup works)
- mid: Base case expectation
- high: Optimistic estimate (best case)
- Typical range: 0.50-0.75 (never above 0.80 - nothing is that certain)

REMEMBER: You are providing analysis, not financial advice. The human makes all final decisions."""

REASONING_USER_PROMPT_TEMPLATE = """Analyze the following technical data for {symbol} and generate a trade idea.

CURRENT PRICE DATA:
- Current: ₹{current_price}
- Open: ₹{open_price}
- High: ₹{high_price}
- Low: ₹{low_price}
- Previous Close: ₹{prev_close}
- Change: {change_percent}%
- Volume: {volume} (Avg 20-day: {avg_volume})

TREND INDICATORS:
- EMA 9: ₹{ema_9}
- EMA 21: ₹{ema_21}
- EMA 50: ₹{ema_50}
- EMA 200: ₹{ema_200}
- SMA 20: ₹{sma_20}
- Trend Direction: {trend_direction}
- Trend Strength (ADX): {adx}
- +DI: {plus_di}, -DI: {minus_di}

MOMENTUM INDICATORS:
- RSI (14): {rsi}
- MACD Line: {macd_line}
- MACD Signal: {macd_signal}
- MACD Histogram: {macd_histogram}
- MACD Crossover: {macd_crossover}
- Stochastic K: {stoch_k}, D: {stoch_d}, Zone: {stoch_zone}

VOLATILITY INDICATORS:
- ATR (14): ₹{atr} ({atr_percent}% of price)
- Bollinger Upper: ₹{bb_upper}
- Bollinger Middle: ₹{bb_middle}
- Bollinger Lower: ₹{bb_lower}
- %B: {percent_b}
- Volatility Zone: {volatility_zone}

VOLUME INDICATORS:
- VWAP: ₹{vwap}
- VWAP Deviation: {vwap_deviation}%
- Volume Ratio: {volume_ratio}x average

SUPPORT/RESISTANCE LEVELS:
- Support: {support_levels}
- Resistance: {resistance_levels}
- Pivot: ₹{pivot}
- R1: ₹{r1}, R2: ₹{r2}
- S1: ₹{s1}, S2: ₹{s2}

RISK METRICS (Pre-calculated):
- Suggested Stop Loss: ₹{suggested_sl} ({sl_percent}% below entry)
- Suggested Take Profits: {suggested_tp}
- Risk/Reward Ratios: {rr_ratios}

{market_context}

Based on this data, generate a trade idea in the following JSON format:
{{
    "direction": "LONG" | "SHORT" | "NEUTRAL",
    "confidence_band": {{
        "low": 0.XX,
        "mid": 0.XX,
        "high": 0.XX
    }},
    "timeframe": "INTRADAY" | "SWING" | "POSITIONAL",
    "regime": {{
        "trend": "BULLISH" | "BEARISH" | "SIDEWAYS",
        "volatility": "LOW" | "NORMAL" | "HIGH" | "EXTREME",
        "momentum": "STRONG" | "MODERATE" | "WEAK" | "DIVERGING"
    }},
    "reasoning": {{
        "primary_factors": ["reason1", "reason2", ...],
        "confluences": ["factor1", "factor2", ...],
        "concerns": ["concern1", "concern2", ...]
    }},
    "suggested_entry": {{
        "entry_type": "MARKET" | "LIMIT" | "STOP_LIMIT",
        "entry_price": 1234.50,
        "entry_zone": {{"low": 1230.0, "high": 1240.0}},
        "trigger_condition": "optional trigger description"
    }},
    "invalidation": "Clear description of what would invalidate this trade thesis"
}}

IMPORTANT: Your confidence band should reflect realistic probabilities based on the technical setup. Most setups have 55-70% historical success rates. Be conservative."""


# =============================================================================
# EXPLANATION LAYER PROMPTS (Claude Haiku / GPT-3.5)
# =============================================================================

EXPLANATION_SYSTEM_PROMPT = """You are a trading assistant that explains trade ideas in plain English for Indian retail traders.

YOUR ROLE:
- Convert technical analysis into easy-to-understand explanations
- Write clear risk disclosures
- List what could go wrong
- Provide a checklist for the human to verify

CRITICAL RULES:
1. Use simple, non-technical language where possible
2. ALWAYS include risk disclosure - trading involves risk of loss
3. ALWAYS explain "what could go wrong"
4. NEVER promise profits or guarantee outcomes
5. Use Indian context (INR, NSE, market hours, etc.)
6. Be honest about uncertainty

TONE:
- Helpful and educational
- Honest about risks
- Empowering the human to make their own decision
- Not pushy or promotional

OUTPUT FORMAT:
You must respond with valid JSON matching the TradeExplanation schema.
Include all required fields: summary, rationale, risk_disclosure, what_could_go_wrong, alternative_scenarios, confidence_statement, human_checklist."""

EXPLANATION_USER_PROMPT_TEMPLATE = """Generate a human-readable explanation for this trade suggestion.

TRADE IDEA:
- Symbol: {symbol}
- Direction: {direction}
- Confidence Range: {confidence_low}-{confidence_high} (base: {confidence_mid})
- Timeframe: {timeframe}
- Market Regime: {trend} trend, {volatility} volatility, {momentum} momentum

REASONING PROVIDED:
- Primary Factors: {primary_factors}
- Confluences: {confluences}
- Concerns: {concerns}

ENTRY PLAN:
- Entry Type: {entry_type}
- Entry Price/Zone: {entry_price}
- Invalidation: {invalidation}

RISK PLAN (from Risk Engine):
- Validation Status: {validation_status}
- Position Size: {position_size} shares
- Position Value: ₹{position_value}
- Max Loss Amount: ₹{max_loss_amount}
- Max Loss Percent: {max_loss_percent}%
- Stop Loss: ₹{stop_loss}
- Take Profit Targets: {take_profit_targets}
- Risk/Reward Ratio: {risk_reward_ratio}

PORTFOLIO IMPACT:
- Current Exposure: {current_exposure}%
- New Exposure (if taken): {new_exposure}%

RISK WARNINGS FROM SYSTEM:
{risk_warnings}

Generate an explanation in the following JSON format:
{{
    "summary": "1-2 sentence summary of the trade suggestion",
    "rationale": "Detailed explanation in plain English (100-300 words)",
    "risk_disclosure": "Mandatory risk warning (50-100 words)",
    "what_could_go_wrong": ["risk1", "risk2", "risk3", ...],
    "alternative_scenarios": [
        {{
            "scenario": "Description of what could happen",
            "probability": "XX%" or "Low/Medium/High",
            "outcome": "What happens to the trade",
            "action": "What the trader should do"
        }}
    ],
    "confidence_statement": "Statement about probability, NOT certainty",
    "human_checklist": ["item1", "item2", "item3", ...]
}}

IMPORTANT:
- The risk_disclosure must mention the specific amount at risk (₹{max_loss_amount})
- Include at least 3 things that could go wrong
- Include at least 2 alternative scenarios
- The checklist should include practical items the trader can verify"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_reasoning_prompt(
    symbol: str,
    indicator_output: dict,
    market_context: dict = None,
) -> str:
    """Format the reasoning prompt with indicator data."""

    price = indicator_output.get("price", {})
    indicators = indicator_output.get("indicators", {})
    trend = indicators.get("trend", {})
    momentum = indicators.get("momentum", {})
    volatility = indicators.get("volatility", {})
    volume = indicators.get("volume", {})
    levels = indicator_output.get("levels", {})
    risk_metrics = indicator_output.get("risk_metrics", {})
    macd = momentum.get("macd", {})
    stoch = momentum.get("stochastic", {})
    bb = volatility.get("bollinger_bands", {})
    pivots = levels.get("pivot_points", {})

    context_str = ""
    if market_context:
        context_parts = []
        if market_context.get("global_sentiment"):
            context_parts.append(f"Global Sentiment: {market_context['global_sentiment']}")
        if market_context.get("sector_sentiment"):
            context_parts.append(f"Sector Sentiment: {market_context['sector_sentiment']}")
        if market_context.get("recent_news_summary"):
            context_parts.append(f"Recent News: {market_context['recent_news_summary']}")
        if market_context.get("earnings_nearby"):
            context_parts.append("⚠️ Earnings announcement nearby")
        if market_context.get("major_event_nearby"):
            context_parts.append(f"⚠️ Major event: {market_context.get('event_description', 'Unknown')}")
        if context_parts:
            context_str = "MARKET CONTEXT:\n" + "\n".join(f"- {p}" for p in context_parts)

    return REASONING_USER_PROMPT_TEMPLATE.format(
        symbol=symbol,
        current_price=price.get("current", 0),
        open_price=price.get("open", 0),
        high_price=price.get("high", 0),
        low_price=price.get("low", 0),
        prev_close=price.get("previous_close", 0),
        change_percent=round(price.get("change_percent", 0), 2),
        volume=price.get("volume", 0),
        avg_volume=price.get("avg_volume", 0),
        ema_9=trend.get("ema_9", 0),
        ema_21=trend.get("ema_21", 0),
        ema_50=trend.get("ema_50", 0),
        ema_200=trend.get("ema_200", 0),
        sma_20=trend.get("sma_20", 0),
        trend_direction=trend.get("trend_direction", "UNKNOWN"),
        adx=trend.get("adx", 0),
        plus_di=trend.get("plus_di", 0),
        minus_di=trend.get("minus_di", 0),
        rsi=momentum.get("rsi_14", 50),
        macd_line=macd.get("macd_line", 0),
        macd_signal=macd.get("signal_line", 0),
        macd_histogram=macd.get("histogram", 0),
        macd_crossover=macd.get("crossover", "NONE"),
        stoch_k=stoch.get("k", 50) if stoch else 50,
        stoch_d=stoch.get("d", 50) if stoch else 50,
        stoch_zone=stoch.get("zone", "NEUTRAL") if stoch else "NEUTRAL",
        atr=risk_metrics.get("atr", 0),
        atr_percent=risk_metrics.get("atr_percent", 0),
        bb_upper=bb.get("upper", 0),
        bb_middle=bb.get("middle", 0),
        bb_lower=bb.get("lower", 0),
        percent_b=bb.get("percent_b", 0.5),
        volatility_zone=risk_metrics.get("volatility_zone", "NORMAL"),
        vwap=volume.get("vwap", 0),
        vwap_deviation=volume.get("vwap_deviation", 0),
        volume_ratio=volume.get("volume_ratio", 1),
        support_levels=", ".join(f"₹{s}" for s in levels.get("support", [])),
        resistance_levels=", ".join(f"₹{r}" for r in levels.get("resistance", [])),
        pivot=pivots.get("pivot", 0),
        r1=pivots.get("r1", 0),
        r2=pivots.get("r2", 0),
        s1=pivots.get("s1", 0),
        s2=pivots.get("s2", 0),
        suggested_sl=risk_metrics.get("suggested_sl", 0),
        sl_percent=risk_metrics.get("suggested_sl_percent", 0),
        suggested_tp=", ".join(f"₹{t}" for t in risk_metrics.get("suggested_tp", [])),
        rr_ratios=", ".join(f"{r}:1" for r in risk_metrics.get("risk_reward_ratios", [])),
        market_context=context_str,
    )


def format_explanation_prompt(
    trade_idea: dict,
    risk_plan: dict,
) -> str:
    """Format the explanation prompt with trade and risk data."""

    reasoning = trade_idea.get("reasoning", {})
    entry = trade_idea.get("suggested_entry", {})
    regime = trade_idea.get("regime", {})
    confidence = trade_idea.get("confidence_band", {})
    approved_plan = risk_plan.get("approved_plan", {})
    portfolio_impact = risk_plan.get("portfolio_impact", {})

    # Format take profit targets
    tp_targets = approved_plan.get("take_profit", [])
    if isinstance(tp_targets, list) and tp_targets:
        if isinstance(tp_targets[0], dict):
            tp_str = ", ".join(f"₹{t['price']} ({t.get('exit_percent', 100)}%)" for t in tp_targets)
        else:
            tp_str = ", ".join(f"₹{t}" for t in tp_targets)
    else:
        tp_str = "Not specified"

    # Format entry price/zone
    entry_price = entry.get("entry_price")
    entry_zone = entry.get("entry_zone")
    if entry_price:
        entry_str = f"₹{entry_price}"
    elif entry_zone:
        entry_str = f"₹{entry_zone['low']} - ₹{entry_zone['high']}"
    else:
        entry_str = "Market price"

    return EXPLANATION_USER_PROMPT_TEMPLATE.format(
        symbol=trade_idea.get("symbol", "UNKNOWN"),
        direction=trade_idea.get("direction", "NEUTRAL"),
        confidence_low=confidence.get("low", 0.5),
        confidence_mid=confidence.get("mid", 0.55),
        confidence_high=confidence.get("high", 0.6),
        timeframe=trade_idea.get("timeframe", "INTRADAY"),
        trend=regime.get("trend", "SIDEWAYS"),
        volatility=regime.get("volatility", "NORMAL"),
        momentum=regime.get("momentum", "MODERATE"),
        primary_factors="\n  - ".join(reasoning.get("primary_factors", ["No factors provided"])),
        confluences="\n  - ".join(reasoning.get("confluences", ["None"])),
        concerns="\n  - ".join(reasoning.get("concerns", ["No concerns listed"])),
        entry_type=entry.get("entry_type", "MARKET"),
        entry_price=entry_str,
        invalidation=trade_idea.get("invalidation", "Not specified"),
        validation_status=risk_plan.get("validation_status", "PENDING"),
        position_size=approved_plan.get("position_size", 0),
        position_value=approved_plan.get("position_value", 0),
        max_loss_amount=approved_plan.get("max_loss_amount", 0),
        max_loss_percent=approved_plan.get("max_loss_percent", 0),
        stop_loss=approved_plan.get("stop_loss", 0),
        take_profit_targets=tp_str,
        risk_reward_ratio=approved_plan.get("risk_reward_ratio", 0),
        current_exposure=portfolio_impact.get("current_exposure_percent", 0),
        new_exposure=portfolio_impact.get("new_exposure_percent", 0),
        risk_warnings="\n".join(f"- {w}" for w in risk_plan.get("risk_warnings", [])),
    )
