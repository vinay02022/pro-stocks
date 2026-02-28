# StockPro Module Contracts

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                       │
│                         UI Only - API Consumer                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP/JSON
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (Python FastAPI)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │    Data      │    │  Indicator   │    │   Strategy   │       │
│  │  Ingestion   │───▶│   Engine     │───▶│   Service    │       │
│  │  Service     │    │  (Python)    │    │ (Orchestrator)│      │
│  └──────────────┘    └──────────────┘    └──────┬───────┘       │
│         │                   │                    │               │
│         │                   │           ┌───────┴───────┐       │
│         ▼                   ▼           ▼               ▼       │
│  ┌──────────────┐    ┌──────────────┐  ┌─────────┐ ┌─────────┐ │
│  │ External APIs│    │    Redis     │  │Reasoning│ │  Risk   │ │
│  │ Groww/Angel  │    │    Cache     │  │   LLM   │ │ Engine  │ │
│  └──────────────┘    └──────────────┘  └────┬────┘ └────┬────┘ │
│                                              │          │       │
│                                              ▼          │       │
│                                        ┌─────────┐     │       │
│                                        │Explanat.│◀────┘       │
│                                        │   LLM   │             │
│                                        └─────────┘             │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                      PostgreSQL                           │  │
│  │         (Users, Portfolios, Trades, Ideas)               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Contract 1: Data Ingestion Service

**Location:** `app/services/data_ingestion/`

### Input: `DataRequest`

```python
{
    "symbols": ["RELIANCE", "NIFTY"],      # Required: 1-50 symbols
    "data_types": ["OHLCV"],               # OHLCV, OPTIONS_CHAIN, NEWS
    "timeframe": "15m",                     # 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w
    "lookback": 100,                        # 1-1000 candles
    "include_options": false,
    "include_news": false,
    "options_expiry": null                  # YYYY-MM-DD if needed
}
```

### Output: `MarketSnapshot`

```python
{
    "timestamp": "2024-02-04T10:30:00+05:30",
    "symbols": [
        {
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "timeframe": "15m",
            "ohlcv": [
                {"timestamp": "...", "open": 2440, "high": 2455, "low": 2438, "close": 2450, "volume": 100000}
            ],
            "current_price": 2450.50,
            "day_change_percent": 1.25
        }
    ],
    "options_chain": null,  # OptionsChainData if requested
    "news": null,           # List[NewsItem] if requested
    "metadata": {
        "source": "Groww, AngelOne",
        "latency_ms": 245,
        "is_market_open": true,
        "market_phase": "open",
        "last_updated": "2024-02-04T10:30:00+05:30"
    }
}
```

### Responsibilities:

- Fetch from Groww API (equities, indices)
- Fetch from Angel One API (options chain)
- Fetch from News API
- Rate limiting per API
- Redis caching (60s for quotes, 180s for options)
- Data normalization to standard schema

### NO LLM - Pure data fetching

---

## Contract 2: Indicator Engine

**Location:** `app/services/indicators/`

### Input: `MarketSnapshot` (with OHLCV data)

### Output: `IndicatorOutput`

