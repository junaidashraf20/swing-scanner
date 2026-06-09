# ============================================================
#  SWING SCANNER - CONFIGURATION
# ============================================================

import os

# --- Telegram Bot ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "PASTE_YOUR_BOT_TOKEN_HERE")

# --- Chat IDs (descriptive names so you always know which is which) ---
# Each gets a DIFFERENT message format automatically:
#   Personal     → full technical detail (for you)
#   Intermediate → medium detail + SL zone
#   Beginner     → simple: Buy above X, SL Y, Target Z

TELEGRAM_CHATS = {
    "personal":     os.environ.get("TELEGRAM_CHAT_PERSONAL",     ""),
    "intermediate": os.environ.get("TELEGRAM_CHAT_INTERMEDIATE", ""),
    "beginner":     os.environ.get("TELEGRAM_CHAT_BEGINNER",     ""),
}

# --- Scan Schedule ---
SCAN_HOUR   = 18
SCAN_MINUTE = 0

# --- Universe ---
UNIVERSE      = "nifty500"
CUSTOM_STOCKS = []

# --- Strategy Parameters ---
SR_SWING_WINDOW      = 5
SR_ZONE_THRESHOLD    = 0.025
SR_MIN_TOUCHES       = 2
SR_PROXIMITY         = 0.02
SMC_SWING_WINDOW     = 5
BREAKOUT_LOOKBACK    = 30
BREAKOUT_MAX_RANGE   = 0.15
BREAKOUT_VOLUME_MULT = 1.2

# --- Order Block Strategy Parameters ---
ORDER_BLOCK_IMPULSE_LOOKBACK    = 30   # How many bars back to scan for bullish impulse
ORDER_BLOCK_CONSOLIDATION_MIN   = 3    # Minimum bars in consolidation zone
ORDER_BLOCK_CONSOLIDATION_MAX   = 10   # Maximum bars in consolidation zone
ORDER_BLOCK_VOLUME_MULT         = 1.2  # Volume multiplier for breakout confirmation

# --- Data ---
LOOKBACK_DAYS = 365
