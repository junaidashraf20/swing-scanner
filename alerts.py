"""
alerts.py — 3-tier message system
  Personal     → full technical detail
  Intermediate → medium detail + SL zone
  Beginner     → simple: Buy above X, SL Y, Target Z
"""

import urllib.request
import json
import logging
import time

logger = logging.getLogger(__name__)
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_CHARS    = 4000
MAX_SL_RISK  = 0.08   # skip SL/Target if risk > 8% of entry


# ════════════════════════════════════════════════════════════════
#  CORE SENDER
# ════════════════════════════════════════════════════════════════

def send_telegram(bot_token, chat_id, message):
    url  = TELEGRAM_API.format(token=bot_token)
    data = json.dumps({
        "chat_id":    chat_id,
        "text":       message,
        "parse_mode": "Markdown",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data,
          headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
            if body.get("ok"):
                logger.info("Telegram alert sent ✅")
                return True
            logger.error(f"Telegram error: {body}")
            return False
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False


# ════════════════════════════════════════════════════════════════
#  TRADE PLAN CALCULATOR  (SL + Target for 1:2 RR)
# ════════════════════════════════════════════════════════════════

def calc_trade_plan(sig):
    """
    Returns (entry, sl, target, risk_pct, is_valid).
    entry  = breakout level
    sl     = recent base low
    target = entry + 2 × risk  (1:2 RR)
    risk_pct = risk as % of entry
    is_valid = False if risk > 8% (too wide for beginners)
    """
    entry    = float(sig.get("broke_above", 0))
    base_low = float(sig.get("base_low", 0))

    if entry <= 0 or base_low <= 0 or base_low >= entry:
        return entry, None, None, None, False

    risk     = entry - base_low
    risk_pct = risk / entry

    if risk_pct > MAX_SL_RISK:
        return entry, base_low, None, risk_pct, False  # too wide

    target = round(entry + 2 * risk, 2)
    return (
        round(entry, 2),
        round(base_low, 2),
        target,
        round(risk_pct * 100, 1),
        True
    )


# ════════════════════════════════════════════════════════════════
#  FORMAT — PERSONAL (full technical detail)
# ════════════════════════════════════════════════════════════════

def format_signal_personal(sig):
    stype  = sig.get("type", "")
    tf     = sig.get("timeframe", "D")
    broke  = sig.get("broke_above")
    curr   = sig.get("current")
    vol    = sig.get("vol_ratio")
    ext    = sig.get("extension", "")
    tf_tag = "Weekly" if tf == "W" else "Daily"
    ext_str = f" | Ext {ext}%" if ext else ""

    if stype == "52_WEEK_HIGH":
        return (
            f"  🏆 *52-Week High Breakout* [{tf_tag}]\n"
            f"     Broke ₹{broke} → Now ₹{curr} | Vol {vol}x{ext_str}"
        )
    elif stype == "RESISTANCE":
        touches  = sig.get("touches", "")
        strength = sig.get("strength", "")
        return (
            f"  🔓 *Resistance Breakout* [{tf_tag}]\n"
            f"     Broke ₹{broke} ({touches}T, str {strength}) → Now ₹{curr} | Vol {vol}x{ext_str}"
        )
    elif stype == "CONSOLIDATION":
        rng  = sig.get("range_pct")
        bars = sig.get("range_candles")
        return (
            f"  📦 *Consolidation Breakout* [{tf_tag}]\n"
            f"     Broke ₹{broke} ({bars}d base, {rng}% tight) → Now ₹{curr} | Vol {vol}x{ext_str}"
        )
    elif stype == "ORDER_BLOCK":
        return (
            f"  📦⬆️ *Bullish Order Block Breakout* [{tf_tag}]\n"
            f"     Broke ₹{broke} → Now ₹{curr} | Vol {vol}x{ext_str}"
        )
    return f"  💥 Breakout ₹{broke} → ₹{curr} | Vol {vol}x [{tf_tag}]"


# ════════════════════════════════════════════════════════════════
#  FORMAT — INTERMEDIATE (medium detail + SL)
# ════════════════════════════════════════════════════════════════

def format_signal_intermediate(sig):
    stype  = sig.get("type", "")
    tf     = sig.get("timeframe", "D")
    broke  = sig.get("broke_above")
    curr   = sig.get("current")
    vol    = sig.get("vol_ratio")
    tf_tag = "Weekly" if tf == "W" else "Daily"
    entry, sl, target, risk_pct, valid = calc_trade_plan(sig)

    vol_label = "Strong 💪" if vol and vol >= 2.0 else "Above avg ✅" if vol and vol >= 1.5 else "Moderate"

    if stype == "52_WEEK_HIGH":
        line = f"  🏆 *52-Week High Breakout* [{tf_tag}]\n     Breakout above ₹{broke} | Now ₹{curr}\n     Volume: {vol_label} ({vol}x)"
    elif stype == "RESISTANCE":
        touches = sig.get("touches", "")
        line = f"  🔓 *Resistance Breakout* [{tf_tag}]\n     Broke key level ₹{broke} ({touches}-touch) | Now ₹{curr}\n     Volume: {vol_label} ({vol}x)"
    elif stype == "CONSOLIDATION":
        rng  = sig.get("range_pct")
        bars = sig.get("range_candles")
        line = f"  📦 *Consolidation Breakout* [{tf_tag}]\n     Tight {rng}% base broke ₹{broke} | Now ₹{curr}\n     Volume: {vol_label} ({vol}x)"
    elif stype == "ORDER_BLOCK":
        line = f"  📦⬆️ *Bullish Order Block* [{tf_tag}]\n     Breakout ₹{broke} | Now ₹{curr}\n     Volume: {vol_label} ({vol}x)"
    else:
        line = f"  💥 Breakout ₹{broke} → ₹{curr} | Vol {vol}x [{tf_tag}]"

    if valid:
        line += f"\n     SL zone: ₹{sl} | Risk: {risk_pct}%"
    elif sl:
        line += f"\n     SL zone: ₹{sl} | Risk wide ({risk_pct}%) — size carefully"

    return line


# ════════════════════════════════════════════════════════════════
#  FORMAT — BEGINNER (simple trade plan)
# ════════════════════════════════════════════════════════════════

def format_signal_beginner(sig):
    stype  = sig.get("type", "")
    tf     = sig.get("timeframe", "D")
    broke  = sig.get("broke_above")
    vol    = sig.get("vol_ratio")
    tf_tag = "Weekly" if tf == "W" else "Daily"
    entry, sl, target, risk_pct, valid = calc_trade_plan(sig)

    vol_label = "Strong 💪" if vol and vol >= 2.0 else "Good ✅"

    if stype == "52_WEEK_HIGH":
        type_label = "Fresh 52-Week High"
    elif stype == "RESISTANCE":
        type_label = "Key Resistance Break"
    elif stype == "CONSOLIDATION":
        type_label = "Range Breakout"
    elif stype == "ORDER_BLOCK":
        type_label = "Block Breakout"
    else:
        type_label = "Breakout"

    lines = [f"  📊 *{type_label}* [{tf_tag}]"]
    lines.append(f"  ✅ *Buy above:* ₹{broke}")

    if valid:
        lines.append(f"  🛑 *Stop Loss:* ₹{sl}")
        lines.append(f"  🎯 *Target:* ₹{target}  _(1:2 RR)_")
    elif sl:
        lines.append(f"  🛑 *Stop Loss:* ₹{sl}  _(risk is wide — use small qty)_")
        lines.append(f"  🎯 Target: Calculate manually")
    else:
        lines.append(f"  🛑 *Stop Loss:* Below recent low")
        lines.append(f"  🎯 Target: 2× your risk from entry")

    lines.append(f"  📈 Volume: {vol_label}")
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════
#  MESSAGE BUILDERS
# ════════════════════════════════════════════════════════════════

def _build(date_str, results, fmt_fn, header="🚨 *Breakout Alerts*"):
    if not results:
        return (
            f"📊 *Swing Scanner — {date_str}*\n\n"
            "No breakout setups today.\nStay patient. 🙏"
        )

    weekly_count = sum(1 for r in results for s in r["signals"] if s.get("weekly_flag"))
    parts = [
        f"{header} — {date_str}",
        f"_{len(results)} stocks | ⭐ {weekly_count} weekly_",
        "─────────────────",
    ]

    weekly_r = [r for r in results if any(s.get("weekly_flag") for s in r["signals"])]
    daily_r  = [r for r in results if not any(s.get("weekly_flag") for s in r["signals"])]

    if weekly_r:
        parts.append("\n⭐ *WEEKLY — Wait for weekly close:*")
        for item in weekly_r:
            sym = item["symbol"].replace(".NS", "")
            has_w = any(s.get("weekly_flag") for s in item["signals"])
            parts.append(f"\n📌 *{sym}*{' ⭐' if has_w else ''}")
            sorted_sigs = sorted(item["signals"], key=lambda s: 0 if s.get("weekly_flag") else 1)
            for sig in sorted_sigs:
                parts.append(fmt_fn(sig))
                if sig.get("weekly_flag"):
                    parts.append("     _(Wait for weekly candle close)_")

    if daily_r:
        parts.append("\n📋 *DAILY — Can enter on close:*")
        for item in daily_r:
            sym = item["symbol"].replace(".NS", "")
            parts.append(f"\n📌 *{sym}*")
            for sig in item["signals"]:
                parts.append(fmt_fn(sig))

    parts.append("\n─────────────────")
    parts.append("📈 *Tradify Team*")
    parts.append("⚠️ _Not SEBI advice. Do your own analysis._")
    return "\n".join(parts)


def build_message_personal(date_str, results):
    return _build(date_str, results, format_signal_personal,
                  "🚨 *Breakout Alerts — Full Detail*")

def build_message_intermediate(date_str, results):
    return _build(date_str, results, format_signal_intermediate,
                  "🚨 *Breakout Alerts*")

def build_message_beginner(date_str, results):
    return _build(date_str, results, format_signal_beginner,
                  "📊 *Today's Trade Setups*")


# ════════════════════════════════════════════════════════════════
#  SEND FUNCTIONS
# ════════════════════════════════════════════════════════════════

def _send_with_split(bot_token, chat_id, date_str, results, build_fn):
    """Send message, split into batches if too long."""
    full_msg = build_fn(date_str, results)
    if len(full_msg) <= MAX_CHARS:
        send_telegram(bot_token, chat_id, full_msg)
        return
    BATCH = 8
    for i in range(0, len(results), BATCH):
        batch = results[i: i + BATCH]
        part  = f" (Part {i//BATCH + 1})" if len(results) > BATCH else ""
        send_telegram(bot_token, chat_id, build_fn(f"{date_str}{part}", batch))
        if i + BATCH < len(results):
            time.sleep(1)


def send_scan_results(bot_token, chat_id, date_str, results, skip_message=None):
    """Legacy single-chat sender — used for holiday skip messages."""
    if skip_message:
        send_telegram(bot_token, chat_id, f"📅 *{date_str}*\n\n{skip_message}")
        return
    if not results:
        send_telegram(bot_token, chat_id, build_message_personal(date_str, []))
        return
    _send_with_split(bot_token, chat_id, date_str, results, build_message_personal)


def send_scan_results_multi(bot_token, chat_cfg, date_str, results, skip_message=None):
    """
    Sends different message formats to different chats.

    chat_cfg = {
        "personal":     "chat_id_here",
        "intermediate": "chat_id_here",
        "beginner":     "chat_id_here",
    }
    """
    PLACEHOLDERS = {
        "YOUR_PERSONAL_CHAT_ID", "YOUR_GROUP_1_ID",
        "YOUR_GROUP_2_ID", "PASTE_YOUR_CHAT_ID_HERE", "",
    }

    format_map = {
        "personal":     (build_message_personal,     "Personal"),
        "intermediate": (build_message_intermediate, "Intermediate"),
        "beginner":     (build_message_beginner,     "Beginner"),
    }

    for key, (build_fn, label) in format_map.items():
        chat_id = chat_cfg.get(key, "")
        if not chat_id or chat_id in PLACEHOLDERS:
            continue
        try:
            if skip_message:
                send_telegram(bot_token, chat_id, f"📅 *{date_str}*\n\n{skip_message}")
            elif not results:
                send_telegram(bot_token, chat_id, build_fn(date_str, []))
            else:
                _send_with_split(bot_token, chat_id, date_str, results, build_fn)
            logger.info(f"  ✅ Sent [{label}] to {chat_id}")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"  ❌ Failed [{label}] {chat_id}: {e}")


# ════════════════════════════════════════════════════════════════
#  EARLY RALLY — Separate Message (same to all)
# ════════════════════════════════════════════════════════════════

def build_early_rally_message(date_str, results):
    if not results:
        return None
    parts = [
        f"🚀 *Early Rally Watch — {date_str}*",
        "_Volume explosion after quiet base — catch it early_",
        "─────────────────",
    ]
    weekly = [r for r in results if any(s.get("weekly_flag") for s in r["signals"])]
    daily  = [r for r in results if not any(s.get("weekly_flag") for s in r["signals"])]

    if weekly:
        parts.append("\n⭐ *WEEKLY:*")
        for item in weekly:
            sym = item["symbol"].replace(".NS", "")
            for sig in item["signals"]:
                parts.append(f"\n📌 *{sym}* ⭐")
                parts.append(
                    f"  🚀 VCP Breakout [Weekly]\n"
                    f"     Base broke ₹{sig['broke_above']} → Now ₹{sig['current']}\n"
                    f"     Vol explosion: {sig['explosion_ratio']}x base avg | {sig['overall_vol']}x median\n"
                    f"     Base: {sig['base_range']}% range ({sig['base_tightness']})"
                )
                parts.append("     _(Wait for weekly candle close)_")

    if daily:
        parts.append("\n📋 *DAILY:*")
        for item in daily:
            sym = item["symbol"].replace(".NS", "")
            for sig in item["signals"]:
                parts.append(f"\n📌 *{sym}*")
                parts.append(
                    f"  🚀 VCP Breakout [Daily]\n"
                    f"     Base broke ₹{sig['broke_above']} → Now ₹{sig['current']}\n"
                    f"     Vol explosion: {sig['explosion_ratio']}x base avg | {sig['overall_vol']}x median\n"
                    f"     Base: {sig['base_range']}% range ({sig['base_tightness']})"
                )

    parts.append("\n─────────────────")
    parts.append("⚡ _Potential rally starters — high conviction._")
    parts.append("📈 *Tradify Team*")
    parts.append("⚠️ _Not SEBI advice. Educational scans only._")
    return "\n".join(parts)


def send_early_rally_alerts(bot_token, chat_cfg, date_str, results):
    if not results:
        return
    msg = build_early_rally_message(date_str, results)
    if not msg:
        return
    PLACEHOLDERS = {
        "YOUR_PERSONAL_CHAT_ID", "YOUR_GROUP_1_ID",
        "YOUR_GROUP_2_ID", "PASTE_YOUR_CHAT_ID_HERE", "",
    }
    # Send to all valid chats
    for key, chat_id in chat_cfg.items():
        if not chat_id or chat_id in PLACEHOLDERS:
            continue
        try:
            send_telegram(bot_token, chat_id, msg)
            logger.info(f"  ✅ Early Rally sent to [{key}] {chat_id}")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"  ❌ Failed early rally [{key}]: {e}")