```python
{
    "symbol": "RELIANCE",
    "timestamp": "2024-02-04T10:30:00+05:30",
    "price": {
        "current": 2450.50,
        "open": 2440.00,
        "high": 2465.00,
        "low": 2435.00,
        "previous_close": 2420.00,
        "change": 30.50,
        "change_percent": 1.26,
        "volume": 5000000
    },
    "indicators": {
        "trend": {
            "ema_9": 2448.0,
            "ema_21": 2442.0,
            "ema_50": 2430.0,
            "ema_200": 2380.0,
            "sma_20": 2445.0,
            "sma_50": 2425.0,
            "sma_200": 2350.0,
            "trend_direction": "BULLISH",
            "trend_strength": 65.0,
            "adx": 28.5,
            "plus_di": 32.0,
            "minus_di": 18.0
        },
        "momentum": {
            "rsi_14": 62.5,
            "rsi_divergence": null,
            "macd": {
                "macd_line": 12.5,
                "signal_line": 10.2,
                "histogram": 2.3,
                "crossover": "BULLISH"
            },
            "stochastic": {"k": 72.0, "d": 68.0, "zone": "NEUTRAL"}
        },
        "volatility": {
            "atr_14": 45.2,
            "atr_percent": 1.85,
            "bollinger_bands": {
                "upper": 2510.0,
                "middle": 2445.0,
                "lower": 2380.0,
                "bandwidth": 0.053,
                "percent_b": 0.54
            }
        },
        "volume": {
            "current_volume": 5000000,
            "avg_volume_20": 4200000,
            "volume_ratio": 1.19,
            "vwap": 2452.30,
            "vwap_deviation": -0.07
        }
    },
    "levels": {
        "support": [2420, 2380, 2340],
        "resistance": [2480, 2520, 2580],
        "pivot_points": {
            "pivot": 2440,
            "r1": 2465, "r2": 2490, "r3": 2515,
            "s1": 2415, "s2": 2390, "s3": 2365,
            "type": "standard"
        },
        "day_high": 2465,
        "day_low": 2435
    },
    "risk_metrics": {
        "atr": 45.2,
        "atr_percent": 1.85,
        "suggested_sl": 2405.0,
        "suggested_sl_percent": 1.86,
        "suggested_tp": [2500, 2550, 2600],
        "risk_reward_ratios": [1.1, 2.2, 3.3],
        "position_sizing": {
            "recommended_shares": 40,
            "recommended_value": 98000,
            "risk_amount": 1800,
            "risk_percent": 1.0,
            "method": "ATR"
        },
        "volatility_zone": "NORMAL"
    }
}
```

### Responsibilities:

- Calculate ALL technical indicators
- Detect support/resistance levels
- Calculate pivot points
- Compute ATR-based stop loss
- Position sizing recommendations
- Risk-reward calculations

### NO LLM - Pure Python/NumPy calculations

---

## Contract 3: Reasoning LLM Service

**Location:** `app/services/llm/`

### Input: `IndicatorOutput` + `MarketContext`

### Output: `TradeIdea`

```python
{
    "id": "uuid-here",
    "timestamp": "2024-02-04T10:35:00+05:30",
    "symbol": "RELIANCE",
    "exchange": "NSE",
    "direction": "LONG",           # LONG, SHORT, NEUTRAL
    "confidence_band": {
        "low": 0.55,               # Conservative estimate
        "mid": 0.65,               # Base case
        "high": 0.72               # Optimistic estimate
    },
    "timeframe": "SWING",          # INTRADAY, SWING, POSITIONAL
    "regime": {
        "trend": "BULLISH",
        "volatility": "NORMAL",
        "momentum": "MODERATE"
    },
    "reasoning": {
        "primary_factors": [
            "Price above all major EMAs indicating strong uptrend",
            "RSI at 62 shows momentum without being overbought"
        ],
        "confluences": [
            "Volume 19% above average confirming move",
            "Sector showing relative strength"
        ],
        "concerns": [                # MUST always have concerns
            "Resistance at 2500 tested twice before",
            "Broader market showing weakness",
            "Earnings in 2 weeks could add volatility"
        ]
    },
    "suggested_entry": {
        "entry_type": "LIMIT",
        "entry_price": 2440.0,
        "entry_zone": {"low": 2430, "high": 2450}
    },
    "invalidation": "Close below 2380 would invalidate the bullish thesis",
    "expires_at": "2024-02-04T15:30:00+05:30",
    "status": "PENDING"
}
```

### Responsibilities:

- Market regime detection
- Trade suitability analysis
- Strategy selection
- Confluence analysis
- Generate reasoning with concerns

### USES LLM (GPT-5/Opus) for reasoning

### NEVER does math - all numbers from IndicatorOutput

---

## Contract 4: Risk Validation Engine

**Location:** `app/services/risk/`

### Input: `TradeIdea` + `PortfolioState` + `RiskConfig`

### Output: `RiskPlan`

