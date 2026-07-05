"""

"""
import random
import time
import uuid

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

    if response.status_code in (429, 503):
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

if __name__ == "__main__":
    data = fetch_latest_draw()
    print(data)