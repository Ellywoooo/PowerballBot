"""Tests for prediction vs actual comparison."""

from pathlib import Path

import pandas as pd

from notifier import format_result_message
from scorer import (
    save_predictions,
    compare_prediction_to_actual,
    archive_predictions,
)


def _fake_lines_df():
    return pd.DataFrame(
        [
            {
                "line_no": 1,
                "line": "10 12 13 22 24 25",
                "powerball": 1,
                "score": 3.5,
            },
            {
                "line_no": 2,
                "line": "13 17 19 22 23 40",
                "powerball": 7,
                "score": 3.2,
            },
            {
                "line_no": 3,
                "line": "10 17 19 24 32 38",
                "powerball": 3,
                "score": 3.0,
            },
        ]
    )


def _actual_row():
    return {
        "Draw": 2602,
        "Date": "2026-07-11",
        "Winning Number 1": 10,
        "2": 21,
        "3": 22,
        "4": 26,
        "5": 37,
        "6": 40,
        "Bonus Number": 15,
        "Powerball": 7,
    }


def test_save_and_compare(tmp_path):
    latest = tmp_path / "latest.csv"
    lines = _fake_lines_df()
    save_predictions(lines, path=latest)

    saved = pd.read_csv(latest)
    assert list(saved.columns) == [
        "Line",
        "Number 1",
        "Number 2",
        "Number 3",
        "Number 4",
        "Number 5",
        "Number 6",
        "Powerball",
        "Score",
        "Draw",
        "Predicted At",
    ]
    assert pd.isna(saved.loc[0, "Draw"])

    comparison = compare_prediction_to_actual(_actual_row(), path=latest)
    assert comparison == [
        {"line": 1, "main_matches": 2, "powerball_match": False},  # 10, 22
        {"line": 2, "main_matches": 2, "powerball_match": True},   # 22, 40 + PB
        {"line": 3, "main_matches": 1, "powerball_match": False},  # 10
    ]


def test_compare_returns_none_when_missing(tmp_path):
    missing = tmp_path / "does_not_exist.csv"
    assert compare_prediction_to_actual(_actual_row(), path=missing) is None


def test_archive_predictions(tmp_path, monkeypatch):
    latest = tmp_path / "latest.csv"
    history = tmp_path / "history.csv"
    monkeypatch.setattr("scorer.config.PREDICTIONS_HISTORY_PATH", str(history))

    save_predictions(_fake_lines_df(), path=latest)
    comparison = compare_prediction_to_actual(_actual_row(), path=latest)
    archive_predictions(_actual_row(), comparison, path=latest)

    updated = pd.read_csv(latest)
    assert int(updated.loc[0, "Draw"]) == 2602

    hist = pd.read_csv(history)
    assert len(hist) == 3
    assert int(hist.loc[1, "Main Matches"]) == 2
    assert bool(hist.loc[1, "Powerball Match"]) is True


def test_format_result_message_includes_best_line():
    comparison = [
        {"line": 1, "main_matches": 2, "powerball_match": False},
        {"line": 2, "main_matches": 2, "powerball_match": True},
        {"line": 3, "main_matches": 1, "powerball_match": False},
    ]
    message = format_result_message(_actual_row(), comparison)
    assert "Today's Result:" in message
    assert "2. 2 numbers matched + Powerball!" in message
    assert "Best line: #2 with 2 matches + PB" in message