```python
{
    "trade_id": "uuid-matching-trade-idea",
    "validation_status": "APPROVED",    # APPROVED, REJECTED, MODIFIED
    "rejection_reasons": null,          # List if REJECTED
    "approved_plan": {
        "position_size": 40,
        "position_value": 98000,
        "max_loss_amount": 2800,
        "max_loss_percent": 1.4,
        "risk_reward_ratio": 2.5,
        "stop_loss": 2380,
        "take_profit": [
            {"price": 2520, "exit_percent": 50, "label": "TP1"},
            {"price": 2600, "exit_percent": 50, "label": "TP2"}
        ],
        "trailing_stop": {
            "activation_price": 2520,
            "trail_percent": 2.0
        }
    },
    "portfolio_impact": {
        "current_exposure_percent": 35,
        "new_exposure_percent": 40,
        "sector_exposure": {"Oil & Gas": 15},
        "correlation_warning": null,
        "max_drawdown_if_all_sl_hit": 4.2
    },
    "risk_warnings": [                   # MUST always have warnings
        "Position at maximum allowed size for single stock",
        "Earnings announcement in 2 weeks"
    ]
}
```

### Validation Rules (checked in order):

1. Max position size (default 5%)
2. Max sector exposure (default 25%)
3. Max portfolio exposure (default 50%)
4. Max daily trades (default 10)
5. Daily loss limit (default 2%)
6. Drawdown limit (default 10%)
7. Min risk-reward ratio (default 1.5)
8. Correlation with existing positions
9. Market hours check
10. Liquidity check

### If ANY rule fails → REJECTED (no exceptions)

### NO LLM - Pure deterministic Python logic

---

## Contract 5: Explanation LLM Service

**Location:** `app/services/llm/`

### Input: `ValidatedTrade` (TradeIdea + RiskPlan)

### Output: `TradeExplanation`

```python
{
    "trade_id": "uuid-here",
    "timestamp": "2024-02-04T10:40:00+05:30",
    "summary": "RELIANCE shows bullish momentum with price above key moving averages. Consider a swing long position with defined risk.",
    "rationale": "The stock has been consolidating above the 21 EMA and recently broke out of a 3-day range with above-average volume. RSI at 62 shows momentum without being overbought...",
    "risk_disclosure": "This is a SUGGESTION based on technical analysis, not financial advice. Past patterns do not guarantee future results. You could lose ₹2,800 (1.4% of portfolio) if stop loss is hit.",
    "what_could_go_wrong": [
        "Broader market selloff could drag the stock down",
        "Resistance at 2500 may hold, causing reversal",
        "Unexpected negative news about the company"
    ],
    "alternative_scenarios": [
        {
            "scenario": "Price reverses at 2500 resistance",
            "probability": "35%",
            "outcome": "Trade hits stop loss at 2380",
            "action": "Accept loss, do not average down"
        },
        {
            "scenario": "Sideways consolidation",
            "probability": "25%",
            "outcome": "Price stays between 2420-2500",
            "action": "Consider time-based exit after 5 days"
        }
    ],
    "confidence_statement": "Based on backtesting similar setups, approximately 62% reached first target. This is a probability, not a guarantee.",
    "human_checklist": [
        "Check for company announcements this week",
        "Verify current price is still in entry zone",
        "Confirm sufficient capital for position",
        "Set stop loss order immediately after entry"
    ]
}
```

### Responsibilities:

- Human-readable summary
- Plain English rationale
- Mandatory risk disclosure
- "What could go wrong" scenarios
- Human verification checklist

### USES LLM (GPT-3.5/Haiku) - cheaper, faster

### NEVER claims certainty

---

## API Endpoints Summary

| Endpoint                             | Method  | Input               | Output                  |
| ------------------------------------ | ------- | ------------------- | ----------------------- |
| `/api/v1/market/snapshot`            | POST    | DataRequest         | MarketSnapshot          |
| `/api/v1/market/quote/{symbol}`      | GET     | -                   | QuickQuote              |
| `/api/v1/indicators/{symbol}`        | GET     | timeframe, lookback | IndicatorOutput         |
| `/api/v1/strategy/analyze`           | POST    | AnalyzeRequest      | TradeSuggestionResponse |
| `/api/v1/portfolio/{id}`             | GET     | -                   | PortfolioState          |
| `/api/v1/portfolio/{id}/risk-config` | GET/PUT | RiskConfig          | RiskConfig              |

---

## Key Principles

1. **AI suggests, human executes** - No auto-trading
2. **Probabilistic confidence** - Ranges, not certainty
3. **Risk-first** - All trades validated against hard limits
4. **LLM for reasoning only** - Never for math
5. **Deterministic risk engine** - No LLM in risk validation
6. **Always include concerns** - Nothing is guaranteed
