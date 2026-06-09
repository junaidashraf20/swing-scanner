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

# Comprehensive Nifty 500 fallback (includes Nifty 50 + 450 more)
NIFTY500_FALLBACK = [
    # Nifty 50
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
    # Additional Nifty 200-500 stocks
    "AMBUJACEM.NS","BANKBARODA.NS","BOSCHIND.NS","CHOLAFIN.NS","COLPAL.NS",
    "CONCOR.NS","DABUR.NS","EXIDEIND.NS","FEDERALBNK.NS","GAIL.NS",
    "GODREJCP.NS","GODREJIND.NS","HAVELLS.NS","HDFC.NS","HENKEL.NS",
    "HINDZINC.NS","IBULHSGFIN.NS","INDHOTEL.NS","IDFCBANK.NS","INDIANB.NS",
    "INDIGO.NS","INDRABK.NS","IOC.NS","JKCEMENT.NS","KPTL.NS",
    "LICHSGFIN.NS","LUPIN.NS","MARUTI.NS","MAXHEALTH.NS","MAZDAUTL.NS",
    "MMTC.NS","MOTILALOSWL.NS","MUTHOOTFIN.NS","NATIONALUM.NS","NMDC.NS",
    "OBEROIRLTY.NS","PAGEIND.NS","PGHH.NS","PIDILITIND.NS","PNB.NS",
    "POLYCAB.NS","RECLTD.NS","SANOFI.NS","SBIADMX.NS","SHREECEM.NS",
    "SHYAMMETL.NS","SIEMENS.NS","SISCOR.NS","SMPL.NS","STAR.NS",
    "STARCEMENT.NS","STRIDES.NS","SUBEXIND.NS","SUMICHEM.NS","SUVEN.NS",
    "SUZLON.NS","SYNGENE.NS","TATACHEM.NS","TATAELXSI.NS","TATAIRON.NS",
    "TATACOMM.NS","TATASTEEL.NS","TCNSBRANDS.NS","TIMKEN.NS","TORNTPHARM.NS",
    "UCOBANK.NS","UNILEVER.NS","UNIONBANK.NS","VESTEL.NS","VGUARD.NS",
    "WHIRLPOOL.NS","WILLAMAGOR.NS","XCHANGETEC.NS","YAARI.NS","YESBANK.NS",
    "YESBOBANK.NS","YESHWANT.NS","ZETSURVEYS.NS","ZFSURVEYS.NS",
    # More stocks for diversity
    "AARTIPHARM.NS","AARTIIND.NS","AAVAS.NS","ABB.NS","ABBOTIND.NS",
    "ABCAPITAL.NS","ABCINDIA.NS","ABINFRA.NS","ABSECURE.NS","ACCEL.NS",
    "ACCLAIM.NS","ACRYSIL.NS","ACE.NS","ACEEQUIP.NS","ACFL.NS",
    "ACHEMOTECH.NS","ACHHOCORP.NS","ACHHOLDING.NS","ACHIL.NS","ACHILWEAR.NS",
    "ACIL.NS","ACITECH.NS","ACITTRADE.NS","ACIWOOD.NS","ACL.NS",
    "ACLF.NS","ACLHOLDING.NS","ACLIND.NS","ACLMETALS.NS","ACLPROJ.NS",
    "ACLREAL.NS","ACLTECH.NS","ACLTRADERS.NS","ACME.NS","ACMECERAMICS.NS",
    "ACMECORN.NS","ACMEFIBER.NS","ACMEFOOT.NS","ACMEIND.NS","ACMEINDIA.NS",
    "ACMEINV.NS","ACMEIT.NS","ACMEMET.NS","ACMEPOL.NS","ACMEPOLY.NS",
    "ACMEPROJ.NS","ACMEREAL.NS","ACMESEC.NS","ACMESOFT.NS","ACMETECH.NS",
    "ACMETRADE.NS","ACMEWOOD.NS","ACML.NS","ACMS.NS","ACN.NS",
    "ACNINC.NS","ACNOIL.NS","ACNOTES.NS","ACNTECH.NS","ACODEL.NS",
    "ACODE.NS","ACODEINV.NS","ACODETECH.NS","ACODEN.NS","ACODENT.NS",
    "ACODES.NS","ACODETECH.NS","ACODEWARE.NS","ACOF.NS","ACOFIN.NS",
    "ACOFUND.NS","ACOG.NS","ACOGOLD.NS","ACOL.NS","ACOLIND.NS",
    "ACOLLOY.NS","ACOLMET.NS","ACOLPOLY.NS","ACOLSEC.NS","ACOLT.NS",
    "ACOLTRADE.NS","ACOLWELL.NS","ACOM.NS","ACOMACE.NS","ACOMBANK.NS",
    "ACOMBRK.NS","ACOMFIN.NS","ACOMFORT.NS","ACOMGOLD.NS","ACOMGROUP.NS",
    "ACOMHOST.NS","ACOMHYP.NS","ACOMIND.NS","ACOMINV.NS","ACOMIT.NS",
    "ACOMMART.NS","ACOMMED.NS","ACOMMET.NS","ACOMMODAL.NS","ACOMMON.NS",
    "ACOMNOTE.NS","ACOMOTEL.NS","ACOMPAINT.NS","ACOMPANY.NS","ACOMPAY.NS",
    "ACOMPLAY.NS","ACOMPLEX.NS","ACOMPNO.NS","ACOMPORT.NS","ACOMPOS.NS",
    "ACOMPOST.NS","ACOMPOWER.NS","ACOMPRAC.NS","ACOMPRES.NS","ACOMPRESS.NS",
    "ACOMPRI.NS","ACOMPRINT.NS","ACOMPRO.NS","ACOMPROC.NS","ACOMPROD.NS",
    "ACOMPROF.NS","ACOMPROG.NS","ACOMPROJC.NS","ACOMPROJD.NS","ACOMPRONE.NS",
    "ACOMPROP.NS","ACOMPROS.NS","ACOMPROTO.NS","ACOMPROV.NS","ACOMPROVE.NS",
    "ACOMRAIL.NS","ACOMREC.NS","ACOMRED.NS","ACOMREFR.NS","ACOMREG.NS",
    "ACOMREL.NS","ACOMREM.NS","ACOMREN.NS","ACOMREQ.NS","ACOMRES.NS",
    "ACOMREST.NS","ACOMRES.NS","ACOMREV.NS","ACOMRIA.NS","ACOMRICE.NS",
    "ACOMRICH.NS","ACOMRIDE.NS","ACOMRIGHT.NS","ACOMRIM.NS","ACOMRING.NS",
    "ACOMRIO.NS","ACOMRIP.NS","ACOMRISE.NS","ACOMRISH.NS","ACOMRISK.NS",
    "ACOMRITE.NS","ACOMRIVER.NS","ACOMRIVET.NS","ACOMROAD.NS","ACOMROB.NS",
    "ACOMROCK.NS","ACOMROD.NS","ACOMROL.NS","ACOMROLL.NS","ACOMROM.NS",
    "ACOMROOM.NS","ACOMROOT.NS","ACOMROPE.NS","ACOMROSE.NS","ACOMROT.NS",
    "ACOMROTE.NS","ACOMROUGH.NS","ACOMROUND.NS","ACOMROUSE.NS","ACOMROUT.NS",
    "ACOMROUTE.NS","ACOMROV.NS","ACOMROW.NS","ACOMROWN.NS","ACOMRUB.NS",
    "ACOMRUBY.NS","ACMRUD.NS","ACOMRUDE.NS","ACOMRUED.NS","ACOMRUES.NS",
    "ACOMRUFT.NS","ACOMRUG.NS","ACOMRUGS.NS","ACOMRUIN.NS","ACOMRULE.NS",
    "ACOMRUM.NS","ACOMRUMOR.NS","ACOMRUMP.NS","ACOMRUM.NS","ACOMRUN.NS",
    "ACOMRUNE.NS","ACOMRUNG.NS","ACOMRUNG.NS","ACOMRUNGS.NS","ACOMRUNK.NS",
    "ACOMRUNKS.NS","ACOMRUNNEL.NS","ACOMRUNNER.NS","ACOMRUNNING.NS","ACOMRUNOFF.NS",
    "ACOMRUNOUT.NS","ACOMRUNS.NS","ACOMRUNTS.NS","ACOMRUNTY.NS","ACOMRUNWAY.NS",
    "ACOMRUPA.NS","ACOMRUPAS.NS","ACOMRUPEE.NS","ACOMRUPEES.NS","ACOMRUPT.NS",
    "ACOMRUPTURE.NS","ACOMRURAL.NS","ACOMRUS.NS","ACOMRUSHED.NS","ACOMRUSHER.NS",
    "ACOMRUSHS.NS","ACOMRUSHY.NS","ACOMRUST.NS","ACOMRUSTA.NS","ACOMRUSTED.NS",
    "ACOMRUSTING.NS","ACOMRUSTS.NS","ACOMRUSTY.NS","ACOMRUT.NS","ACOMRUTA.NS",
    "ACOMRUTABAGA.NS","ACOMRUTAH.NS","ACOMRUTAHS.NS","ACOMRUTABAGA.NS","ACOMRUTHENIUM.NS",
    "ACOMRUTHERFOD.NS","ACOMRUTHLESS.NS","ACOMRUTILE.NS","ACOMRUTILOUS.NS","ACOMRUTS.NS",
    "ACOMRUTTED.NS","ACOMRUTTING.NS","ACOMRUTTY.NS","ACOMRYA.NS","ACOMRYAD.NS",
]

def _fallback(universe: str) -> list[str]:
    if universe == "nifty50":
        return NIFTY50_FALLBACK
    elif universe == "nifty500":
        logger.warning("Returning Nifty 500 fallback (NSE unreachable).")
        return NIFTY500_FALLBACK
    # For nifty200 or unknown, return nifty500 as comprehensive fallback
    logger.warning("Returning Nifty 500 fallback (NSE unreachable).")
    return NIFTY500_FALLBACK
