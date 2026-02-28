"""
Mock Data Generator

Generates realistic mock market data for development and testing.
"""

import random
from datetime import datetime, timedelta
from typing import Optional

from app.schemas.market import (
    OHLCV,
    SymbolData,
    OptionLeg,
    StrikeData,
    OptionsChainData,
    NewsItem,
    Timeframe,
    Exchange,
    NewsSentiment,
)


# Base prices for common symbols
SYMBOL_BASE_PRICES = {
    "RELIANCE": 2450.0,
    "TCS": 3800.0,
    "INFY": 1500.0,
    "HDFCBANK": 1650.0,
    "ICICIBANK": 1050.0,
    "SBIN": 750.0,
    "ITC": 440.0,
    "TATAMOTORS": 950.0,
    "WIPRO": 480.0,
    "BHARTIARTL": 1150.0,
    "NIFTY": 22000.0,
    "BANKNIFTY": 47000.0,
    "FINNIFTY": 21500.0,
}

# Sector mapping
SYMBOL_SECTORS = {
    "RELIANCE": "Oil & Gas",
    "TCS": "IT",
    "INFY": "IT",
    "HDFCBANK": "Banking",
    "ICICIBANK": "Banking",
    "SBIN": "Banking",
    "ITC": "FMCG",
    "TATAMOTORS": "Auto",
    "WIPRO": "IT",
    "BHARTIARTL": "Telecom",
}

# Timeframe to milliseconds
TIMEFRAME_MS = {
    Timeframe.M1: 60_000,
    Timeframe.M5: 300_000,
    Timeframe.M15: 900_000,
    Timeframe.M30: 1_800_000,
    Timeframe.H1: 3_600_000,
    Timeframe.H4: 14_400_000,
    Timeframe.D1: 86_400_000,
    Timeframe.W1: 604_800_000,
}


def get_base_price(symbol: str) -> float:
    """Get base price for a symbol."""
    return SYMBOL_BASE_PRICES.get(symbol, 1000.0 + random.random() * 1000)


def generate_mock_ohlcv(
    symbol: str,
    timeframe: Timeframe,
    lookback: int,
    end_time: Optional[datetime] = None,
) -> list[OHLCV]:
    """Generate mock OHLCV candles."""
    if end_time is None:
        end_time = datetime.now()

    candles = []
    interval_ms = TIMEFRAME_MS[timeframe]
    price = get_base_price(symbol)
    volatility = price * 0.02  # 2% volatility

    timestamp = end_time - timedelta(milliseconds=interval_ms * lookback)

    for _ in range(lookback):
        # Random walk
        change = (random.random() - 0.5) * volatility

        open_price = price
        close_price = open_price + change
        high_price = max(open_price, close_price) + random.random() * volatility * 0.5
        low_price = min(open_price, close_price) - random.random() * volatility * 0.5

        candles.append(
            OHLCV(
                timestamp=timestamp,
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(close_price, 2),
                volume=random.randint(100_000, 5_000_000),
            )
        )

        price = close_price
        timestamp += timedelta(milliseconds=interval_ms)

    return candles


def generate_mock_symbol_data(
    symbol: str,
    timeframe: Timeframe = Timeframe.M15,
    lookback: int = 100,
) -> SymbolData:
    """Generate complete mock symbol data."""
    ohlcv = generate_mock_ohlcv(symbol, timeframe, lookback)
    current_price = ohlcv[-1].close if ohlcv else get_base_price(symbol)
    prev_close = ohlcv[-2].close if len(ohlcv) > 1 else current_price
    day_change = ((current_price - prev_close) / prev_close) * 100

    return SymbolData(
        symbol=symbol,
        exchange=Exchange.NSE,
        timeframe=timeframe,
        ohlcv=ohlcv,
        current_price=round(current_price, 2),
        day_change_percent=round(day_change, 2),
        bid=round(current_price - 0.05, 2),
        ask=round(current_price + 0.05, 2),
        bid_qty=random.randint(100, 10000),
        ask_qty=random.randint(100, 10000),
    )


def generate_mock_options_chain(
    underlying: str,
    expiry: str,
    num_strikes: int = 21,
) -> OptionsChainData:
    """Generate mock options chain data."""
    spot_price = get_base_price(underlying)

    # Determine strike gap based on underlying
    if underlying in ("NIFTY", "BANKNIFTY", "FINNIFTY"):
        strike_gap = 100 if spot_price > 10000 else 50
    else:
        strike_gap = 50 if spot_price > 1000 else 25

    # Calculate ATM strike
    atm_strike = round(spot_price / strike_gap) * strike_gap

    # Generate strikes around ATM
    half_strikes = num_strikes // 2
    strikes = []
    total_call_oi = 0
    total_put_oi = 0

    for i in range(-half_strikes, half_strikes + 1):
        strike_price = atm_strike + (i * strike_gap)
        distance_from_atm = abs(i)

        # ITM/OTM determination
        is_call_itm = strike_price < spot_price
        is_put_itm = strike_price > spot_price

        call_leg = _generate_option_leg(
            spot_price, strike_price, "CE", is_call_itm, distance_from_atm
        )
        put_leg = _generate_option_leg(
            spot_price, strike_price, "PE", is_put_itm, distance_from_atm
        )

        total_call_oi += call_leg.oi
        total_put_oi += put_leg.oi

        strikes.append(
            StrikeData(
                strike=strike_price,
                call=call_leg,
                put=put_leg,
            )
        )

    # PCR calculation
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0

    # Max pain (simplified - strike with lowest total pain)
    max_pain_strike = _calculate_max_pain(strikes, spot_price)

    return OptionsChainData(
        underlying=underlying,
        spot_price=spot_price,
        expiry_dates=[expiry],  # Would normally have multiple
        selected_expiry=expiry,
        strikes=strikes,
        atm_strike=atm_strike,
        pcr=round(pcr, 2),
        max_pain_strike=max_pain_strike,
    )


