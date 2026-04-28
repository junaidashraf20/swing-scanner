"""
data_fetcher.py
───────────────
Robust OHLCV fetcher with:
  1. Primary source  : yfinance Ticker().history() — more stable than download()
  2. Fallback source : jugaad_data (direct NSE data)
  3. Data validation : catches bad/corrupt/empty data before strategies run

Fixes:
  - Switched from yf.download() to yf.Ticker().history() — fixes InterfaceError
  - Reduced connection pool pressure — fixes "pool is full" warning
  - Handles timezone-naive data from yfinance
"""

import pandas as pd
import numpy as np
import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


# ════════════════════════════════════════════════════════════════
#  DATA VALIDATION
# ════════════════════════════════════════════════════════════════

def validate_ohlcv(df: pd.DataFrame, symbol: str = "") -> tuple[bool, str]:
    """
    Validates a daily OHLCV dataframe before running any strategy.
    Returns (is_valid, reason).
    """
    if df is None or df.empty:
        return False, "Empty dataframe"

    if len(df) < 50:
        return False, f"Insufficient rows: {len(df)} (need 50+)"

    required = ["Open", "High", "Low", "Close", "Volume"]
    missing  = [c for c in required if c not in df.columns]
    if missing:
        return False, f"Missing columns: {missing}"

    # Fill NaN with forward fill then drop remaining
    df.ffill(inplace=True)
    df.dropna(subset=required, inplace=True)

    if len(df) < 50:
        return False, f"Too few rows after NaN cleanup: {len(df)}"

    # Check for zero or negative prices
    for col in ["Open", "High", "Low", "Close"]:
        if (df[col] <= 0).any():
            return False, f"Zero/negative price in {col}"

    # Basic OHLC integrity
    if (df["High"] < df["Low"]).any():
        return False, "High < Low found in data"

    # Remove abnormal spikes (>50% single-day move — bad data)
    pct_change = df["Close"].pct_change().abs()
    bad_dates  = df.index[pct_change > 0.5].tolist()
    if bad_dates:
        df.drop(index=bad_dates, inplace=True, errors="ignore")

    # Minimum liquidity filter
    avg_vol = df["Volume"].tail(20).mean()
    if avg_vol < 50000:
        return False, f"Illiquid: avg vol {avg_vol:.0f} < 50,000"

    if len(df) < 35:
        return False, f"Too few rows after cleaning: {len(df)}"

    return True, "OK"


# ════════════════════════════════════════════════════════════════
#  PRIMARY: YFINANCE  (using Ticker.history — more stable)
# ════════════════════════════════════════════════════════════════

def fetch_yfinance(symbol: str, days: int = 365) -> pd.DataFrame | None:
    """
    Fetch using yf.Ticker().history() — avoids InterfaceError
    that occurs with yf.download() in newer yfinance versions.
    """
    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        df = ticker.history(
            period=f"{days + 40}d",
            interval="1d",
            auto_adjust=True,
            actions=False,       # skip dividends/splits columns
            timeout=10,
        )

        if df is None or df.empty:
            return None

        # Normalize index — strip timezone to avoid comparison issues
        df.index = pd.to_datetime(df.index).tz_localize(None)

        # Keep only standard OHLCV columns
        needed = ["Open", "High", "Low", "Close", "Volume"]
        existing = [c for c in needed if c in df.columns]
        df = df[existing].copy()

        return df.tail(days)

    except Exception as e:
        logger.debug(f"{symbol} yfinance error: {e}")
        return None


# ════════════════════════════════════════════════════════════════
#  FALLBACK: JUGAAD_DATA (direct NSE)
# ════════════════════════════════════════════════════════════════

def fetch_jugaad(symbol: str, days: int = 365) -> pd.DataFrame | None:
    """
    Fallback: fetch from NSE directly via jugaad_data.
    """
    try:
        from jugaad_data.nse import stock_df
        from datetime import date

        clean_sym  = symbol.replace(".NS", "").replace(".BO", "").upper()
        end_date   = datetime.now(IST).date()
        start_date = end_date - timedelta(days=days + 40)

        df = stock_df(
            symbol=clean_sym,
            from_date=start_date,
            to_date=end_date,
            series="EQ",
        )

        if df is None or df.empty:
            return None

        col_map = {
            "CH_TIMESTAMP":          "Date",
            "CH_OPENING_PRICE":      "Open",
            "CH_TRADE_HIGH_PRICE":   "High",
            "CH_TRADE_LOW_PRICE":    "Low",
            "CH_CLOSING_PRICE":      "Close",
            "CH_TOT_TRADED_QTY":     "Volume",
        }
        df = df.rename(columns=col_map)

        needed = ["Date", "Open", "High", "Low", "Close", "Volume"]
        existing = [c for c in needed if c in df.columns]
        df = df[existing].copy()

        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()

        return df.tail(days)

    except Exception as e:
        logger.debug(f"{symbol} jugaad error: {e}")
        return None


# ════════════════════════════════════════════════════════════════
#  MAIN FETCH — auto fallback + validation
# ════════════════════════════════════════════════════════════════

def fetch_ohlcv(symbol: str, days: int = 365) -> pd.DataFrame | None:
    """
    Fetch OHLCV with automatic fallback and validation.
    1. Try yfinance Ticker().history()
    2. If fails → try jugaad_data
    3. Validate final data
    4. Return cleaned DataFrame or None
    """
    # ── Try yfinance ──────────────────────────────────────────
    df = fetch_yfinance(symbol, days)
    if df is not None and not df.empty:
        valid, reason = validate_ohlcv(df, symbol)
        if valid:
            return df
        logger.debug(f"{symbol}: yfinance invalid ({reason}) → trying jugaad")

    # ── Fallback to jugaad_data ───────────────────────────────
    time.sleep(0.05)
    df = fetch_jugaad(symbol, days)
    if df is not None and not df.empty:
        valid, reason = validate_ohlcv(df, symbol)
        if valid:
            return df
        logger.debug(f"{symbol}: jugaad also invalid ({reason})")

    return None
