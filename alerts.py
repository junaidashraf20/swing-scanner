"""
alerts.py — Clean simple Telegram alerts for breakout scanner
"""

import urllib.request
import json
import logging
import time

logger = logging.getLogger(__name__)
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


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


def format_signal_line(sig):
    """One clean line per signal."""
    stype    = sig.get("type", "")
    tf       = sig.get("timeframe", "D")
    broke    = sig.get("broke_above")
    current  = sig.get("current")
    vol      = sig.get("vol_ratio")
    tf_tag   = "〔W〕" if tf == "W" else "〔D〕"

    if stype == "52_WEEK_HIGH":
        return f"  🏆 {tf_tag} 52-Week High  |  Broke ₹{broke}  |  Vol {vol}x"

    elif stype == "RESISTANCE":
        touches = sig.get("touches", "")
        return f"  🔓 {tf_tag} Resistance Break  |  ₹{broke} ({touches} touches)  |  Vol {vol}x"

    elif stype == "CONSOLIDATION":
        rng  = sig.get("range_pct")
        bars = sig.get("range_candles")
        return f"  📦 {tf_tag} Consolidation Break  |  ₹{broke} ({rng}% range, {bars} candles)  |  Vol {vol}x"

    return f"  💥 {tf_tag} Breakout  |  ₹{broke}  |  Vol {vol}x"


def format_alert_message(date_str, results):
    if not results:
        return (
            f"📊 *Swing Scanner — {date_str}*\n\n"
            "No breakout setups found today.\n"
            "Stay patient. 🙏"
        )

    # Separate weekly and daily signals
    weekly = [(r, s) for r in results for s in r["signals"] if s.get("weekly_flag")]
    daily  = [(r, s) for r in results for s in r["signals"] if not s.get("weekly_flag")]

    lines = [f"🚨 *Breakout Alerts — {date_str}*"]
    lines.append(f"_{len(results)} stocks found_\n")

    # Weekly setups first — higher priority
    if weekly:
        lines.append("⭐ *WEEKLY SETUPS — wait for weekly close:*")
        seen = set()
        for r, s in weekly:
            sym = r["symbol"].replace(".NS", "")
            key = (sym, s.get("type"), s.get("timeframe"))
            if key in seen: continue
            seen.add(key)
            lines.append(f"\n*{sym}*")
            lines.append(format_signal_line(s))
            lines.append(f"  📍 Now: ₹{s.get('current')}")

    # Daily setups
    if daily:
        lines.append("\n📋 *DAILY SETUPS — can enter on close:*")
        seen = set()
        for r, s in daily:
            sym = r["symbol"].replace(".NS", "")
            key = (sym, s.get("type"), s.get("timeframe"))
            if key in seen: continue
            seen.add(key)
            lines.append(f"\n*{sym}*")
            lines.append(format_signal_line(s))
            lines.append(f"  📍 Now: ₹{s.get('current')}")

    lines.append("\n─────────────────")
    lines.append("⚡ Verify before entering. Trade safe.")
    lines.append("🤖 Swing Scanner")
    return "\n".join(lines)


def send_scan_results(bot_token, chat_id, date_str, results, skip_message=None):
    if skip_message:
        send_telegram(bot_token, chat_id,
                      f"📅 *Swing Scanner — {date_str}*\n\n{skip_message}")
        return

    BATCH = 15
    if not results:
        send_telegram(bot_token, chat_id, format_alert_message(date_str, []))
        return

    for i in range(0, len(results), BATCH):
        batch = results[i: i + BATCH]
        part  = f"(Part {i // BATCH + 1})" if len(results) > BATCH else ""
        msg   = format_alert_message(f"{date_str} {part}", batch)
        send_telegram(bot_token, chat_id, msg)
        if i + BATCH < len(results):
            time.sleep(1)
