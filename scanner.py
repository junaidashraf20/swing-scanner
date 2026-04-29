"""
scanner.py — Main scan engine (production grade)
─────────────────────────────────────────────────
Critical fixes applied:
  ✅ FIX 1 — yfinance fallback to jugaad_data (via data_fetcher.py)
  ✅ FIX 2 — NSE holiday + weekend check (via market_calendar.py)
  ✅ FIX 3 — Data validation before running strategies (via data_fetcher.py)
"""

import logging
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

from stock_universe import get_universe
from strategies import run_all_strategies
from alerts import send_scan_results
from data_fetcher import fetch_ohlcv, passes_liquidity_filter
from market_calendar import assert_market_open
import config as cfg

# ── Logging ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("scanner.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


def _build_cfg() -> dict:
    return {
        "SR_SWING_WINDOW":      cfg.SR_SWING_WINDOW,
        "SR_ZONE_THRESHOLD":    cfg.SR_ZONE_THRESHOLD,
        "SR_MIN_TOUCHES":       cfg.SR_MIN_TOUCHES,
        "SR_PROXIMITY":         cfg.SR_PROXIMITY,
        "SMC_SWING_WINDOW":     cfg.SMC_SWING_WINDOW,
        "BREAKOUT_LOOKBACK":    cfg.BREAKOUT_LOOKBACK,
        "BREAKOUT_MAX_RANGE":   cfg.BREAKOUT_MAX_RANGE,
        "BREAKOUT_VOLUME_MULT": cfg.BREAKOUT_VOLUME_MULT,
    }


def scan_stock(symbol: str, strategy_cfg: dict) -> dict | None:
    """Fetch + validate + liquidity check + scan one stock."""
    df = fetch_ohlcv(symbol, cfg.LOOKBACK_DAYS)
    if df is None:
        return None
    # Liquidity + market cap proxy filter
    liq_ok, liq_reason = passes_liquidity_filter(df, symbol)
    if not liq_ok:
        logger.debug(f"{symbol} skipped: {liq_reason}")
        return None
    signals = run_all_strategies(df, strategy_cfg)
    if signals:
        return {"symbol": symbol, "signals": signals}
    return None


def run_scan(send_alert: bool = True, force: bool = False) -> list[dict]:
    """
    Full scan pipeline.
    force=True bypasses the holiday check (for manual testing).
    """
    now  = datetime.now(IST)
    date_str = now.strftime("%d %b %Y")

    logger.info(f"══ Swing Scanner starting — {date_str} ══")

    # ── FIX 2: Market holiday / weekend check ─────────────────
    if not force:
        if not assert_market_open():
            logger.info("Scan aborted — market was not open today.")
            if send_alert:
                send_scan_results(
                    cfg.TELEGRAM_BOT_TOKEN,
                    cfg.TELEGRAM_CHAT_ID,
                    date_str,
                    [],
                    skip_message="🗓 No scan today — NSE holiday or weekend.",
                )
            return []

    # ── Fetch stock universe ───────────────────────────────────
    symbols = get_universe(cfg.UNIVERSE, getattr(cfg, "CUSTOM_STOCKS", []))
    logger.info(f"Universe: {len(symbols)} stocks")

    # ── Scan in parallel ───────────────────────────────────────
    strategy_cfg = _build_cfg()
    results      = []
    completed    = 0
    failed       = 0

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(scan_stock, sym, strategy_cfg): sym for sym in symbols}
        for future in as_completed(futures):
            completed += 1
            if completed % 50 == 0:
                logger.info(f"  Scanned {completed}/{len(symbols)} stocks...")
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                failed += 1
                logger.debug(f"Future error: {e}")

    logger.info(f"Scan complete — {len(results)} signals | {failed} fetch failures | {len(symbols)-completed} skipped")

    # ── Console summary ────────────────────────────────────────
    if results:
        logger.info("\n📋 SIGNALS:")
        for r in results:
            sym    = r["symbol"].replace(".NS", "")
            strats = list({s["strategy"] for s in r["signals"]})
            types  = [s.get("type", "") for s in r["signals"]]
            logger.info(f"  {sym:20s} → {', '.join(types)}")
    else:
        logger.info("No setups found today.")

    # ── Send Telegram alert ────────────────────────────────────
    if send_alert:
        logger.info("Sending Telegram alert...")
        send_scan_results(cfg.TELEGRAM_BOT_TOKEN, cfg.TELEGRAM_CHAT_ID, date_str, results)

    return results


if __name__ == "__main__":
    no_alert = "--no-alert" in sys.argv
    force    = "--force"    in sys.argv   # bypass holiday check for testing
    run_scan(send_alert=not no_alert, force=force)
