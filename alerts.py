"""
alerts.py — Telegram alerts for all 5 strategies
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


def format_signal(sig):
    """Format any signal type into clean readable lines."""
    lines = []
    strategy = sig.get("strategy", "")
    stype    = sig.get("type", "")
    label    = sig.get("label", "Setup")
    current  = sig.get("current")
    weekly   = sig.get("weekly_flag", False)
    note     = sig.get("weekly_note", "")

    lines.append(f"  *{label}*")

    # ── Breakout signals ──
    if strategy == "BREAKOUT":
        broke     = sig.get("broke_above")
        vol_ratio = sig.get("vol_ratio")
        lines.append(f"     Broke: ₹{broke}  →  Now: ₹{current}")
        lines.append(f"     Volume: {vol_ratio}x median")
        if stype == "RESISTANCE":
            lines.append(f"     Resistance touches: {sig.get('touches', '-')}")
        if stype == "CONSOLIDATION":
            lines.append(f"     Range: {sig.get('range_days')}d tight ({sig.get('range_pct')}%)")

    # ── Support Zone signals ──
    elif strategy == "SR":
        zone  = sig.get("zone_price")
        touch = sig.get("touches")
        sit   = sig.get("situation", "")
        lines.append(f"     Zone: ₹{zone}  |  Now: ₹{current}")
        lines.append(f"     Touches: {touch}  |  {sit}")

    # ── OB Retest ──
    elif strategy == "SMC" and stype == "OB_RETEST":
        ob_hi = sig.get("ob_high")
        ob_lo = sig.get("ob_low")
        bos   = sig.get("bos_level")
        sit   = sig.get("situation", "")
        lines.append(f"     OB Zone: ₹{ob_lo} – ₹{ob_hi}  |  Now: ₹{current}")
        lines.append(f"     BOS was at: ₹{bos}")
        lines.append(f"     {sit}")

    # Weekly flag
    if weekly and note:
        lines.append(f"     {note}")

    return "\n".join(lines)


def format_alert_message(date_str, results):
    if not results:
        return (
            f"📊 *Swing Scanner — {date_str}*\n\n"
            "✅ Scan complete. No setups today.\n"
            "Stay patient — right setups will come."
        )

    lines = [f"🚨 *Swing Setups — {date_str}*\n"]

    # Separate weekly-level setups to show first
    weekly_items = [(r, s) for r in results for s in r["signals"] if s.get("weekly_flag")]
    if weekly_items:
        lines.append("⭐ *WEEKLY-LEVEL SETUPS:*")
        seen = set()
        for r, s in weekly_items:
            sym = r["symbol"].replace(".NS", "")
            key = (sym, s.get("type"))
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"\n━━━━━━━━━━━━")
            lines.append(f"📌 *{sym}*")
            lines.append(format_signal(s))
        lines.append(f"\n📋 *ALL SETUPS:*")

    for item in results:
        sym     = item["symbol"].replace(".NS", "")
        signals = item["signals"]
        lines.append(f"\n━━━━━━━━━━━━")
        lines.append(f"📌 *{sym}*")
        for sig in signals:
            lines.append(format_signal(sig))

    lines.append(f"\n━━━━━━━━━━━━")
    lines.append("⚡ Verify before entering. Trade safe.")
    lines.append("🤖 Swing Scanner Bot")
    return "\n".join(lines)


def send_scan_results(bot_token, chat_id, date_str, results):
    BATCH_SIZE = 12
    if not results:
        send_telegram(bot_token, chat_id, format_alert_message(date_str, []))
        return
    for i in range(0, len(results), BATCH_SIZE):
        batch = results[i: i + BATCH_SIZE]
        part  = f"(Part {i // BATCH_SIZE + 1})" if len(results) > BATCH_SIZE else ""
        msg   = format_alert_message(f"{date_str} {part}", batch)
        send_telegram(bot_token, chat_id, msg)
        if i + BATCH_SIZE < len(results):
            time.sleep(1)


# ── Overwrite send_scan_results to support skip_message ──────
_original_send_scan_results = send_scan_results

def send_scan_results(bot_token, chat_id, date_str, results, skip_message=None):
    """Extended version — supports holiday skip message."""
    if skip_message:
        send_telegram(bot_token, chat_id, f"📅 *Swing Scanner — {date_str}*\n\n{skip_message}")
        return
    _original_send_scan_results(bot_token, chat_id, date_str, results)
