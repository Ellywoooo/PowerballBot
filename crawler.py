"""

"""
import random
import re
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
    """Convert API JSON to CSV row + dividend winner data."""
    lotto = data["lotto"]
    powerball = data["powerBall"]

    numbers = [int(n) for n in lotto["lottoWinningNumbers"]["numbers"]]
    bonus = int(lotto["lottoWinningNumbers"]["bonusBalls"])

    row = {
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

    dividends = {
        "lottoWinners": lotto.get("lottoWinners", []),
        "powerballWinners": powerball.get("powerballWinners", []),
    }

    return row, dividends

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
    """Fetch latest draw, save to CSV if new. Returns (row, dividends)."""
    data = fetch_latest_draw()
    row, dividends = parse_draw(data)

    if append_if_new(row):
        print(f"Added draw {row['Draw']} ({row['Date']})")
    else:
        print(f"Draw {row['Draw']} already in CSV — no update needed")

    return row, dividends


def fetch_jackpot_from_homepage():
    """
    Fetch the advertised Powerball jackpot from the CMS home content API
    (same alt text shown on the homepage banner image).

    Returns integer dollars (e.g. 35_000_000) or None.
    Never raises — network/parse failures degrade gracefully.
    """
    try:
        time.sleep(random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX))

        headers = {
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json",
            "Origin": "https://mylotto.co.nz",
            "Referer": "https://mylotto.co.nz/",
            "LNZ-Request-ID": f"{uuid.uuid4()}.web",
        }

        response = requests.get(config.CONTENT_HOME_URL, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Jackpot fetch failed: HTTP {response.status_code}")
            return None

        data = response.json()
        alt_texts = []

        def _collect_alt_texts(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in {"alt_text", "alt", "ga_creative_name"} and isinstance(value, str):
                        alt_texts.append(value)
                    else:
                        _collect_alt_texts(value)
            elif isinstance(obj, list):
                for item in obj:
                    _collect_alt_texts(item)

        _collect_alt_texts(data)

        jackpot_text = None
        for text in alt_texts:
            lower = text.lower()
            if "jackpot" in lower and "powerball" in lower:
                jackpot_text = text
                break

        if jackpot_text is None:
            print("Jackpot fetch failed: no Powerball jackpot alt text in CMS response")
            return None

        match = re.search(r"\$(\d+(?:\.\d+)?)\s*million", jackpot_text, re.IGNORECASE)
        if not match:
            print(f"Jackpot fetch failed: no $N million pattern in: {jackpot_text!r}")
            return None

        millions = float(match.group(1))
        return int(millions * 1_000_000)
    except Exception as exc:
        print(f"Jackpot fetch failed with unexpected error: {exc}")
        return None


if __name__ == "__main__":
    crawl()
