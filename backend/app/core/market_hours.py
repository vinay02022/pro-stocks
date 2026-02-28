"""
Market Hours Utility

Handles IST timezone, market sessions, and NSE holidays.
"""

from datetime import datetime, date, timedelta
from enum import Enum
from typing import Optional
import pytz

IST = pytz.timezone("Asia/Kolkata")

# Market timing (IST)
MARKET_OPEN = "09:15"
MARKET_CLOSE = "15:30"
PRE_OPEN_START = "09:00"
PRE_OPEN_END = "09:08"
POST_CLOSE_END = "15:40"


class MarketSession(str, Enum):
    PRE_OPEN = "PRE_OPEN"
    OPENING = "OPENING"
    NORMAL = "NORMAL"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


# NSE Holidays 2024-2026
NSE_HOLIDAYS = {
    # 2024
    date(2024, 1, 26),   # Republic Day
    date(2024, 3, 8),    # Maha Shivaratri
    date(2024, 3, 25),   # Holi
    date(2024, 3, 29),   # Good Friday
    date(2024, 4, 11),   # Id-Ul-Fitr
    date(2024, 4, 14),   # Dr. Ambedkar Jayanti
    date(2024, 4, 17),   # Ram Navami
    date(2024, 4, 21),   # Mahavir Jayanti
    date(2024, 5, 1),    # Maharashtra Day
    date(2024, 5, 23),   # Buddha Purnima
    date(2024, 6, 17),   # Eid ul-Adha
    date(2024, 7, 17),   # Muharram
    date(2024, 8, 15),   # Independence Day
    date(2024, 10, 2),   # Gandhi Jayanti
    date(2024, 11, 1),   # Diwali
    date(2024, 11, 15),  # Guru Nanak Jayanti
    date(2024, 12, 25),  # Christmas
    # 2025
    date(2025, 1, 26),   # Republic Day
    date(2025, 2, 26),   # Maha Shivaratri
    date(2025, 3, 14),   # Holi
    date(2025, 3, 31),   # Id-Ul-Fitr
    date(2025, 4, 10),   # Mahavir Jayanti
    date(2025, 4, 14),   # Dr. Ambedkar Jayanti
    date(2025, 4, 18),   # Good Friday
    date(2025, 5, 1),    # Maharashtra Day
    date(2025, 6, 7),    # Eid ul-Adha
    date(2025, 8, 15),   # Independence Day
    date(2025, 8, 27),   # Janmashtami
    date(2025, 10, 2),   # Gandhi Jayanti
    date(2025, 10, 21),  # Diwali
    date(2025, 10, 22),  # Diwali Balipratipada
    date(2025, 11, 5),   # Guru Nanak Jayanti
    date(2025, 12, 25),  # Christmas
    # 2026
    date(2026, 1, 26),   # Republic Day
    date(2026, 8, 15),   # Independence Day
    date(2026, 10, 2),   # Gandhi Jayanti
    date(2026, 12, 25),  # Christmas
}


def get_ist_now() -> datetime:
    """Get current time in IST."""
    return datetime.now(IST)


def is_weekend(dt: date) -> bool:
    """Check if date is a weekend."""
    return dt.weekday() >= 5  # Saturday = 5, Sunday = 6


def is_holiday(dt: date) -> bool:
    """Check if date is an NSE holiday."""
    return dt in NSE_HOLIDAYS


def is_trading_day(dt: date) -> bool:
    """Check if date is a trading day."""
    return not is_weekend(dt) and not is_holiday(dt)


def get_market_session(dt: Optional[datetime] = None) -> MarketSession:
    """Get current market session."""
    if dt is None:
        dt = get_ist_now()

    if not is_trading_day(dt.date()):
        return MarketSession.CLOSED

    time_str = dt.strftime("%H:%M")

    if time_str < PRE_OPEN_START:
        return MarketSession.CLOSED
    elif time_str < PRE_OPEN_END:
        return MarketSession.PRE_OPEN
    elif time_str < MARKET_OPEN:
        return MarketSession.OPENING
    elif time_str < MARKET_CLOSE:
        return MarketSession.NORMAL
    elif time_str < POST_CLOSE_END:
        return MarketSession.CLOSING
    else:
        return MarketSession.CLOSED


def is_market_open(dt: Optional[datetime] = None) -> bool:
    """Check if market is currently open for trading."""
    session = get_market_session(dt)
    return session in (MarketSession.NORMAL, MarketSession.CLOSING)


def get_next_trading_day(dt: Optional[date] = None) -> date:
    """Get the next trading day."""
    if dt is None:
        dt = get_ist_now().date()

    next_day = dt + timedelta(days=1)
    while not is_trading_day(next_day):
        next_day += timedelta(days=1)

    return next_day


def get_previous_trading_day(dt: Optional[date] = None) -> date:
    """Get the previous trading day."""
    if dt is None:
        dt = get_ist_now().date()

    prev_day = dt - timedelta(days=1)
    while not is_trading_day(prev_day):
        prev_day -= timedelta(days=1)

    return prev_day


def get_weekly_expiry(dt: Optional[date] = None) -> date:
    """Get the weekly options expiry (Thursday)."""
    if dt is None:
        dt = get_ist_now().date()

    # Find next Thursday
    days_until_thursday = (3 - dt.weekday()) % 7
    if days_until_thursday == 0 and not is_market_open():
        days_until_thursday = 7

    thursday = dt + timedelta(days=days_until_thursday)

    # If Thursday is a holiday, expiry is previous day
    while not is_trading_day(thursday):
        thursday -= timedelta(days=1)

    return thursday


def get_upcoming_expiries(count: int = 4) -> list[str]:
    """Get upcoming weekly expiry dates."""
    expiries = []
    current = get_weekly_expiry()

    for _ in range(count):
        expiries.append(current.isoformat())
        current = get_weekly_expiry(current + timedelta(days=1))

    return expiries


def get_market_status() -> dict:
    """Get comprehensive market status."""
    now = get_ist_now()
    session = get_market_session(now)

    status = {
        "is_open": is_market_open(now),
        "session": session.value,
        "is_holiday": is_holiday(now.date()),
        "is_weekend": is_weekend(now.date()),
        "current_time_ist": now.strftime("%H:%M:%S"),
        "current_date": now.date().isoformat(),
    }

    if not status["is_open"]:
        next_trading = get_next_trading_day(now.date())
        status["next_open"] = f"{next_trading.isoformat()}T{MARKET_OPEN}:00+05:30"

    return status
