"""
scanner.py — Main scan engine with multi-format alerts
"""

import logging
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from zoneinfo import ZoneInfo

from stock_universe import get_universe
from strategies import run_all_strategies
from alerts import send_scan_results_multi, send_early_rally_alerts
from early_rally import run_early_rally_scan
from data_fetcher import fetch_ohlcv, passes_liquidity_filter
from market_calendar import assert_market_open
import config as cfg

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


def _build_cfg():
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


def scan_stock(symbol, strategy_cfg):
    df = fetch_ohlcv(symbol, cfg.LOOKBACK_DAYS)
    if df is None:
        return None
    liq_ok, liq_reason = passes_liquidity_filter(df, symbol)
    if not liq_ok:
        logger.debug(f"{symbol} skipped: {liq_reason}")
        return None

    signals       = run_all_strategies(df, strategy_cfg)
    early_signals = run_early_rally_scan(df)

    # Calculate 20-day base low for beginner SL calculation
    base_low_20 = float(df["Low"].iloc[-21:-1].min()) if len(df) >= 21 else None

    if signals or early_signals:
        return {
            "symbol":        symbol,
            "signals":       signals,
            "early_signals": early_signals,
            "base_low_20":   base_low_20,
        }
    return None


def run_scan(send_alert=True, force=False):
    now      = datetime.now(IST)
    date_str = now.strftime("%d %b %Y")
    logger.info(f"══ Swing Scanner starting — {date_str} ══")

    if not force:
        if not assert_market_open():
            logger.info("Scan aborted — market not open today.")
            if send_alert:
                send_scan_results_multi(cfg.TELEGRAM_BOT_TOKEN, cfg, date_str, [],
                                 skip_message="🗓 No scan today — NSE holiday or weekend.")
            return []

    symbols = get_universe(cfg.UNIVERSE, getattr(cfg, "CUSTOM_STOCKS", []))
    logger.info(f"Universe: {len(symbols)} stocks")

    strategy_cfg = _build_cfg()
    results, completed, failed = [], 0, 0

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(scan_stock, sym, strategy_cfg): sym for sym in symbols}
        for future in as_completed(futures):
            completed += 1
            if completed % 50 == 0:
                logger.info(f"  Scanned {completed}/{len(symbols)}...")
            try:
                r = future.result()
                if r:
                    results.append(r)
            except Exception as e:
                failed += 1
                logger.debug(f"Future error: {e}")

    logger.info(f"Scan complete — {len(results)} hits | {failed} failed")

    # Separate regular and early rally
    early_results   = [
        {"symbol": r["symbol"], "signals": r["early_signals"]}
        for r in results if r.get("early_signals")
    ]
    regular_results = [
        {"symbol": r["symbol"], "signals": r["signals"], "base_low_20": r.get("base_low_20")}
        for r in results if r.get("signals")
    ]

    if regular_results:
        logger.info("\n📋 SIGNALS:")
        for r in regular_results:
            sym   = r["symbol"].replace(".NS", "")
            types = [s.get("type", "") for s in r["signals"]]
            logger.info(f"  {sym:20s} → {', '.join(types)}")
    else:
        logger.info("No setups found today.")

    if early_results:
        logger.info(f"\n🚀 EARLY RALLY: {len(early_results)} stocks")
        for r in early_results:
            logger.info(f"  {r['symbol'].replace('.NS','')}")

    if send_alert:
        logger.info("Sending alerts...")
        send_scan_results_multi(cfg.TELEGRAM_BOT_TOKEN, cfg, date_str, regular_results)
        if early_results:
            all_ids = [
                cfg.TELEGRAM_CHAT_PERSONAL,
                cfg.TELEGRAM_CHAT_INTERMEDIATE,
                cfg.TELEGRAM_CHAT_BEGINNER,
            ]
            send_early_rally_alerts(cfg.TELEGRAM_BOT_TOKEN, all_ids, date_str, early_results)

    return results


if __name__ == "__main__":
    no_alert = "--no-alert" in sys.argv
    force    = "--force"    in sys.argv
    run_scan(send_alert=not no_alert, force=force)
