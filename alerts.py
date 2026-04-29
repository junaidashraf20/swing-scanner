"""
alerts.py — Compact single-message Telegram alerts
"""

import urllib.request
import json
import logging
import time

logger = logging.getLogger(__name__)
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_CHARS = 4000  # Telegram limit is 4096 — leave buffer


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


def signal_line(sig):
    """Ultra compact single line per signal."""
    stype = sig.get("type", "")
    tf    = "W" if sig.get("timeframe") == "W" else "D"
    broke = sig.get("broke_above")
    vol   = sig.get("vol_ratio")

    if stype == "52_WEEK_HIGH":
        return f"🏆[{tf}] 52W High ₹{broke} vol {vol}x"
    elif stype == "RESISTANCE":
        t = sig.get("touches", "")
        return f"🔓[{tf}] Resistance ₹{broke} ({t}T) vol {vol}x"
    elif stype == "CONSOLIDATION":
        r = sig.get("range_pct")
        return f"📦[{tf}] Consolidation ₹{broke} ({r}%) vol {vol}x"
    return f"💥[{tf}] Breakout ₹{broke} vol {vol}x"


def build_message(date_str, results):
    """
    Builds the most compact possible message.
    Weekly setups first, then daily.
    One line per stock per signal.
    """
    if not results:
        return (
            f"📊 *{date_str}*\n"
            "No breakout setups today. Stay patient."
        )

    weekly_lines = []
    daily_lines  = []

    for item in results:
        sym  = item["symbol"].replace(".NS", "")
        for sig in item["signals"]:
            line = f"*{sym}* — {signal_line(sig)}"
            if sig.get("weekly_flag"):
                weekly_lines.append(line)
            else:
                daily_lines.append(line)

    parts = [f"🚨 *Breakout Alerts — {date_str}*"]
    parts.append(f"_{len(results)} stocks | {len(weekly_lines)+len(daily_lines)} signals_\n")

    if weekly_lines:
        parts.append("⭐ *Weekly — wait for weekly close*")
        parts.extend(weekly_lines)

    if daily_lines:
        if weekly_lines:
            parts.append("")
        parts.append("📋 *Daily setups*")
        parts.extend(daily_lines)

    parts.append("\n─────────────────")
    parts.append("⚡ Verify before entering.")
    parts.append("🤖 Swing Scanner")

    return "\n".join(parts)


def split_into_messages(date_str, results):
    """
    Tries to fit everything in 1 message.
    Only splits if truly exceeds Telegram's 4096 char limit.
    """
    full_msg = build_message(date_str, results)

    if len(full_msg) <= MAX_CHARS:
        return [full_msg]  # Single message — ideal

    # Split by stocks only if necessary
    messages = []
    batch = []
    total = len(results)

    for i, item in enumerate(results):
        batch.append(item)
        test_msg = build_message(
            f"{date_str} ({len(messages)+1})",
            batch
        )
        if len(test_msg) > MAX_CHARS:
            # Send previous batch, start new one
            if len(batch) > 1:
                messages.append(build_message(
                    f"{date_str} (Part {len(messages)+1})",
                    batch[:-1]
                ))
                batch = [item]
            else:
                messages.append(test_msg[:MAX_CHARS])
                batch = []

    if batch:
        part = f" (Part {len(messages)+1})" if messages else ""
        messages.append(build_message(f"{date_str}{part}", batch))

    return messages


def send_scan_results(bot_token, chat_id, date_str, results, skip_message=None):
    if skip_message:
        send_telegram(bot_token, chat_id,
                      f"📅 *{date_str}*\n\n{skip_message}")
        return

    if not results:
        send_telegram(bot_token, chat_id, build_message(date_str, []))
        return

    messages = split_into_messages(date_str, results)
    logger.info(f"Sending {len(messages)} Telegram message(s) for {len(results)} stocks")

    for i, msg in enumerate(messages):
        send_telegram(bot_token, chat_id, msg)
        if i < len(messages) - 1:
            time.sleep(1)
