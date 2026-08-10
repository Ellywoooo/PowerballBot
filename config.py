from datetime import date


# --- Paths ---
DATA_PATH = "data/draws_clean.csv"
PREDICTIONS_LATEST_PATH = "predictions/latest.csv"
PREDICTIONS_HISTORY_PATH = "predictions/history.csv"

# --- Columns ---
MAIN_COLUMNS = [
    "main_1", "main_2", "main_3", "main_4", "main_5", "main_6", "bonus"
]

# --- Scoring weights (must sum to 1.0) ---
WEIGHT_FREQ = 0.40
WEIGHT_RECENCY = 0.35
WEIGHT_GAP = 0.25

# --- Analysis ---
RECENT_DRAWS = 52
POWERBALL_RULE_CHANGE_DATE = date(2026, 9, 13)
POWERBALL_MIN = 1


def get_powerball_max(today=None):
    today = today or date.today()
    return 14 if today >= POWERBALL_RULE_CHANGE_DATE else 10

# --- Line generation ---
NUM_LINES = 8
MAX_SHARED = 2
CANDIDATE_POOL_SIZE = 18
SAMPLE_POOL_SIZE = 100  # top-score combos to weighted-sample from
SAMPLING_TEMPERATURE = 1.5  # 1.0 = no change; higher = flatter distribution
RECENCY_PENALTY_LOOKBACK = 4
RECENCY_PENALTY_STRENGTH = 0.25  # 0 = no penalty, 1 = max penalty

# --- Crawler ---
# API URL for Lotto NZ results
CRAWLER_URL = "https://pathway.mylotto.co.nz/api/results/v1/results/lotto"
HOMEPAGE_URL = "https://mylotto.co.nz"
# CMS homepage content (includes Powerball jackpot banner alt text)
CONTENT_HOME_URL = "https://pathway.mylotto.co.nz/api/content/pages/home"
USER_AGENT = "PowerballBot/1.0 (learning project; github.com/Ellywoooo/PowerballBot)"
REQUEST_DELAY_MIN = 1.5
REQUEST_DELAY_MAX = 3.0
CACHE_DIR = "cache"