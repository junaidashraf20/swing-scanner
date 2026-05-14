# ════════════════════════════════════════════════════════════════
#  EARLY RALLY — Separate Message Format
# ════════════════════════════════════════════════════════════════

def build_early_rally_message(date_str: str, results: list[dict]) -> str:
    """Separate clean message for VCP / Early Rally setups."""
    if not results:
        return None  # Don't send if nothing found

    parts = [
        f"🚀 *Early Rally Watch — {date_str}*",
        f"_Volume explosion after quiet base — catch it early_",
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


def send_early_rally_alerts(bot_token: str, chat_ids: list,
                             date_str: str, results: list[dict]) -> None:
    """Send early rally as a SEPARATE message to all recipients."""
    if not results:
        return  # Silence if no setups — don't send empty message

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
