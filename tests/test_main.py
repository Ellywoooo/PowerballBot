"""Tests for main orchestrator guards."""

import pandas as pd

from scorer import save_predictions, should_skip_predict
from main import run_predict


def _write_draws(path, draws):
    rows = ["Draw,Date,Winning Number 1,2,3,4,5,6,Bonus Number,Powerball"]
    for draw, date, mains, bonus, powerball in draws:
        rows.append(
            f"{draw},{date},{mains[0]},{mains[1]},{mains[2]},"
            f"{mains[3]},{mains[4]},{mains[5]},{bonus},{powerball}"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_history(path, draw, predicted_at="2026-07-18T12:00:00+00:00"):
    rows = [
        "Draw,Line,Number 1,Number 2,Number 3,Number 4,Number 5,Number 6,"
        "Powerball,Score,Main Matches,Bonus Match,Powerball Match,Division,"
        "Prize Amount,Prize Note,Predicted At"
    ]
    for line in range(1, 9):
        rows.append(
            f"{draw},{line},1,2,3,4,5,6,7,3.0,0,False,False,,,,"
            f"{predicted_at}"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_should_skip_predict_when_latest_draw_archived_and_latest_pending(
    tmp_path, monkeypatch
):
    draws = tmp_path / "draws_clean.csv"
    history = tmp_path / "history.csv"
    latest = tmp_path / "latest.csv"

    _write_draws(
        draws,
        [
            (2603, "2026-07-15", [6, 10, 14, 19, 20, 27], 39, 1),
            (2604, "2026-07-18", [13, 28, 30, 31, 34, 35], 10, 9),
        ],
    )
    _write_history(history, 2604)
    save_predictions(
        pd.DataFrame(
            [
                {
                    "line_no": 1,
                    "line": "10 12 13 22 24 25",
                    "powerball": 1,
                    "score": 3.5,
                }
            ]
        ),
        path=latest,
    )

    monkeypatch.setattr("scorer.config.DATA_PATH", str(draws))
    monkeypatch.setattr("scorer.config.PREDICTIONS_HISTORY_PATH", str(history))
    monkeypatch.setattr("scorer.config.PREDICTIONS_LATEST_PATH", str(latest))

    assert should_skip_predict() is True


def test_should_skip_predict_allows_next_draw_when_latest_draw_is_filled(
    tmp_path, monkeypatch
):
    draws = tmp_path / "draws_clean.csv"
    history = tmp_path / "history.csv"
    latest = tmp_path / "latest.csv"

    _write_draws(
        draws,
        [
            (2603, "2026-07-15", [6, 10, 14, 19, 20, 27], 39, 1),
            (2604, "2026-07-18", [13, 28, 30, 31, 34, 35], 10, 9),
        ],
    )
    _write_history(history, 2604)
    save_predictions(
        pd.DataFrame(
            [
                {
                    "line_no": 1,
                    "line": "10 12 13 22 24 25",
                    "powerball": 1,
                    "score": 3.5,
                }
            ]
        ),
        path=latest,
    )

    latest_df = pd.read_csv(latest)
    latest_df["Draw"] = 2604
    latest_df.to_csv(latest, index=False)

    monkeypatch.setattr("scorer.config.DATA_PATH", str(draws))
    monkeypatch.setattr("scorer.config.PREDICTIONS_HISTORY_PATH", str(history))
    monkeypatch.setattr("scorer.config.PREDICTIONS_LATEST_PATH", str(latest))

    assert should_skip_predict() is False


def test_run_predict_skips_when_draw_already_archived(tmp_path, monkeypatch, capsys):
    draws = tmp_path / "draws_clean.csv"
    history = tmp_path / "history.csv"
    latest = tmp_path / "latest.csv"

    _write_draws(
        draws,
        [
            (2603, "2026-07-15", [6, 10, 14, 19, 20, 27], 39, 1),
            (2604, "2026-07-18", [13, 28, 30, 31, 34, 35], 10, 9),
        ],
    )
    _write_history(history, 2604)
    save_predictions(
        pd.DataFrame(
            [
                {
                    "line_no": 1,
                    "line": "10 12 13 22 24 25",
                    "powerball": 1,
                    "score": 3.5,
                }
            ]
        ),
        path=latest,
    )

    monkeypatch.setattr("config.DATA_PATH", str(draws))
    monkeypatch.setattr("scorer.config.DATA_PATH", str(draws))
    monkeypatch.setattr("scorer.config.PREDICTIONS_HISTORY_PATH", str(history))
    monkeypatch.setattr("scorer.config.PREDICTIONS_LATEST_PATH", str(latest))

    save_called = []
    monkeypatch.setattr("main.save_predictions", lambda *args, **kwargs: save_called.append(True))
    monkeypatch.setattr(
        "main.generate_lines",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not generate")),
    )

    run_predict()

    assert save_called == []
    output = capsys.readouterr().out
    assert "Draw 2604 already archived" in output
    assert "skipping predict" in output
