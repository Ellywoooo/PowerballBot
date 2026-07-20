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
from notifier import notify, notify_results, notify_error
from scorer import (
    save_predictions,
    compare_prediction_to_actual,
    archive_predictions,
)


def run_predict():
    mode = "predict"

    try:
        df = load_draws()
        main_score = compute_main_scores(df)
        powerball_score = compute_powerball_scores(df)
        lines = generate_lines(main_score, powerball_score)
    except Exception as exc:
        notify_error("predictor", str(exc), mode)
        raise

    try:
        save_predictions(lines)
    except Exception as exc:
        notify_error("scorer", str(exc), mode)
        raise

    # Never raises — returns None if scrape fails; omit jackpot line then.
    jackpot_amount = crawler.fetch_jackpot_from_homepage()

    try:
        notify(lines, jackpot_amount=jackpot_amount)
    except Exception as exc:
        notify_error("notifier", str(exc), mode)
        raise


def run_results():
    mode = "results"

    try:
        row, dividends = crawler.crawl()
    except Exception as exc:
        notify_error("crawler", str(exc), mode)
        raise

    try:
        comparison = compare_prediction_to_actual(row, dividends=dividends)
        if comparison is not None:
            archive_predictions(row, comparison)
    except Exception as exc:
        notify_error("scorer", str(exc), mode)
        raise

    try:
        notify_results(row, comparison, dividends)
    except Exception as exc:
        notify_error("notifier", str(exc), mode)
        raise


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
