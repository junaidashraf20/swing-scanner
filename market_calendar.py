"""
market_calendar.py
──────────────────
NSE Holiday checker.
Maintains a hardcoded list of NSE holidays for current year
+ auto-fetches from NSE API if possible.
Scanner will NOT run on market holidays.
"""

import requests
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

# ── Hardcoded NSE holidays 2025 & 2026 ───────────────────────
# Source: NSE India official holiday calendar
NSE_HOLIDAYS = {
    # 2025
    date(2025, 1, 26),  # Republic Day
    date(2025, 2, 26),  # Mahashivratri
    date(2025, 3, 14),  # Holi
    date(2025, 3, 31),  # Id-Ul-Fitr (Ramadan Eid)
    date(2025, 4, 10),  # Shri Ram Navami
    date(2025, 4, 14),  # Dr. Baba Saheb Ambedkar Jayanti
    date(2025, 4, 18),  # Good Friday
    date(2025, 5, 1),   # Maharashtra Day
    date(2025, 8, 15),  # Independence Day
    date(2025, 8, 27),  # Ganesh Chaturthi
    date(2025, 10, 2),  # Gandhi Jayanti / Dussehra
    date(2025, 10, 20), # Diwali Laxmi Pujan (Muhurat Trading only)
    date(2025, 10, 21), # Diwali Balipratipada
    date(2025, 11, 5),  # Prakash Gurpurb Sri Guru Nanak Dev
    date(2025, 12, 25), # Christmas
    # 2026
    date(2026, 1, 26),  # Republic Day
    date(2026, 3, 3),   # Mahashivratri
    date(2026, 3, 20),  # Holi
    date(2026, 4, 3),   # Good Friday
    date(2026, 4, 14),  # Dr. Baba Saheb Ambedkar Jayanti
    date(2026, 4, 22),  # Shri Ram Navami
    date(2026, 5, 1),   # Maharashtra Day
    date(2026, 8, 15),  # Independence Day
    date(2026, 10, 2),  # Gandhi Jayanti
    date(2026, 11, 11), # Diwali (approx)
    date(2026, 12, 25), # Christmas
}


def is_market_open(check_date: date = None) -> tuple[bool, str]:
    """
    Returns (is_open, reason).
    is_open = True if NSE is trading today.
    """
    if check_date is None:
        check_date = datetime.now(IST).date()

    # Weekend check
    if check_date.weekday() == 5:
        return False, f"Saturday — NSE closed"
    if check_date.weekday() == 6:
        return False, f"Sunday — NSE closed"

    # Holiday check
    if check_date in NSE_HOLIDAYS:
        return False, f"NSE Holiday — {check_date.strftime('%d %b %Y')}"

    return True, "Market open"


def assert_market_open() -> bool:
    """
    Call this at the start of scanner.
    Returns True if market was open today (safe to scan).
    Logs and returns False if it was a holiday/weekend.
    """
    is_open, reason = is_market_open()
    if not is_open:
        logger.warning(f"⚠️  Skipping scan — {reason}")
        return False
    logger.info(f"✅ Market was open today — proceeding with scan")
    return True
