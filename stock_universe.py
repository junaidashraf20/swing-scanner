"""
stock_universe.py — Fetches Nifty 50 / 200 / 500 symbols
Uses NSE India's public API with a browser-like session.
Falls back to a bundled list if NSE is unreachable.
"""

import requests
import time
import logging

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer":         "https://www.nseindia.com/",
    "Connection":      "keep-alive",
}

INDEX_MAP = {
    "nifty50":  "NIFTY%2050",
    "nifty200": "NIFTY%20200",
    "nifty500": "NIFTY%20500",
}


def fetch_from_nse(index_key: str) -> list[str]:
    """Return list of Yahoo Finance tickers (symbol.NS) for the given index."""
    index_param = INDEX_MAP.get(index_key, "NIFTY%20500")
    url = f"https://www.nseindia.com/api/equity-stockIndices?index={index_param}"

    session = requests.Session()
    # Prime the session so NSE sets cookies
    session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=10)
    time.sleep(1)

    resp = session.get(url, headers=NSE_HEADERS, timeout=15)
    resp.raise_for_status()

    data = resp.json().get("data", [])
    symbols = []
    for item in data:
        sym = item.get("symbol", "")
        if sym and sym not in ("NIFTY 50", "NIFTY 200", "NIFTY 500", ""):
            symbols.append(sym + ".NS")

    return symbols


def get_universe(universe: str = "nifty500", custom: list = None) -> list[str]:
    """
    Returns a list of Yahoo Finance ticker strings.
    universe: 'nifty50' | 'nifty200' | 'nifty500' | 'custom'
    """
    if universe == "custom" and custom:
        return [s.upper() + ".NS" if not s.endswith(".NS") else s for s in custom]

    try:
        logger.info(f"Fetching {universe} from NSE India...")
        symbols = fetch_from_nse(universe)
        if symbols:
            logger.info(f"Fetched {len(symbols)} stocks from NSE.")
            return symbols
    except Exception as e:
        logger.warning(f"NSE fetch failed ({e}). Using fallback list.")

    return _fallback(universe)


# ── Fallback lists (top stocks, hardcoded) ───────────────────────────────────

NIFTY50_FALLBACK = [
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","BHARTIARTL.NS","ICICIBANK.NS",
    "INFOSYS.NS","SBILIFE.NS","KOTAKBANK.NS","LT.NS","AXISBANK.NS",
    "HINDUNILVR.NS","ITC.NS","BAJFINANCE.NS","SBIN.NS","MARUTI.NS",
    "SUNPHARMA.NS","TITAN.NS","NTPC.NS","ONGC.NS","WIPRO.NS",
    "NESTLEIND.NS","POWERGRID.NS","ULTRACEMCO.NS","TATAMOTORS.NS","HCLTECH.NS",
    "ADANIENT.NS","ADANIPORTS.NS","COALINDIA.NS","BAJAJFINSV.NS","JSWSTEEL.NS",
    "ASIANPAINT.NS","DRREDDY.NS","INDUSINDBK.NS","TATACONSUM.NS","DIVISLAB.NS",
    "CIPLA.NS","GRASIM.NS","HDFCLIFE.NS","APOLLOHOSP.NS","BAJAJ-AUTO.NS",
    "EICHERMOT.NS","HINDALCO.NS","BRITANNIA.NS","BPCL.NS","TATAPOWER.NS",
    "TECHM.NS","SHRIRAMFIN.NS","M&M.NS","HEROMOTOCO.NS","LTIM.NS",
]

def _fallback(universe: str) -> list[str]:
    if universe == "nifty50":
        return NIFTY50_FALLBACK
    # For nifty200/500 return nifty50 as minimal fallback
    logger.warning("Returning Nifty 50 fallback (NSE unreachable).")
    return NIFTY50_FALLBACK
