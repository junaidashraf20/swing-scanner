"""
strategies.py — PERFECTED BREAKOUT ONLY
─────────────────────────────────────────
Your exact rules:
  • Breakout close above resistance with volume above median
  • 3 types: 52-Week High | Strong Resistance Level | Consolidation Range
  • Both Daily AND Weekly timeframe breakouts detected
  • Resistance validity = strength based (touches + rejection size), not age
  • Bullish only
"""

import numpy as np
import pandas as pd
import logging

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════

def median_volume(df, period=20):
    return float(df["Volume"].iloc[-(period + 1):-1].median())

def volume_above_median(df, period=20):
    med = median_volume(df, period)
    today_vol = float(df["Volume"].iloc[-1])
    if med <= 0:
        return False, 0.0
    ratio = today_vol / med
    return ratio >= 1.0, round(ratio, 2)

def is_bullish_close(candle):
    return float(candle["Close"]) > float(candle["Open"])

def resample_weekly(df):
    """Convert daily OHLCV to weekly candles."""
    weekly = df.resample("W").agg({
        "Open":   "first",
        "High":   "max",
        "Low":    "min",
        "Close":  "last",
        "Volume": "sum",
    }).dropna()
    return weekly


# ════════════════════════════════════════════════════════════════
#  RESISTANCE ZONE DETECTION
#  Strength-based — more touches + bigger rejections = stronger
# ════════════════════════════════════════════════════════════════

def find_resistance_zones(df, window=5, zone_threshold=0.025):
    """
    Finds resistance zones based on STRENGTH not age.
    
    Strength score for each zone =
        (number of touches × 2) + (avg rejection size as % of price)
    
    Returns list of zones sorted by strength (strongest first):
    [{"price": float, "touches": int, "strength": float}, ...]
    """
    n = len(df)
    raw_highs = []

    # Find all swing highs
    for i in range(window, n - window):
        local_max = df["High"].iloc[i - window: i + window + 1].max()
        if float(df["High"].iloc[i]) == local_max:
            # Rejection size = how much price fell after hitting this high
            rejection = float(df["High"].iloc[i]) - float(df["Close"].iloc[i])
            rejection_pct = rejection / float(df["High"].iloc[i])
            raw_highs.append({
                "price":    float(df["High"].iloc[i]),
                "bar":      i,
                "rejection": rejection_pct,
            })

    if not raw_highs:
        return []

    # Cluster nearby swing highs into zones
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
        # Strength score
        strength = (touches * 2) + (avg_rejection * 100)
        zones.append({
            "price":    round(avg_price, 2),
            "touches":  touches,
            "strength": round(strength, 2),
        })

    # Sort by strength — strongest zones first
    zones.sort(key=lambda x: x["strength"], reverse=True)
    return zones


# ════════════════════════════════════════════════════════════════
#  BREAKOUT TYPE 1 — 52-WEEK HIGH
# ════════════════════════════════════════════════════════════════

def detect_52week_breakout(df, timeframe="D"):
    """Fires when today's close breaks above the 52-week (or 52-week equivalent) high."""
    bars_in_year = 252 if timeframe == "D" else 52
    if len(df) < bars_in_year:
        return None

    today      = df.iloc[-1]
    prev_close = float(df["Close"].iloc[-2])
    year_high  = float(df["High"].iloc[-bars_in_year:-1].max())
    today_close= float(today["Close"])

    if not (prev_close <= year_high < today_close):
        return None
    if not is_bullish_close(today):
        return None

    vol_ok, vol_ratio = volume_above_median(df)
    if not vol_ok:
        return None

    label = "52-Week High Breakout 🏆" if timeframe == "D" else "52-Week High Breakout (Weekly) 🏆⭐"
    return {
        "strategy":    "BREAKOUT",
        "type":        "52_WEEK_HIGH",
        "timeframe":   timeframe,
        "label":       label,
        "broke_above": round(year_high, 2),
        "current":     round(today_close, 2),
        "vol_ratio":   vol_ratio,
        "weekly_flag": True,
        "note":        "Fresh 52-week high with volume — strong momentum",
    }


# ════════════════════════════════════════════════════════════════
#  BREAKOUT TYPE 2 — STRONG RESISTANCE LEVEL BREAKOUT
# ════════════════════════════════════════════════════════════════

