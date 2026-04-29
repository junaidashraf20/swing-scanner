# ============================================================
#  SWING SCANNER - CONFIGURATION
# ============================================================

import os

# --- Telegram Alert Settings ---
# Add ALL your chat IDs / group IDs here
# Personal chat ID: just numbers e.g. "987654321"
# Group chat ID: starts with -100 e.g. "-1001234567890"

TELEGRAM_BOT_TOKEN = os.environ.get(
    "TELEGRAM_BOT_TOKEN",
    "PASTE_YOUR_BOT_TOKEN_HERE"
)

# Add multiple recipients here — personal + groups
TELEGRAM_CHAT_IDS = [
    os.environ.get("TELEGRAM_CHAT_ID_1", "YOUR_PERSONAL_CHAT_ID"),
    os.environ.get("TELEGRAM_CHAT_ID_2", "YOUR_GROUP_1_ID"),
    os.environ.get("TELEGRAM_CHAT_ID_3", "YOUR_GROUP_2_ID"),
    # Add more as needed
]

# --- Scan Schedule ---
SCAN_HOUR   = 16
SCAN_MINUTE = 15

# --- Universe ---
UNIVERSE      = "nifty500"
CUSTOM_STOCKS = []

# --- Strategy Parameters ---
SR_SWING_WINDOW    = 5
SR_ZONE_THRESHOLD  = 0.025
SR_MIN_TOUCHES     = 2
SR_PROXIMITY       = 0.02
SMC_SWING_WINDOW   = 5
BREAKOUT_LOOKBACK  = 30
BREAKOUT_MAX_RANGE = 0.15
BREAKOUT_VOLUME_MULT = 1.5

# --- Data ---
LOOKBACK_DAYS = 365
