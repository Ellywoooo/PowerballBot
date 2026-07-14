# --- Paths ---
DATA_PATH = "data/draws_clean.csv"

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

# --- Line generation ---
NUM_LINES = 8
MAX_SHARED = 2
CANDIDATE_POOL_SIZE = 18
SAMPLE_POOL_SIZE = 100  # top-score combos to weighted-sample from

# --- Crawler ---
# API URL for Lotto NZ results
CRAWLER_URL = "https://pathway.mylotto.co.nz/api/results/v1/results/lotto"
USER_AGENT = "PowerballBot/1.0 (learning project; github.com/Ellywoooo/PowerballBot)"
REQUEST_DELAY_MIN = 1.5
REQUEST_DELAY_MAX = 3.0
CACHE_DIR = "cache"