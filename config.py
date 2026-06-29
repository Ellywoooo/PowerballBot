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