def detect_resistance_breakout(df, timeframe="D",
                                swing_window=5,
                                min_touches=2,
                                min_strength=5.0,
                                zone_threshold=0.025):
    """
    Detects breakout above a STRONG resistance zone.
    Strength is based on number of touches + size of rejections — not age.
    """
    today_close = float(df["Close"].iloc[-1])
    prev_close  = float(df["Close"].iloc[-2])
    today       = df.iloc[-1]

    if not is_bullish_close(today):
        return None

    vol_ok, vol_ratio = volume_above_median(df)
    if not vol_ok:
        return None

    # Find resistance zones on historical data (exclude today)
    zones = find_resistance_zones(df.iloc[:-1], swing_window, zone_threshold)
    if not zones:
        return None

    # Find the strongest zone that was just broken
    best = None
    for zone in zones:
        if zone["touches"] < min_touches:
            continue
        if zone["strength"] < min_strength:
            continue
        # Must have broken today (prev below, today above)
        if prev_close <= zone["price"] < today_close:
            if best is None or zone["strength"] > best["strength"]:
                best = zone

    if best is None:
        return None

    tf_label = "Weekly ⭐" if timeframe == "W" else "Daily"
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
        "weekly_flag": timeframe == "W",
        "note":        f"Broke {best['touches']}-touch resistance (strength {best['strength']})",
    }


# ════════════════════════════════════════════════════════════════
#  BREAKOUT TYPE 3 — CONSOLIDATION RANGE BREAKOUT
# ════════════════════════════════════════════════════════════════

def detect_consolidation_breakout(df, timeframe="D",
                                   lookback=30,
                                   max_range_pct=0.15):
    """
    Detects breakout from a tight consolidation range.
    Works on both daily (30 candles) and weekly (15 candles).
    """
    lb = lookback if timeframe == "D" else max(15, lookback // 4)

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

    vol_ok, vol_ratio = volume_above_median(df)
    if not vol_ok:
        return None

    tf_label = "Weekly ⭐" if timeframe == "W" else "Daily"
    return {
        "strategy":    "BREAKOUT",
        "type":        "CONSOLIDATION",
        "timeframe":   timeframe,
        "label":       f"{lb}-Candle Consolidation Breakout ({tf_label}) 📦",
        "broke_above": round(hi, 2),
        "current":     round(today_close, 2),
        "range_pct":   round(rng * 100, 1),
        "range_candles": lb,
        "vol_ratio":   vol_ratio,
        "weekly_flag": timeframe == "W",
        "note":        f"Tight {round(rng*100,1)}% range for {lb} candles — energy released",
    }


# ════════════════════════════════════════════════════════════════
#  UNIFIED RUNNER — Daily + Weekly
# ════════════════════════════════════════════════════════════════

def run_all_strategies(df, cfg):
    """
    Runs all 3 breakout types on both Daily and Weekly timeframes.
    Returns combined list of signals.
    """
    if df is None or len(df) < 35:
        return []

    sw  = cfg.get("SR_SWING_WINDOW", 5)
    mt  = cfg.get("SR_MIN_TOUCHES", 2)
    zt  = cfg.get("SR_ZONE_THRESHOLD", 0.025)
    lb  = cfg.get("BREAKOUT_LOOKBACK", 30)
    mr  = cfg.get("BREAKOUT_MAX_RANGE", 0.15)

    signals = []

    # ── DAILY SCANS ───────────────────────────────────────────
    try:
        s = detect_52week_breakout(df, "D")
        if s: signals.append(s)
    except Exception as e:
        logger.debug(f"52W daily error: {e}")

    try:
        s = detect_resistance_breakout(df, "D", sw, mt, 5.0, zt)
        if s: signals.append(s)
    except Exception as e:
        logger.debug(f"Resistance daily error: {e}")

    try:
        s = detect_consolidation_breakout(df, "D", lb, mr)
        if s: signals.append(s)
    except Exception as e:
        logger.debug(f"Consolidation daily error: {e}")

    # ── WEEKLY SCANS ──────────────────────────────────────────
    if len(df) >= 60:  # Need enough data for weekly candles
        try:
            wdf = resample_weekly(df)
            if wdf is not None and len(wdf) >= 20:

                try:
                    s = detect_52week_breakout(wdf, "W")
                    if s: signals.append(s)
                except Exception as e:
                    logger.debug(f"52W weekly error: {e}")

                try:
                    s = detect_resistance_breakout(wdf, "W", sw, mt, 4.0, zt)
                    if s: signals.append(s)
                except Exception as e:
                    logger.debug(f"Resistance weekly error: {e}")

                try:
                    s = detect_consolidation_breakout(wdf, "W", 15, mr)
                    if s: signals.append(s)
                except Exception as e:
                    logger.debug(f"Consolidation weekly error: {e}")

        except Exception as e:
            logger.debug(f"Weekly resample error: {e}")

    return signals
