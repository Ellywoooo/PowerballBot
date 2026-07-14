"""
Orchestrator for PowerballBot.

Modes:
- predict: score → generate lines → save predictions/latest.csv → Slack
- results: crawl → compare predictions → archive history → Slack
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
from scorer import (
    save_predictions,
    compare_prediction_to_actual,
    archive_predictions,
)


def run_predict():
    df = load_draws()
    main_score = compute_main_scores(df)
    powerball_score = compute_powerball_scores(df)
    lines = generate_lines(main_score, powerball_score)
    save_predictions(lines)
    notify(lines)


def run_results():
    row = crawler.crawl()
    comparison = compare_prediction_to_actual(row)
    if comparison is not None:
        archive_predictions(row, comparison)
    notify_results(row, comparison)


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
