"""
scheduler.py
────────────
Runs the swing scanner automatically every weekday at 4:15 PM IST.
Keep this script running in the background (or use cron — see README).

Usage:
    python scheduler.py
"""

import schedule
import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from scanner import run_scan
import config as cfg

logger = logging.getLogger(__name__)
IST    = ZoneInfo("Asia/Kolkata")

SCAN_TIME = f"{cfg.SCAN_HOUR:02d}:{cfg.SCAN_MINUTE:02d}"


def job():
    now = datetime.now(IST)
    # Skip weekends (Saturday=5, Sunday=6)
    if now.weekday() >= 5:
        logger.info(f"Weekend — skipping scan ({now.strftime('%A')})")
        return
    logger.info(f"⏰ Scheduled scan triggered at {now.strftime('%H:%M IST')}")
    run_scan(send_alert=True)


# Schedule in IST — machine must have IST timezone or use TZ=Asia/Kolkata
schedule.every().day.at(SCAN_TIME).do(job)

logger.info(f"Scheduler started. Scan runs every weekday at {SCAN_TIME} IST.")
logger.info("Press Ctrl+C to stop.\n")

while True:
    schedule.run_pending()
    time.sleep(30)
