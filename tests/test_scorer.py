"""Tests for prediction vs actual comparison."""

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


def _single_line_df(line="10 21 22 30 31 32", powerball=1, score=2.5):
    return pd.DataFrame(
        [
            {
                "line_no": 1,
                "line": line,
                "powerball": powerball,
                "score": score,
            }
        ]
    )


def _actual_row(
    draw=2602,
    n1=10,
    n2=21,
    n3=22,
    n4=26,
    n5=37,
    n6=40,
    bonus=15,
    powerball=7,
):
    return {
        "Draw": draw,
        "Date": "2026-07-11",
        "Winning Number 1": n1,
        "2": n2,
        "3": n3,
        "4": n4,
        "5": n5,
        "6": n6,
        "Bonus Number": bonus,
        "Powerball": powerball,
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


def test_compare_returns_none_when_no_predictions_file(tmp_path):
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


def test_archive_predictions_creates_header_on_first_write(tmp_path, monkeypatch):
    latest = tmp_path / "latest.csv"
    history = tmp_path / "history.csv"
    monkeypatch.setattr("scorer.config.PREDICTIONS_HISTORY_PATH", str(history))

    assert not history.exists()

    save_predictions(_single_line_df(), path=latest)
    actual = _actual_row()
    comparison = compare_prediction_to_actual(actual, path=latest)
    archive_predictions(actual, comparison, path=latest)

    raw = history.read_text(encoding="utf-8").strip().splitlines()
    assert len(raw) == 2  # header + one data row
    assert raw[0].startswith("Draw,Line,Number 1")

    hist = pd.read_csv(history)
    assert len(hist) == 1
    assert int(hist.loc[0, "Draw"]) == 2602


def test_archive_predictions_appends_without_duplicate_header(tmp_path, monkeypatch):
    latest = tmp_path / "latest.csv"
    history = tmp_path / "history.csv"
    monkeypatch.setattr("scorer.config.PREDICTIONS_HISTORY_PATH", str(history))

    save_predictions(_single_line_df(line="10 21 22 30 31 32"), path=latest)
    first = _actual_row(draw=2602)
    comparison = compare_prediction_to_actual(first, path=latest)
    archive_predictions(first, comparison, path=latest)

    save_predictions(_single_line_df(line="01 02 03 04 05 06"), path=latest)
    second = _actual_row(draw=2603, n1=1, n2=2, n3=3, n4=4, n5=5, n6=6)
    comparison = compare_prediction_to_actual(second, path=latest)
    archive_predictions(second, comparison, path=latest)

    raw = history.read_text(encoding="utf-8").strip().splitlines()
    header_count = sum(1 for line in raw if line.startswith("Draw,Line,"))
    assert header_count == 1
    assert len(raw) == 3  # header + two data rows

    hist = pd.read_csv(history)
    assert len(hist) == 2
    assert list(hist["Draw"].astype(int)) == [2602, 2603]


def test_main_matches_count_is_accurate(tmp_path):
    latest = tmp_path / "latest.csv"
    # Predicted: 10 21 22 30 31 32 — shares 10, 21, 22 with actual (3 matches)
    save_predictions(
        _single_line_df(line="10 21 22 30 31 32", powerball=9),
        path=latest,
    )
    comparison = compare_prediction_to_actual(_actual_row(), path=latest)

    assert comparison is not None
    assert len(comparison) == 1
    assert comparison[0]["main_matches"] == 3
    assert comparison[0]["powerball_match"] is False


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