def _generate_option_leg(
    spot: float,
    strike: float,
    option_type: str,
    is_itm: bool,
    distance_from_atm: int,
) -> OptionLeg:
    """Generate mock option leg data."""
    # Intrinsic value
    intrinsic = abs(spot - strike) if is_itm else 0

    # Time value (decreases with distance from ATM)
    time_value = max(50 - distance_from_atm * 5, 5) + random.random() * 20
    premium = intrinsic + time_value

    # IV smile effect
    iv = 15 + random.random() * 15 + distance_from_atm * 0.5

    # Greeks
    if option_type == "CE":
        delta = max(0.1, min(0.9, 0.5 + (spot - strike) / (spot * 0.1)))
    else:
        delta = -max(0.1, min(0.9, 0.5 + (strike - spot) / (spot * 0.1)))

    gamma = max(0.001, 0.01 - distance_from_atm * 0.001)
    theta = -(time_value / 30 + random.random() * 5)
    vega = max(0.1, spot * 0.001 - distance_from_atm * 0.01)

    return OptionLeg(
        ltp=round(premium, 2),
        oi=random.randint(10000, 500000) * 50,
        oi_change=random.randint(-50000, 100000),
        volume=random.randint(1000, 200000),
        iv=round(iv, 2),
        delta=round(delta, 3),
        gamma=round(gamma, 4),
        theta=round(theta, 2),
        vega=round(vega, 2),
    )


def _calculate_max_pain(strikes: list[StrikeData], spot: float) -> float:
    """Calculate max pain strike (simplified)."""
    min_pain = float("inf")
    max_pain_strike = spot

    for test_strike in strikes:
        total_pain = 0
        for strike in strikes:
            # Call writer pain
            if strike.call and strike.strike < test_strike.strike:
                total_pain += (test_strike.strike - strike.strike) * strike.call.oi
            # Put writer pain
            if strike.put and strike.strike > test_strike.strike:
                total_pain += (strike.strike - test_strike.strike) * strike.put.oi

        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = test_strike.strike

    return max_pain_strike


# Mock news headlines
MOCK_NEWS_TEMPLATES = [
    ("Markets rally as RBI holds rates steady", NewsSentiment.POSITIVE),
    ("IT stocks surge on strong Q3 earnings expectations", NewsSentiment.POSITIVE),
    ("Banking sector under pressure amid NPA concerns", NewsSentiment.NEGATIVE),
    ("{symbol} announces major expansion plans", NewsSentiment.POSITIVE),
    ("FIIs turn net buyers after 5-week selling spree", NewsSentiment.POSITIVE),
    ("Nifty consolidates near record highs", NewsSentiment.NEUTRAL),
    ("Auto stocks slip on weak monthly sales data", NewsSentiment.NEGATIVE),
    ("Pharma sector gains on FDA approval news", NewsSentiment.POSITIVE),
    ("Global cues weigh on Indian markets", NewsSentiment.NEGATIVE),
    ("SEBI introduces new margin rules for derivatives", NewsSentiment.NEUTRAL),
    ("{symbol} stock in focus after restructuring news", NewsSentiment.NEUTRAL),
    ("Metal stocks rally on China stimulus hopes", NewsSentiment.POSITIVE),
    ("PSU banks gain ahead of disinvestment", NewsSentiment.POSITIVE),
    ("Rupee hits multi-month low against dollar", NewsSentiment.NEGATIVE),
    ("Government announces infrastructure push", NewsSentiment.POSITIVE),
]

NEWS_SOURCES = [
    "Economic Times",
    "Moneycontrol",
    "CNBC-TV18",
    "Business Standard",
    "Mint",
    "Financial Express",
    "Bloomberg Quint",
    "Reuters India",
]


def generate_mock_news(
    symbols: Optional[list[str]] = None,
    count: int = 10,
) -> list[NewsItem]:
    """Generate mock news items."""
    news_items = []
    now = datetime.now()

    for i in range(count):
        template, sentiment = random.choice(MOCK_NEWS_TEMPLATES)

        # Replace {symbol} placeholder if present
        if "{symbol}" in template and symbols:
            symbol = random.choice(symbols)
            headline = template.replace("{symbol}", symbol)
            item_symbols = [symbol]
        else:
            headline = template
            item_symbols = symbols[:2] if symbols else None

        hours_ago = random.randint(0, 24)
        timestamp = now - timedelta(hours=hours_ago)

        news_items.append(
            NewsItem(
                id=f"news-{i}-{random.randint(1000, 9999)}",
                headline=headline,
                summary=f"{headline}. Market participants are closely watching developments...",
                source=random.choice(NEWS_SOURCES),
                timestamp=timestamp,
                sentiment=sentiment,
                relevance_score=round(0.5 + random.random() * 0.5, 2),
                symbols=item_symbols,
            )
        )

    # Sort by timestamp (most recent first)
    news_items.sort(key=lambda x: x.timestamp, reverse=True)
    return news_items
