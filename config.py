# ============================================================
#  SWING SCANNER - CONFIGURATION
#
#  For GitHub Actions: credentials are read from GitHub Secrets
#  For local/PythonAnywhere: fill in values directly below
# ============================================================

import os

# --- Telegram Alert Settings ---
# GitHub Actions reads these from Secrets automatically.
# For local use: replace the fallback strings with your real values.
TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "PASTE_YOUR_BOT_TOKEN_HERE"         # ← replace for local use
)
TELEGRAM_CHAT_ID = os.environ.get(
    "TELEGRAM_CHAT_ID",
    "PASTE_YOUR_CHAT_ID_HERE"           # ← replace for local use
)

# --- Scan Schedule (used by scheduler.py on local PC only) ---
SCAN_HOUR   = 16    # 4 PM IST
SCAN_MINUTE = 15

# --- Universe ---
# Options: "nifty50", "nifty200", "nifty500", "custom"
UNIVERSE      = "nifty500"
CUSTOM_STOCKS = []

# --- Strategy Parameters ---

# Support & Resistance
SR_SWING_WINDOW    = 5
SR_ZONE_THRESHOLD  = 0.02
SR_MIN_TOUCHES     = 3
SR_PROXIMITY       = 0.02

# SMC
SMC_SWING_WINDOW   = 5

# Breakout
BREAKOUT_LOOKBACK      = 30
BREAKOUT_MAX_RANGE     = 0.18
BREAKOUT_VOLUME_MULT   = 1.5

# --- Data ---
LOOKBACK_DAYS = 365
