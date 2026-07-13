"""

"""
import random
import time
import uuid
import pandas as pd
import requests
import config


def fetch_latest_draw():
    """GET latest draw JSON from Lotto NZ results API."""
    time.sleep(random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX))

    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept": "application/json",
        "Origin": "https://mylotto.co.nz",
        "Referer": "https://mylotto.co.nz/results",
        "LNZ-Request-ID": f"{uuid.uuid4()}.web",
    }

    response = requests.get(config.CRAWLER_URL, headers=headers, timeout=15)

    if response.status_code in {429, 503}:
        raise RuntimeError(f"Rate limited / server busy: {response.status_code}")
    if response.status_code != 200:
        raise RuntimeError(f"Fetch failed: {response.status_code} {response.text[:200]}")

    return response.json()

def parse_draw(data):
    """Convert API JSON to a row matching draws_clean.csv columns."""
    lotto = data["lotto"]
    powerball = data["powerBall"]

    numbers = [int(n) for n in lotto["lottoWinningNumbers"]["numbers"]]
    bonus = int(lotto["lottoWinningNumbers"]["bonusBalls"])

    return {
        "Draw": lotto["drawNumber"],
        "Date": lotto["drawDate"],
        "Winning Number 1": numbers[0],
        "2": numbers[1],
        "3": numbers[2],
        "4": numbers[3],
        "5": numbers[4],
        "6": numbers[5],
        "Bonus Number": bonus,
        "Powerball": int(powerball["powerballWinningNumber"]),
    }

# Read the data from the CSV file
# Check if the draw number is already in the CSV file
# If it is, return False
# If it is not, append the row to the CSV file and return True
def append_if_new(row, path=config.DATA_PATH):
    """Append row to CSV if draw_number not already stored. Returns True if added."""
    df = pd.read_csv(path)

    if row["Draw"] in df["Draw"].values:
        return False

    new_row = pd.DataFrame([row])
    df = pd.concat([new_row, df], ignore_index=True)
    df.to_csv(path, index=False)
    return True

# Crawl the latest draw
# Fetch the latest draw from the API
# Parse the draw into a row
# Append the row to the CSV file if it is not already in the CSV file
# Print a message if the draw was added or if it was already in the CSV file
def crawl():
    """Fetch latest draw, save to CSV if new. Returns the parsed row."""
    data = fetch_latest_draw()
    row = parse_draw(data)

    if append_if_new(row):
        print(f"Added draw {row['Draw']} ({row['Date']})")
    else:
        print(f"Draw {row['Draw']} already in CSV — no update needed")

    return row

if __name__ == "__main__":
    crawl()
