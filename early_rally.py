"""
early_rally.py — VCP / Volume Dry-up Breakout Scanner
───────────────────────────────────────────────────────
Detects the VERY START of a new rally — before it becomes obvious.

Logic:
  1. Volume dry-up  : last 10-15 candles have quieter volume than usual
  2. Price coiling  : range getting tighter (volatility contracting)
  3. Explosive break: today's volume is 2x+ the quiet base period volume
  4. Strong candle  : large body, closes in top 25% of day's range
  5. Fresh base     : within 20% of recent low (not extended)

Based on: Mark Minervini's VCP (Volatility Contraction Pattern)
Timeframe: Daily + Weekly
"""

import numpy as np
import pandas as pd
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


# ════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════

def resample_weekly(df):
    return df.resample("W").agg({
        "Open": "first", "High": "max",
        "Low": "min", "Close": "last", "Volume": "sum",
    }).dropna()

def is_weekly_close_day() -> bool:
    from market_calendar import NSE_HOLIDAYS
    today = datetime.now(IST).date()
    if today.weekday() == 4 and today not in NSE_HOLIDAYS:
        return True
    friday = today + timedelta(days=(4 - today.weekday()) % 7)
    if today.weekday() == 3 and friday in NSE_HOLIDAYS:
        return True
    return False


# ════════════════════════════════════════════════════════════════
#  CORE DETECTION
# ════════════════════════════════════════════════════════════════

def detect_vcp_breakout(df: pd.DataFrame, timeframe: str = "D") -> dict | None:
    """
    Detects VCP (Volatility Contraction Pattern) breakout.

    Conditions:
    A. VOLUME DRY-UP during base:
       - Average volume of last 10-15 candles < 80% of 30-day median
       - Volume was trending down or flat (getting quieter)

    B. EXPLOSIVE BREAKOUT today:
       - Today's volume >= 2x the quiet base period's average volume
       - Today's volume >= 1.5x the 30-day overall median

    C. STRONG CANDLE:
       - Body size >= 1% of price (meaningful move, not a doji)
       - Close in top 30% of day's range (strong close)
       - Bullish (close > open)

    D. FRESH BASE (not extended):
       - 20-day low within 20% of breakout level

    E. BREAKOUT:
       - Close above the high of the base period
    """
    if df is None or len(df) < 35:
        return None

    today       = df.iloc[-1]
    today_close = float(today["Close"])
    today_open  = float(today["Open"])
    today_high  = float(today["High"])
    today_low   = float(today["Low"])
    today_vol   = float(today["Volume"])

    # ── C. Strong candle check ────────────────────────────────
    candle_range = today_high - today_low
    if candle_range <= 0:
        return None

    body_size    = abs(today_close - today_open)
    body_pct     = body_size / today_close * 100
    close_pos    = (today_close - today_low) / candle_range  # 0=bottom, 1=top

    if body_pct < 1.0:
        return None  # Doji or tiny candle — not a strong move

    if close_pos < 0.70:
        return None  # Closed below top 30% — weak close

    if today_close <= today_open:
        return None  # Must be bullish

    # ── Base period definition ────────────────────────────────
    base_len = 15  # look at last 15 candles as "base"
    if len(df) < base_len + 5:
        return None

    base        = df.iloc[-(base_len + 1):-1]
    base_high   = float(base["High"].max())
    base_low    = float(base["Low"].min())
    base_range  = (base_high - base_low) / base_low if base_low > 0 else 1.0

    # ── A. Volume dry-up during base ─────────────────────────
    overall_median = float(df["Volume"].iloc[-31:-1].median())
    base_avg_vol   = float(base["Volume"].mean())

    if overall_median <= 0:
        return None

    # Base volume must be quieter than overall median
    base_vol_ratio = base_avg_vol / overall_median
    if base_vol_ratio > 0.85:
        return None  # Volume was NOT drying up during base — skip

    # ── B. Explosive breakout volume ─────────────────────────
    # Today's volume vs base average
    explosion_ratio = today_vol / base_avg_vol if base_avg_vol > 0 else 0
    overall_ratio   = today_vol / overall_median if overall_median > 0 else 0

    if explosion_ratio < 2.0:
        return None  # Not explosive enough vs quiet base

    if overall_ratio < 1.5:
        return None  # Must also be above overall median

    # ── E. Breakout above base high ──────────────────────────
    prev_close = float(df["Close"].iloc[-2])
    if not (prev_close <= base_high < today_close):
        return None  # Not breaking above base high today

    # ── D. Fresh base — not extended ─────────────────────────
    recent_low   = float(df["Low"].iloc[-21:-1].min())
    if recent_low <= 0:
        return None
    extension = (base_high - recent_low) / recent_low
    if extension > 0.20:
        return None  # Already extended from base

    # ── Extra quality: tighter base = better setup ───────────
    # Base range is a quality indicator (tighter = more coiled)
    base_tightness = "Tight" if base_range <= 0.08 else "Moderate" if base_range <= 0.15 else "Wide"

    tf_label = "Weekly" if timeframe == "W" else "Daily"

    return {
        "strategy":        "EARLY_RALLY",
        "type":            "VCP_BREAKOUT",
        "timeframe":       timeframe,
        "label":           f"🚀 VCP Breakout [{tf_label}]",
        "broke_above":     round(base_high, 2),
        "current":         round(today_close, 2),
        "explosion_ratio": round(explosion_ratio, 1),
        "overall_vol":     round(overall_ratio, 1),
        "base_range":      round(base_range * 100, 1),
        "base_tightness":  base_tightness,
        "base_vol_ratio":  round(base_vol_ratio, 2),
        "close_pos":       round(close_pos * 100, 0),
        "weekly_flag":     timeframe == "W",
        "note": (
            f"Base vol was {round(base_vol_ratio*100)}% of median "
            f"→ today exploded {round(explosion_ratio,1)}x. "
            f"{base_tightness} base ({round(base_range*100,1)}%)."
        ),
    }


# ════════════════════════════════════════════════════════════════
#  RUNNER
# ════════════════════════════════════════════════════════════════

def run_early_rally_scan(df: pd.DataFrame) -> list[dict]:
    """
    Runs VCP detection on daily and weekly timeframes.
    Returns list of signals (empty if none found).
    """
    if df is None or len(df) < 35:
        return []

    signals = []

    # Daily
    try:
        s = detect_vcp_breakout(df, "D")
        if s:
            signals.append(s)
    except Exception as e:
        logger.debug(f"VCP daily error: {e}")

    # Weekly — only on Friday
    if len(df) >= 60 and is_weekly_close_day():
        try:
            wdf = resample_weekly(df)
            if wdf is not None and len(wdf) >= 20:
                s = detect_vcp_breakout(wdf, "W")
                if s:
                    signals.append(s)
        except Exception as e:
            logger.debug(f"VCP weekly error: {e}")

    return signals
