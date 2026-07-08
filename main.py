"""
Orchestrator for PowerballBot.

Modes:
- predict: crawl → score → generate lines → Slack
- results: fetch latest draw → Slack (winning numbers)
"""

import argparse
import crawler
from predictor import (
    load_draws,
    compute_main_scores,
    compute_powerball_scores,
    generate_lines,
)
from notifier import notify, notify_results


def run_predict():
    crawler.crawl()

    df = load_draws()
    main_score = compute_main_scores(df)
    powerball_score = compute_powerball_scores(df)
    lines = generate_lines(main_score, powerball_score)
    notify(lines)


def run_results():
    data = crawler.fetch_latest_draw()
    row = crawler.parse_draw(data)
    notify_results(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["predict", "results"],
        default="predict",
        help="What to send to Slack",
    )
    args = parser.parse_args()

    if args.mode == "results":
        run_results()
    else:
        run_predict()


if __name__ == "__main__":
    main()