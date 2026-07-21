"""Tests for prediction vs actual comparison."""

import pandas as pd
import pytest

from notifier import format_result_message
from scorer import (
    save_predictions,
    compare_prediction_to_actual,
    archive_predictions,
    determine_division,
    parse_prize_value,
    division_one_status,
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


def _fake_dividends():
    return {
        "lottoWinners": [
            {"division": 1, "prizeValue": "1000000.00", "numberOfWinners": 1},
            {"division": 3, "prizeValue": "702.00", "numberOfWinners": 670},
            {"division": 7, "prizeValue": "Bonus Ticket", "numberOfWinners": 399628},
        ],
        "powerballWinners": [
            {"division": 1, "prizeValue": "ROLLOVER", "numberOfWinners": 0},
            {
                "division": 2,
                "prizeValue": "11277.00",
                "numberOfWinners": 3,
                "combinedPrizeValue": "39190.00",
            },
            {
                "division": 7,
                "prizeValue": "15.00",
                "numberOfWinners": 32073,
                "combinedPrizeValue": "Bonus Ticket + 15.00",
            },
        ],
    }


@pytest.mark.parametrize(
    "main_matches, bonus_match, expected",
    [
        (6, False, 1),
        (6, True, 1),
        (5, True, 2),
        (5, False, 3),
        (4, True, 4),
        (4, False, 5),
        (3, True, 6),
        (3, False, 7),
        (2, True, None),
        (0, False, None),
    ],
)
def test_determine_division(main_matches, bonus_match, expected):
    assert determine_division(main_matches, bonus_match) == expected


def test_parse_prize_value():
    assert parse_prize_value("702.00") == 702.0
    assert parse_prize_value("ROLLOVER") is None
    assert parse_prize_value("Bonus Ticket") is None


def test_division_one_status():
    dividends = _fake_dividends()
    status = division_one_status(dividends)
    assert status == {"lotto_won": True, "powerball_won": False}


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
    assert comparison[0] == {
        "line": 1,
        "main_matches": 2,
        "bonus_match": False,
        "powerball_match": False,
        "division": None,
        "prize_amount": None,
        "prize_note": None,
    }
    assert comparison[1]["main_matches"] == 2
    assert comparison[1]["powerball_match"] is True


def test_compare_returns_none_when_no_predictions_file(tmp_path):
    missing = tmp_path / "does_not_exist.csv"
    assert compare_prediction_to_actual(_actual_row(), path=missing) is None


def test_compare_with_dividends_lotto_and_powerball_wins(tmp_path):
    latest = tmp_path / "latest.csv"

    # Line A: 5 mains, no bonus -> division 3, lotto prize $702
    save_predictions(
        _single_line_df(line="10 21 22 26 37 30", powerball=9),
        path=latest,
    )
    lotto_only = compare_prediction_to_actual(
        _actual_row(), path=latest, dividends=_fake_dividends()
    )
    assert lotto_only[0]["division"] == 3
    assert lotto_only[0]["prize_amount"] == 702.0
    assert lotto_only[0]["prize_note"] is None

    # Line B: 3 mains + PB match -> division 7, combined prize from powerballWinners
    save_predictions(
        _single_line_df(line="10 21 22 30 31 32", powerball=7),
        path=latest,
    )
    pb_win = compare_prediction_to_actual(
        _actual_row(), path=latest, dividends=_fake_dividends()
    )
    assert pb_win[0]["division"] == 7
    assert pb_win[0]["prize_amount"] == 15.0
    assert pb_win[0]["prize_note"] is None


def test_compare_bonus_ticket_prize_note(tmp_path):
    latest = tmp_path / "latest.csv"
    # 3 mains, no bonus, no PB -> division 7 lotto only -> Bonus Ticket
    save_predictions(
        _single_line_df(line="10 21 22 30 31 32", powerball=9),
        path=latest,
    )
    comparison = compare_prediction_to_actual(
        _actual_row(), path=latest, dividends=_fake_dividends()
    )
    assert comparison[0]["division"] == 7
    assert comparison[0]["prize_amount"] is None
    assert comparison[0]["prize_note"] == "Bonus Ticket"


def test_archive_predictions_skips_duplicate_draw(tmp_path, monkeypatch):
    latest = tmp_path / "latest.csv"
    history = tmp_path / "history.csv"
    monkeypatch.setattr("scorer.config.PREDICTIONS_HISTORY_PATH", str(history))

    save_predictions(_fake_lines_df(), path=latest)
    actual = _actual_row()
    comparison = compare_prediction_to_actual(actual, path=latest)

    assert archive_predictions(actual, comparison, path=latest) is True
    assert archive_predictions(actual, comparison, path=latest) is False

    hist = pd.read_csv(history)
    assert len(hist) == 3
    assert hist["Draw"].nunique() == 1


def test_archive_predictions_writes_extended_columns(tmp_path, monkeypatch):
    latest = tmp_path / "latest.csv"
    history = tmp_path / "history.csv"
    monkeypatch.setattr("scorer.config.PREDICTIONS_HISTORY_PATH", str(history))

    save_predictions(
        _single_line_df(line="10 21 22 30 31 32", powerball=9, score=4.25),
        path=latest,
    )
    actual = _actual_row()
    comparison = compare_prediction_to_actual(
        actual, path=latest, dividends=_fake_dividends()
    )

    assert archive_predictions(actual, comparison, path=latest) is True

    hist = pd.read_csv(history, keep_default_na=False)
    assert list(hist.columns) == [
        "Draw",
        "Line",
        "Number 1",
        "Number 2",
        "Number 3",
        "Number 4",
        "Number 5",
        "Number 6",
        "Powerball",
        "Score",
        "Main Matches",
        "Bonus Match",
        "Powerball Match",
        "Division",
        "Prize Amount",
        "Prize Note",
        "Predicted At",
    ]
    assert float(hist.loc[0, "Score"]) == 4.25
    assert hist.loc[0, "Bonus Match"] in (False, "False")
    assert int(hist.loc[0, "Division"]) == 7
    assert hist.loc[0, "Prize Amount"] == ""
    assert hist.loc[0, "Prize Note"] == "Bonus Ticket"


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
    assert len(raw) == 2
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
    assert len(raw) == 3

    hist = pd.read_csv(history)
    assert len(hist) == 2
    assert list(hist["Draw"].astype(int)) == [2602, 2603]


def test_main_matches_count_is_accurate(tmp_path):
    latest = tmp_path / "latest.csv"
    save_predictions(
        _single_line_df(line="10 21 22 30 31 32", powerball=9),
        path=latest,
    )
    comparison = compare_prediction_to_actual(_actual_row(), path=latest)

    assert comparison is not None
    assert len(comparison) == 1
    assert comparison[0]["main_matches"] == 3
    assert comparison[0]["powerball_match"] is False
    assert comparison[0]["bonus_match"] is False


def test_format_result_message_shows_division_and_prizes():
    comparison = [
        {
            "line": 1,
            "main_matches": 2,
            "bonus_match": False,
            "powerball_match": False,
            "division": None,
            "prize_amount": None,
            "prize_note": None,
        },
        {
            "line": 2,
            "main_matches": 3,
            "bonus_match": True,
            "powerball_match": False,
            "division": 6,
            "prize_amount": 702.0,
            "prize_note": None,
        },
        {
            "line": 3,
            "main_matches": 3,
            "bonus_match": False,
            "powerball_match": True,
            "division": 7,
            "prize_amount": 15.0,
            "prize_note": None,
        },
    ]
    message = format_result_message(
        _actual_row(), comparison, dividends=_fake_dividends()
    )

    assert "Today's Result:" in message
    assert "Division 1: Lotto WON $1M | Powerball not won, rolls over" in message
    assert "1. Main: 2 matched | Bonus: No | Powerball: No" in message
    assert "2. Main: 3 matched | Bonus: Yes | Powerball: No — Won $702!" in message
    assert "3. Main: 3 matched | Bonus: No | Powerball: Yes — Won $15 (Div 7)!" in message
    assert "Best line" not in message
