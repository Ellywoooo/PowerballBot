"""Tests for crawler parse/append/fetch — no real network calls."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from crawler import parse_draw, append_if_new, fetch_latest_draw


def _fake_api_response():
    return {
        "lotto": {
            "drawNumber": 2602,
            "drawDate": "2026-07-11",
            "lottoWinningNumbers": {
                "numbers": ["10", "21", "22", "26", "37", "40"],
                "bonusBalls": "15",
            },
        },
        "powerBall": {
            "powerballWinningNumber": "6",
        },
    }


def _csv_row(
    draw=2600,
    date="2026-07-04",
    n1=2,
    n2=15,
    n3=17,
    n4=18,
    n5=26,
    n6=30,
    bonus=28,
    powerball=9,
):
    return {
        "Draw": draw,
        "Date": date,
        "Winning Number 1": n1,
        "2": n2,
        "3": n3,
        "4": n4,
        "5": n5,
        "6": n6,
        "Bonus Number": bonus,
        "Powerball": powerball,
    }


def test_parse_draw_matches_csv_shape():
    row = parse_draw(_fake_api_response())

    assert row == {
        "Draw": 2602,
        "Date": "2026-07-11",
        "Winning Number 1": 10,
        "2": 21,
        "3": 22,
        "4": 26,
        "5": 37,
        "6": 40,
        "Bonus Number": 15,
        "Powerball": 6,
    }


def test_append_if_new_skips_duplicate(tmp_path):
    path = tmp_path / "draws.csv"
    existing = _csv_row(draw=2600)
    pd.DataFrame([existing]).to_csv(path, index=False)

    duplicate = _csv_row(draw=2600, date="2026-07-04")
    assert append_if_new(duplicate, path=path) is False

    df = pd.read_csv(path)
    assert len(df) == 1


def test_append_if_new_adds_new_row(tmp_path):
    path = tmp_path / "draws.csv"
    existing = _csv_row(draw=2600)
    pd.DataFrame([existing]).to_csv(path, index=False)

    new_row = _csv_row(
        draw=2601,
        date="2026-07-08",
        n1=12,
        n2=15,
        n3=27,
        n4=28,
        n5=35,
        n6=40,
        bonus=9,
        powerball=7,
    )
    assert append_if_new(new_row, path=path) is True

    df = pd.read_csv(path)
    assert len(df) == 2
    assert int(df.loc[0, "Draw"]) == 2601
    assert int(df.loc[0, "Winning Number 1"]) == 12
    assert int(df.loc[0, "Powerball"]) == 7
    assert int(df.loc[1, "Draw"]) == 2600


def _mock_response(status_code, payload=None, text=""):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    response.json.return_value = payload if payload is not None else {}
    return response


@patch("crawler.time.sleep", return_value=None)
@patch("crawler.requests.get")
def test_fetch_latest_draw_raises_on_429(mock_get, _mock_sleep):
    mock_get.return_value = _mock_response(429, text="rate limited")
    with pytest.raises(RuntimeError, match="429"):
        fetch_latest_draw()


@patch("crawler.time.sleep", return_value=None)
@patch("crawler.requests.get")
def test_fetch_latest_draw_raises_on_503(mock_get, _mock_sleep):
    mock_get.return_value = _mock_response(503, text="busy")
    with pytest.raises(RuntimeError, match="503"):
        fetch_latest_draw()


@patch("crawler.time.sleep", return_value=None)
@patch("crawler.requests.get")
def test_fetch_latest_draw_returns_json_on_200(mock_get, _mock_sleep):
    payload = _fake_api_response()
    mock_get.return_value = _mock_response(200, payload=payload)

    result = fetch_latest_draw()

    assert result == payload
    mock_get.assert_called_once()
