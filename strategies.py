"""
strategies.py — OPTIMIZED BREAKOUT ONLY
─────────────────────────────────────────
Key filter added:
  • Base proximity filter — recent 20-day low must be within 20% of
    breakout level. Filters stocks already extended from base.
    Keeps fresh breakouts (NAVA, FORTIS style).
    Removes extended moves (LALPATHLAB, MCX style).
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

def median_volume(df, period=20):
    return float(df["Volume"].iloc[-(period + 1):-1].median())

def volume_above_median(df, period=20, multiplier=1.2):
    med = median_volume(df, period)
    today_vol = float(df["Volume"].iloc[-1])
    if med <= 0:
        return False, 0.0
    ratio = today_vol / med
    return ratio >= multiplier, round(ratio, 2)

def is_bullish_close(candle):
    return float(candle["Close"]) > float(candle["Open"])

def resample_weekly(df):
    weekly = df.resample("W").agg({
        "Open":   "first",
        "High":   "max",
        "Low":    "min",
        "Close":  "last",
        "Volume": "sum",
    }).dropna()
    return weekly

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
#  BASE PROXIMITY FILTER  ← NEW KEY FILTER
# ════════════════════════════════════════════════════════════════

def is_fresh_breakout(df, breakout_level: float,
                       lookback: int = 20,
                       max_extension: float = 0.25) -> tuple[bool, float]:
    """
    Checks if the stock is breaking out from a FRESH BASE
    and has NOT already run up too much.

    Logic:
      recent_low  = lowest low in last `lookback` candles (excluding today)
      extension   = (breakout_level - recent_low) / recent_low

    If extension > max_extension → stock already ran too much → SKIP
    If extension <= max_extension → stock is breaking from base → KEEP

    Examples:
      NAVA:         base ~700, breakout 727  → 3.9%  ✅ fresh
      FORTIS:       base ~860, breakout 951  → 10.6% ✅ fresh
      TATA CONSUMER:base ~1150, breakout 1244→ 8.1%  ✅ fresh
      LALPATHLAB:   base ~1300, breakout 1598→ 22.9% ❌ extended
      MCX/Lauruslabs: similar large extensions ❌ extended
    """
    if len(df) < lookback + 1:
        return True, 0.0  # Not enough data — allow through

    recent_low = float(df["Low"].iloc[-(lookback + 1):-1].min())

    if recent_low <= 0:
        return True, 0.0

    extension = (breakout_level - recent_low) / recent_low
    is_fresh  = extension <= max_extension

    return is_fresh, round(extension * 100, 1)


# ════════════════════════════════════════════════════════════════
#  RESISTANCE ZONE DETECTION
# ════════════════════════════════════════════════════════════════

def find_resistance_zones(df, window=5, zone_threshold=0.025):
    n = len(df)
    raw_highs = []
    for i in range(window, n - window):
        local_max = df["High"].iloc[i - window: i + window + 1].max()
        if float(df["High"].iloc[i]) == local_max:
            rejection = float(df["High"].iloc[i]) - float(df["Close"].iloc[i])
            rejection_pct = rejection / float(df["High"].iloc[i])
            raw_highs.append({
                "price":     float(df["High"].iloc[i]),
                "bar":       i,
                "rejection": rejection_pct,
            })
    if not raw_highs:
        return []
    raw_highs.sort(key=lambda x: x["price"])
    clusters = [[raw_highs[0]]]
    for h in raw_highs[1:]:
        ref = clusters[-1][-1]["price"]
        if abs(h["price"] - ref) / ref < zone_threshold:
            clusters[-1].append(h)
        else:
            clusters.append([h])
    zones = []
    for cluster in clusters:
        avg_price     = float(np.mean([c["price"] for c in cluster]))
        touches       = len(cluster)
        avg_rejection = float(np.mean([c["rejection"] for c in cluster]))
        strength      = (touches * 2) + (avg_rejection * 100)
        zones.append({
            "price":    round(avg_price, 2),
            "touches":  touches,
            "strength": round(strength, 2),
        })
    zones.sort(key=lambda x: x["strength"], reverse=True)
    return zones


# ════════════════════════════════════════════════════════════════
#  BREAKOUT TYPE 1 — 52-WEEK HIGH
# ════════════════════════════════════════════════════════════════

def detect_52week_breakout(df, timeframe="D"):
    bars_in_year = 252 if timeframe == "D" else 52
    if len(df) < bars_in_year:
        return None

    today       = df.iloc[-1]
    prev_close  = float(df["Close"].iloc[-2])
    year_high   = float(df["High"].iloc[-bars_in_year:-1].max())
    today_close = float(today["Close"])

    if not (prev_close <= year_high < today_close):
        return None
    if not is_bullish_close(today):
        return None

    vol_ok, vol_ratio = volume_above_median(df, multiplier=1.2)
    if not vol_ok:
        return None

    # Base proximity check
    fresh, extension = is_fresh_breakout(df, year_high)
    if not fresh:
        logger.debug(f"52W breakout skipped — already extended {extension}% from base")
        return None

    label = "52-Week High Breakout 🏆" if timeframe == "D" else "52-Week High Breakout 🏆⭐"
    base_low = round(float(df["Low"].iloc[-21:-1].min()), 2)
    return {
        "strategy":    "BREAKOUT",
        "type":        "52_WEEK_HIGH",
        "timeframe":   timeframe,
        "label":       label,
        "broke_above": round(year_high, 2),
        "current":     round(today_close, 2),
        "vol_ratio":   vol_ratio,
        "extension":   extension,
        "base_low":    base_low,
        "weekly_flag": timeframe == "W",
    }


# ════════════════════════════════════════════════════════════════
#  BREAKOUT TYPE 2 — RESISTANCE LEVEL BREAKOUT
# ════════════════════════════════════════════════════════════════

def detect_resistance_breakout(df, timeframe="D",
                                swing_window=5,
                                min_touches=2,
                                min_strength=5.0,
                                zone_threshold=0.025):
    today_close = float(df["Close"].iloc[-1])
    prev_close  = float(df["Close"].iloc[-2])
    today       = df.iloc[-1]

    if not is_bullish_close(today):
        return None

    vol_ok, vol_ratio = volume_above_median(df, multiplier=1.2)
    if not vol_ok:
        return None

    zones = find_resistance_zones(df.iloc[:-1], swing_window, zone_threshold)
    if not zones:
        return None

    best = None
    for zone in zones:
        if zone["touches"] < min_touches:
            continue
        if zone["strength"] < min_strength:
            continue
        if prev_close <= zone["price"] < today_close:
            # Base proximity check
            fresh, extension = is_fresh_breakout(df, zone["price"])
            if not fresh:
                logger.debug(f"Resistance breakout skipped — extended {extension}% from base")
                continue
            if best is None or zone["strength"] > best["strength"]:
                best = {**zone, "extension": extension}

    if best is None:
        return None

    tf_label = "Weekly ⭐" if timeframe == "W" else "Daily"
    base_low = round(float(df["Low"].iloc[-21:-1].min()), 2)
    return {
        "strategy":    "BREAKOUT",
        "type":        "RESISTANCE",
        "timeframe":   timeframe,
        "label":       f"Resistance Breakout ({tf_label}) 🔓",
        "broke_above": best["price"],
        "current":     round(today_close, 2),
        "touches":     best["touches"],
        "strength":    best["strength"],
        "vol_ratio":   vol_ratio,
        "extension":   best["extension"],
        "base_low":    base_low,
        "weekly_flag": timeframe == "W",
    }


# ════════════════════════════════════════════════════════════════
#  BREAKOUT TYPE 3 — CONSOLIDATION BREAKOUT
# ════════════════════════════════════════════════════════════════

def detect_consolidation_breakout(df, timeframe="D",
                                   lookback=30,
                                   max_range_pct=0.10):
    lb = lookback if timeframe == "D" else max(12, lookback // 4)
    if len(df) < lb + 2:
        return None

    consol      = df.iloc[-(lb + 1):-1]
    today       = df.iloc[-1]
    today_close = float(today["Close"])
    prev_close  = float(df["Close"].iloc[-2])

    hi  = float(consol["High"].max())
    lo  = float(consol["Low"].min())
    rng = (hi - lo) / lo if lo > 0 else 1.0

    if rng > max_range_pct:
        return None
    if not (prev_close <= hi < today_close):
        return None
    if not is_bullish_close(today):
        return None

    vol_ok, vol_ratio = volume_above_median(df, multiplier=1.2)
    if not vol_ok:
        return None

    # For consolidation — base IS the consolidation so no extension check needed
    # The consolidation itself ensures stock was in a base

    tf_label = "Weekly ⭐" if timeframe == "W" else "Daily"
    base_low = round(float(lo), 2)  # consolidation low IS the base low
    return {
        "strategy":      "BREAKOUT",
        "type":          "CONSOLIDATION",
        "timeframe":     timeframe,
        "label":         f"{lb}-Candle Consolidation Breakout ({tf_label}) 📦",
        "broke_above":   round(hi, 2),
        "current":       round(today_close, 2),
        "range_pct":     round(rng * 100, 1),
        "range_candles": lb,
        "vol_ratio":     vol_ratio,
        "base_low":      base_low,
        "weekly_flag":   timeframe == "W",
    }


# ════════════════════════════════════════════════════════════════
#  BULLISH ORDER BLOCK — IMPULSE + CONSOLIDATION PATTERN
# ════════════════════════════════════════════════════════════════

def identify_bullish_order_block(df, lookback=30, consol_min=3, consol_max=10):
    """
    Identifies a bullish order block zone by finding:
    1. A recent bullish impulse (rising closes/opens)
    2. The peak high of that impulse
    3. The consolidation/pullback zone below the peak (order block zone)
    
    Returns: (block_high, block_low, is_valid)
    """
    if len(df) < lookback + 1:
        return None, None, False

    # Look back to find a bullish impulse (majority closes > opens in recent window)
    recent = df.iloc[-(lookback + 1):-1]
    bullish_count = sum(1 for _, candle in recent.iterrows()
                        if float(candle["Close"]) > float(candle["Open"]))
    
    if bullish_count < lookback * 0.5:  # At least 50% bullish candles
        return None, None, False

    # Find the peak high in the recent window
    peak_high = float(recent["High"].max())
    peak_idx = recent["High"].idxmax()

    # Look for consolidation zone after the peak (pullback/order block)
    # Consolidation is lower highs and lows below the peak
    after_peak = df.loc[peak_idx:]
    
    if len(after_peak) < consol_min + 1:
        return None, None, False

    # Extract consolidation bars (those with lows below peak)
    consol_bars = []
    for idx, candle in after_peak.iloc[1:].iterrows():
        high = float(candle["High"])
        if high < peak_high:
            consol_bars.append(candle)
        if len(consol_bars) >= consol_max:
            break

    # Valid order block must have min consolidation bars
    if len(consol_bars) < consol_min:
        return None, None, False

    # Order block zone: highest high of consolidation bars (this is where we bought)
    # and the lowest low of consolidation (our stop loss area)
    consol_df = pd.DataFrame(consol_bars)
    block_high = float(consol_df["High"].max())
    block_low = float(consol_df["Low"].min())

    # Block high should be reasonably below peak (consolidation, not another impulse)
    if block_high >= peak_high * 0.95:
        return None, None, False

    return block_high, block_low, True


def detect_order_block_breakout(df, timeframe="D", cfg=None):
    """
    Detects bullish order block breakout:
    - Previous close <= block_high
    - Today close > block_high
    - Bullish close
    - Above-median volume
    
    Returns signal dict or None.
    """
    if cfg is None:
        cfg = {}

    impulse_lb = cfg.get("ORDER_BLOCK_IMPULSE_LOOKBACK", 30)
    consol_min = cfg.get("ORDER_BLOCK_CONSOLIDATION_MIN", 3)
    consol_max = cfg.get("ORDER_BLOCK_CONSOLIDATION_MAX", 10)
    vol_mult = cfg.get("ORDER_BLOCK_VOLUME_MULT", 1.2)

    if len(df) < impulse_lb + 5:
        return None

    # Identify the order block zone
    block_high, block_low, is_valid = identify_bullish_order_block(
        df, impulse_lb, consol_min, consol_max
    )
    if not is_valid or block_high is None:
        return None

    today = df.iloc[-1]
    today_close = float(today["Close"])
    prev_close = float(df["Close"].iloc[-2])

    # Breakout condition: today closes above block_high, yesterday was below/equal
    if not (prev_close <= block_high < today_close):
        return None

    # Must be bullish close
    if not is_bullish_close(today):
        return None

    # Volume confirmation
    vol_ok, vol_ratio = volume_above_median(df, multiplier=vol_mult)
    if not vol_ok:
        return None

    # Base low for SL calculation
    base_low = round(block_low, 2)

    tf_label = "Weekly ⭐" if timeframe == "W" else "Daily"
    return {
        "strategy":    "BREAKOUT",
        "type":        "ORDER_BLOCK",
        "timeframe":   timeframe,
        "label":       f"Bullish Order Block Breakout ({tf_label}) 📦⬆️",
        "broke_above": round(block_high, 2),
        "current":     round(today_close, 2),
        "vol_ratio":   vol_ratio,
        "base_low":    base_low,
        "weekly_flag": timeframe == "W",
        "block_high":  round(block_high, 2),
        "block_low":   round(block_low, 2),
    }


# ════════════════════════════════════════════════════════════════
#  UNIFIED RUNNER
# ════════════════════════════════════════════════════════════════

def run_all_strategies(df, cfg):
    if df is None or len(df) < 35:
        return []

    sw = cfg.get("SR_SWING_WINDOW", 5)
    mt = cfg.get("SR_MIN_TOUCHES", 2)
    zt = cfg.get("SR_ZONE_THRESHOLD", 0.025)
    lb = cfg.get("BREAKOUT_LOOKBACK", 30)
    mr = cfg.get("BREAKOUT_MAX_RANGE", 0.15)

    signals = []

    # ── DAILY ─────────────────────────────────────────────────
    try:
        s = detect_52week_breakout(df, "D")
        if s: signals.append(s)
    except Exception as e:
        logger.debug(f"52W daily: {e}")

    try:
        s = detect_resistance_breakout(df, "D", sw, mt, 5.0, zt)
        if s: signals.append(s)
    except Exception as e:
        logger.debug(f"Resistance daily: {e}")

    try:
        s = detect_consolidation_breakout(df, "D", lb, mr)
        if s: signals.append(s)
    except Exception as e:
        logger.debug(f"Consolidation daily: {e}")

    try:
        s = detect_order_block_breakout(df, "D", cfg)
        if s: signals.append(s)
    except Exception as e:
        logger.debug(f"Order block daily: {e}")

    # ── WEEKLY — only on Friday ───────────────────────────────
    if len(df) >= 60 and is_weekly_close_day():
        try:
            wdf = resample_weekly(df)
            if wdf is not None and len(wdf) >= 20:
                try:
                    s = detect_52week_breakout(wdf, "W")
                    if s: signals.append(s)
                except Exception as e:
                    logger.debug(f"52W weekly: {e}")
                try:
                    s = detect_resistance_breakout(wdf, "W", sw, mt, 4.0, zt)
                    if s: signals.append(s)
                except Exception as e:
                    logger.debug(f"Resistance weekly: {e}")
                try:
                    s = detect_consolidation_breakout(wdf, "W", 12, mr)
                    if s: signals.append(s)
                except Exception as e:
                    logger.debug(f"Consolidation weekly: {e}")
                try:
                    s = detect_order_block_breakout(wdf, "W", cfg)
                    if s: signals.append(s)
                except Exception as e:
                    logger.debug(f"Order block weekly: {e}")
        except Exception as e:
            logger.debug(f"Weekly resample: {e}")

    return signals
