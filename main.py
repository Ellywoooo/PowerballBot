"""
This is the main file for the Powerball Lottery Predictor.
It will:
- Crawl the latest draw
- Load the draws from the CSV file
- Compute the main scores
- Compute the powerball scores
- Generate the lines
- Notify the user
"""

import crawler
from predictor import (
    load_draws,
    compute_main_scores,
    compute_powerball_scores,
    generate_lines,
)
from notifier import notify

def main():
    crawler.crawl() # Crawl the latest draw

    df = load_draws() # Load the draws from the CSV file
    main_score = compute_main_scores(df)
    powerball_score = compute_powerball_scores(df)
    lines = generate_lines(main_score, powerball_score)

    notify(lines)

if __name__ == "__main__":
    main()