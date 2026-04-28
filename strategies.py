"""
strategies.py — 5 personalized strategies
──────────────────────────────────────────
1. 52-Week High Breakout
2. Resistance Level Breakout
3. Consolidation Range Breakout
4. Support Zone (3+ touches, price at/near support)
5. OB Retest (bullish — broke out, pulled back to OB, ready to continue)

All bullish only. Volume above 20-day median required for breakouts.
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

def is_bullish_close(candle):
    return float(candle["Close"]) > float(candle["Open"])

def volume_above_median(df, period=20):
    med = median_volume(df, period)
    today_vol = float(df["Volume"].iloc[-1])
    if med <= 0:
        return False, 0.0
    ratio = today_vol / med
    return ratio >= 1.0, round(ratio, 2)

def find_swing_highs(df, window=5):
    highs = []
    n = len(df)
    for i in range(window, n - window):
        local_max = df["High"].iloc[i - window: i + window + 1].max()
        if df["High"].iloc[i] == local_max:
            highs.append((i, float(df["High"].iloc[i])))
    return highs

def find_swing_lows(df, window=5):
    lows = []
    n = len(df)
    for i in range(window, n - window):
        local_min = df["Low"].iloc[i - window: i + window + 1].min()
        if df["Low"].iloc[i] == local_min:
            lows.append((i, float(df["Low"].iloc[i])))
    return lows

def is_weekly_level(price, df, threshold=0.025):
    year_high = float(df["High"].tail(252).max())
    year_low  = float(df["Low"].tail(252).min())
    weekly_refs = [year_high, year_low]
    swing_highs = find_swing_highs(df, window=10)
    if swing_highs:
        top_swings = sorted(swing_highs, key=lambda x: x[1], reverse=True)[:3]
        weekly_refs += [s[1] for s in top_swings]
    for ref in weekly_refs:
        if ref > 0 and abs(price - ref) / ref < threshold:
            return True
    return False

def cluster_levels(prices, threshold=0.02):
    """Group nearby price levels into clusters."""
    if not prices:
        return []
    prices = sorted(prices)
    clusters = [[prices[0]]]
    for p in prices[1:]:
        if abs(p - clusters[-1][-1]) / clusters[-1][-1] < threshold:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    return clusters


# ════════════════════════════════════════════════════════════════
#  1. 52-WEEK HIGH BREAKOUT
# ════════════════════════════════════════════════════════════════

def detect_52week_breakout(df):
    if len(df) < 252:
        return None
    today       = df.iloc[-1]
    prev_close  = float(df["Close"].iloc[-2])
    year_high   = float(df["High"].iloc[-252:-1].max())
    today_close = float(today["Close"])
    if not (prev_close <= year_high < today_close):
        return None
    if not is_bullish_close(today):
        return None
    vol_ok, vol_ratio = volume_above_median(df)
    if not vol_ok:
        return None
    return {
        "strategy":    "BREAKOUT",
        "type":        "52_WEEK_HIGH",
        "label":       "52-Week High Breakout 🏆",
        "broke_above": round(year_high, 2),
        "current":     round(today_close, 2),
        "vol_ratio":   vol_ratio,
        "weekly_flag": True,
        "weekly_note": "⭐ Major weekly level — consider waiting for weekly close",
    }


# ════════════════════════════════════════════════════════════════
#  2. RESISTANCE LEVEL BREAKOUT
# ════════════════════════════════════════════════════════════════

def detect_resistance_breakout(df, swing_window=5, min_touches=2, zone_threshold=0.02):
    today_close = float(df["Close"].iloc[-1])
    prev_close  = float(df["Close"].iloc[-2])
    today       = df.iloc[-1]
    if not is_bullish_close(today):
        return None
    vol_ok, vol_ratio = volume_above_median(df)
    if not vol_ok:
        return None
    swing_highs = find_swing_highs(df.iloc[:-1], swing_window)
    if not swing_highs:
        return None
    clusters = cluster_levels([s[1] for s in swing_highs], zone_threshold)
    best = None
    for cluster in clusters:
        if len(cluster) < min_touches:
            continue
        zone_price = float(np.mean(cluster))
        if prev_close <= zone_price < today_close:
            if best is None or zone_price > best["broke_above"]:
                weekly = is_weekly_level(zone_price, df)
                best = {
                    "strategy":    "BREAKOUT",
                    "type":        "RESISTANCE",
                    "label":       "Resistance Level Breakout 🔓",
                    "broke_above": round(zone_price, 2),
                    "current":     round(today_close, 2),
                    "touches":     len(cluster),
                    "vol_ratio":   vol_ratio,
                    "weekly_flag": weekly,
                    "weekly_note": "⭐ Weekly resistance — consider waiting for weekly close" if weekly else "",
                }
    return best


# ════════════════════════════════════════════════════════════════
#  3. CONSOLIDATION BREAKOUT
# ════════════════════════════════════════════════════════════════

def detect_consolidation_breakout(df, lookback=30, max_range_pct=0.18):
    if len(df) < lookback + 2:
        return None
    consol      = df.iloc[-(lookback + 1):-1]
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
    weekly = is_weekly_level(hi, df)
    return {
        "strategy":    "BREAKOUT",
        "type":        "CONSOLIDATION",
        "label":       f"{lookback}-Day Consolidation Breakout 📦",
        "broke_above": round(hi, 2),
        "current":     round(today_close, 2),
        "range_pct":   round(rng * 100, 1),
        "range_days":  lookback,
        "vol_ratio":   vol_ratio,
        "weekly_flag": weekly,
        "weekly_note": "⭐ Aligns with weekly level — consider waiting for weekly close" if weekly else "",
    }


# ════════════════════════════════════════════════════════════════
#  4. SUPPORT ZONE (3+ touches, price at/near support)
# ════════════════════════════════════════════════════════════════

def detect_support_zone(df, swing_window=5, min_touches=3,
                         zone_threshold=0.02, proximity=0.02):
    """
    Finds key support zones (swing lows + round numbers) with 3+ touches.
    Alerts when:
      - Price is bouncing OFF support (today bullish, low touched zone)
      - Price is sitting NEAR support (within proximity %) — good safety net
    """
    today       = df.iloc[-1]
    today_close = float(today["Close"])
    today_low   = float(today["Low"])

    swing_lows = find_swing_lows(df.iloc[:-1], swing_window)
    if not swing_lows:
        return []

    # Add round number levels near current price
    round_levels = []
    for multiple in [10, 50, 100, 200, 500, 1000]:
        base = round(today_close / multiple) * multiple
        for offset in [-1, 0, 1]:
            lvl = base + offset * multiple
            if lvl > 0:
                round_levels.append(lvl)

    all_levels = [s[1] for s in swing_lows] + round_levels
    clusters   = cluster_levels(all_levels, zone_threshold)

    signals = []
    for cluster in clusters:
        swing_count = sum(1 for p in cluster if p in [s[1] for s in swing_lows])
        if swing_count < min_touches:
            continue

        zone_price = float(np.mean(cluster))

        # Only support zones BELOW current price
        if zone_price >= today_close:
            continue

        dist_pct = (today_close - zone_price) / zone_price

        # Bounce: today's low touched the zone and closed bullish
        if dist_pct <= proximity and is_bullish_close(today):
            weekly = is_weekly_level(zone_price, df)
            signals.append({
                "strategy":    "SR",
                "type":        "SUPPORT_BOUNCE",
                "label":       "Support Zone Bounce 🔷",
                "zone_price":  round(zone_price, 2),
                "current":     round(today_close, 2),
                "touches":     swing_count,
                "dist_pct":    round(dist_pct * 100, 1),
                "situation":   "Price bouncing off support",
                "weekly_flag": weekly,
                "weekly_note": "⭐ Weekly support — strong level" if weekly else "",
            })

        # Near support: price sitting just above zone (safety net context)
        elif proximity < dist_pct <= proximity * 2.5:
            weekly = is_weekly_level(zone_price, df)
            signals.append({
                "strategy":    "SR",
                "type":        "SUPPORT_NEAR",
                "label":       "Near Strong Support 🔵",
                "zone_price":  round(zone_price, 2),
                "current":     round(today_close, 2),
                "touches":     swing_count,
                "dist_pct":    round(dist_pct * 100, 1),
                "situation":   f"Support {round(dist_pct*100,1)}% below — good safety net",
                "weekly_flag": weekly,
                "weekly_note": "⭐ Weekly support below" if weekly else "",
            })

    return signals


# ════════════════════════════════════════════════════════════════
#  5. ORDER BLOCK RETEST (bullish continuation)
# ════════════════════════════════════════════════════════════════

def detect_ob_retest(df, swing_window=5):
    """
    Scenario: Stock previously broke out (BOS bullish).
    Price pulled back and is now retesting the Order Block
    (last bearish candle before the BOS move).
    This is a bullish continuation setup.
    """
    today_close = float(df["Close"].iloc[-1])
    today       = df.iloc[-1]
    n           = len(df)

    swing_highs = find_swing_highs(df, swing_window)
    if len(swing_highs) < 2:
        return None

    # Look for a recent bullish BOS (broke a swing high)
    recent_highs = sorted(swing_highs, key=lambda x: x[0])

    for i in range(len(recent_highs) - 2, max(0, len(recent_highs) - 6), -1):
        bos_idx, bos_level = recent_highs[i]

        # Confirm a BOS happened after this swing high
        later_closes = df["Close"].iloc[bos_idx + 1:]
        if later_closes.empty or float(later_closes.max()) <= bos_level:
            continue  # No BOS here

        # Find the Order Block: last bearish candle BEFORE the BOS swing high
        ob = None
        search_start = max(0, bos_idx - 15)
        for j in range(bos_idx - 1, search_start - 1, -1):
            if float(df["Close"].iloc[j]) < float(df["Open"].iloc[j]):  # bearish candle
                ob = {
                    "ob_high": round(float(df["High"].iloc[j]), 2),
                    "ob_low":  round(float(df["Low"].iloc[j]), 2),
                }
                break

        if ob is None:
            continue

        # Check if today's price is retesting inside the OB zone
        ob_mid = (ob["ob_high"] + ob["ob_low"]) / 2
        if ob["ob_low"] * 0.995 <= today_close <= ob["ob_high"] * 1.005:
            # Price must be above the BOS level (confirmed bull trend)
            if today_close > bos_level * 0.97:
                weekly = is_weekly_level(ob_mid, df)
                return {
                    "strategy":    "SMC",
                    "type":        "OB_RETEST",
                    "label":       "Order Block Retest 🎯",
                    "ob_high":     ob["ob_high"],
                    "ob_low":      ob["ob_low"],
                    "bos_level":   round(bos_level, 2),
                    "current":     round(today_close, 2),
                    "situation":   "Broke out → pulled back to OB → potential continuation",
                    "weekly_flag": weekly,
                    "weekly_note": "⭐ OB aligns with weekly level — high quality setup" if weekly else "",
                }

    return None


# ════════════════════════════════════════════════════════════════
#  UNIFIED RUNNER
# ════════════════════════════════════════════════════════════════

def run_all_strategies(df, cfg):
    """Run all 5 strategies. Returns list of triggered signals."""
    if df is None or len(df) < 35:
        return []

    signals = []

    # ── Breakouts ──
    try:
        s = detect_52week_breakout(df)
        if s: signals.append(s)
    except Exception as e:
        logger.debug(f"52W error: {e}")

    try:
        s = detect_resistance_breakout(
            df,
            swing_window   = cfg.get("SR_SWING_WINDOW", 5),
            min_touches    = cfg.get("SR_MIN_TOUCHES", 2),
            zone_threshold = cfg.get("SR_ZONE_THRESHOLD", 0.02),
        )
        if s: signals.append(s)
    except Exception as e:
        logger.debug(f"Resistance error: {e}")

    try:
        s = detect_consolidation_breakout(
            df,
            lookback      = cfg.get("BREAKOUT_LOOKBACK", 30),
            max_range_pct = cfg.get("BREAKOUT_MAX_RANGE", 0.18),
        )
        if s: signals.append(s)
    except Exception as e:
        logger.debug(f"Consolidation error: {e}")

    # ── Support Zone ──
    try:
        sr_signals = detect_support_zone(
            df,
            swing_window  = cfg.get("SR_SWING_WINDOW", 5),
            min_touches   = cfg.get("SR_MIN_TOUCHES", 3),
            zone_threshold= cfg.get("SR_ZONE_THRESHOLD", 0.02),
            proximity     = cfg.get("SR_PROXIMITY", 0.02),
        )
        signals.extend(sr_signals)
    except Exception as e:
        logger.debug(f"Support zone error: {e}")

    # ── OB Retest ──
    try:
        s = detect_ob_retest(df, swing_window=cfg.get("SMC_SWING_WINDOW", 5))
        if s: signals.append(s)
    except Exception as e:
        logger.debug(f"OB retest error: {e}")

    return signals
