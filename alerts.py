"""
alerts.py — Complete Telegram alerts for Swing Scanner
"""

import urllib.request
import json
import logging
import time

logger = logging.getLogger(__name__)
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_CHARS = 4000


# ════════════════════════════════════════════════════════════════
#  CORE TELEGRAM SENDER
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
#  SIGNAL FORMATTING
# ════════════════════════════════════════════════════════════════

def format_signal(sig):
    stype  = sig.get("type", "")
    tf     = sig.get("timeframe", "D")
    broke  = sig.get("broke_above")
    curr   = sig.get("current")
    vol    = sig.get("vol_ratio")
    tf_tag = "Weekly" if tf == "W" else "Daily"

    if stype == "52_WEEK_HIGH":
        return (
            f"  🏆 *52-Week High Breakout* [{tf_tag}]\n"
            f"     Broke above ₹{broke} → Now ₹{curr} | Vol {vol}x median"
        )
    elif stype == "RESISTANCE":
        touches = sig.get("touches", "")
        return (
            f"  🔓 *Resistance Breakout* [{tf_tag}]\n"
            f"     Broke ₹{broke} ({touches}-touch level) → Now ₹{curr} | Vol {vol}x"
        )
    elif stype == "CONSOLIDATION":
        rng  = sig.get("range_pct")
        bars = sig.get("range_candles")
        return (
            f"  📦 *Consolidation Breakout* [{tf_tag}]\n"
            f"     Broke ₹{broke} ({bars}-candle base, {rng}% tight) → Now ₹{curr} | Vol {vol}x"
        )
    return f"  💥 Breakout ₹{broke} → ₹{curr} | Vol {vol}x [{tf_tag}]"


def build_stock_block(sym, signals):
    lines = []
    has_weekly = any(s.get("weekly_flag") for s in signals)
    weekly_tag = " ⭐" if has_weekly else ""
    lines.append(f"\n📌 *{sym}*{weekly_tag}")
    sorted_sigs = sorted(signals, key=lambda s: (0 if s.get("weekly_flag") else 1))
    for sig in sorted_sigs:
        lines.append(format_signal(sig))
        if sig.get("weekly_flag"):
            lines.append("     _(Wait for weekly candle close)_")
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════
#  MAIN BREAKOUT MESSAGE
# ════════════════════════════════════════════════════════════════

def build_message(date_str, results):
    if not results:
        return (
            f"📊 *Swing Scanner — {date_str}*\n\n"
            "No breakout setups today.\n"
            "Stay patient. Right setups will come. 🙏"
        )

    weekly_count = sum(
        1 for r in results
        for s in r["signals"] if s.get("weekly_flag")
    )

    parts = [
        f"🚨 *Breakout Alerts — {date_str}*",
        f"_{len(results)} stocks | ⭐ {weekly_count} weekly setups_",
        "─────────────────",
    ]

    weekly_results = [r for r in results if any(s.get("weekly_flag") for s in r["signals"])]
    daily_results  = [r for r in results if not any(s.get("weekly_flag") for s in r["signals"])]

    if weekly_results:
        parts.append("\n⭐ *WEEKLY SETUPS — Wait for weekly close:*")
        for item in weekly_results:
            sym = item["symbol"].replace(".NS", "")
            parts.append(build_stock_block(sym, item["signals"]))

    if daily_results:
        parts.append("\n📋 *DAILY SETUPS — Can enter on daily close:*")
        for item in daily_results:
            sym = item["symbol"].replace(".NS", "")
            parts.append(build_stock_block(sym, item["signals"]))

    parts.append("\n─────────────────")
    parts.append("📈 *Tradify Team*")
    parts.append("_Happy Trading! Do your own analysis before entering._")
    parts.append("⚠️ _Not SEBI registered advice. Educational scans only._")

    return "\n".join(parts)


def split_and_send(bot_token, chat_id, date_str, results):
    full_msg = build_message(date_str, results)
    if len(full_msg) <= MAX_CHARS:
        send_telegram(bot_token, chat_id, full_msg)
        return
    BATCH = 8
    for i in range(0, len(results), BATCH):
        batch = results[i: i + BATCH]
        part  = f" (Part {i//BATCH + 1})" if len(results) > BATCH else ""
        send_telegram(bot_token, chat_id, build_message(f"{date_str}{part}", batch))
        if i + BATCH < len(results):
            time.sleep(1)


def send_scan_results(bot_token, chat_id, date_str, results, skip_message=None):
    if skip_message:
        send_telegram(bot_token, chat_id, f"📅 *{date_str}*\n\n{skip_message}")
        return
    if not results:
        send_telegram(bot_token, chat_id, build_message(date_str, []))
        return
    split_and_send(bot_token, chat_id, date_str, results)


def send_scan_results_multi(bot_token, chat_ids, date_str, results, skip_message=None):
    valid_ids = [
        cid for cid in chat_ids
        if cid and cid not in (
            "YOUR_PERSONAL_CHAT_ID", "YOUR_GROUP_1_ID",
            "YOUR_GROUP_2_ID", "PASTE_YOUR_CHAT_ID_HERE",
        )
    ]
    if not valid_ids:
        logger.error("No valid chat IDs — check GitHub Secrets")
        return
    logger.info(f"Sending to {len(valid_ids)} recipient(s)...")
    for chat_id in valid_ids:
        try:
            send_scan_results(bot_token, chat_id, date_str, results, skip_message)
            logger.info(f"  ✅ Sent to {chat_id}")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"  ❌ Failed {chat_id}: {e}")


# ════════════════════════════════════════════════════════════════
#  EARLY RALLY — Separate Message
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
                    f"     Base range: {sig['base_range']}% ({sig['base_tightness']})\n"
                    f"     Candle closed at top {int(100 - sig['close_pos'])}% of range"
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
                    f"     Base range: {sig['base_range']}% ({sig['base_tightness']})\n"
                    f"     Candle closed at top {int(100 - sig['close_pos'])}% of range"
                )

    parts.append("\n─────────────────")
    parts.append("⚡ _These are potential rally starters — high conviction setups._")
    parts.append("📈 *Tradify Team*")
    parts.append("⚠️ _Not SEBI registered advice. Educational scans only._")
    return "\n".join(parts)


def send_early_rally_alerts(bot_token, chat_ids, date_str, results):
    if not results:
        return
    msg = build_early_rally_message(date_str, results)
    if not msg:
        return
    valid_ids = [
        cid for cid in chat_ids
        if cid and cid not in (
            "YOUR_PERSONAL_CHAT_ID", "YOUR_GROUP_1_ID",
            "YOUR_GROUP_2_ID", "PASTE_YOUR_CHAT_ID_HERE",
        )
    ]
    logger.info(f"Sending Early Rally alert to {len(valid_ids)} recipient(s)...")
    for chat_id in valid_ids:
        try:
            send_telegram(bot_token, chat_id, msg)
            logger.info(f"  ✅ Early Rally sent to {chat_id}")
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"  ❌ Failed {chat_id}: {e}")
