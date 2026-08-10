"""Tests for predictor filters, scoring, and generate_lines pool expansion."""

from datetime import date, datetime, timedelta

import pandas as pd
import pytest
import numpy as np

import config
from predictor import (
    passes_filters,
    compute_main_scores,
    compute_powerball_scores,
    apply_recency_penalty,
    generate_lines,
    _sampling_weights,
    _mains_from_row,
)


def _synthetic_draws(n_draws=15):
    """
    Build a small DataFrame matching load_draws() column shape.
    Cycles numbers so every main/bonus value 1-40 appears at least once.
    """
    rows = []
    start = datetime(2025, 1, 1)
    pool = list(range(1, 41))
    for i in range(n_draws):
        offset = (i * 7) % 40
        mains = [pool[(offset + j) % 40] for j in range(6)]
        bonus = pool[(offset + 6) % 40]
        rows.append(
            {
                "draw_number": 2500 + i,
                "draw_date": start + timedelta(days=i * 3),
                "main_1": mains[0],
                "main_2": mains[1],
                "main_3": mains[2],
                "main_4": mains[3],
                "main_5": mains[4],
                "main_6": mains[5],
                "bonus": bonus,
                "powerball": (i % 10) + 1,
            }
        )
    return pd.DataFrame(rows)


def test_passes_filters_rejects_all_odd():
    assert passes_filters([1, 3, 5, 7, 9, 11]) is False


def test_passes_filters_rejects_all_even():
    assert passes_filters([2, 4, 6, 8, 10, 12]) is False


def test_passes_filters_rejects_four_consecutive():
    assert passes_filters([1, 2, 3, 4, 10, 20]) is False


def test_passes_filters_accepts_valid_mixed_line():
    assert passes_filters([2, 5, 11, 19, 27, 33]) is True


def test_compute_main_scores_scaled_between_0_and_1():
    df = _synthetic_draws()
    scores = compute_main_scores(df)

    assert scores.index.min() >= 1
    assert scores.index.max() <= 40
    assert scores.notna().all()
    assert (scores >= 0).all()
    assert (scores <= 1).all()


@pytest.mark.parametrize(
    "today, expected",
    [
        (date(2026, 9, 1), 10),
        (date(2026, 9, 13), 14),
        (date(2026, 9, 20), 14),
    ],
)
def test_get_powerball_max_switches_on_rule_change_date(today, expected):
    assert config.get_powerball_max(today=today) == expected


def test_compute_powerball_scores_filters_old_rule_draws_after_change(monkeypatch):
    df = pd.DataFrame(
        {
            "draw_date": pd.to_datetime(
                ["2026-09-01", "2026-09-05", "2026-09-13", "2026-09-16"]
            ),
            "powerball": [1, 1, 2, 14],
        }
    )
    post_change_df = df[df["draw_date"].dt.date >= config.POWERBALL_RULE_CHANGE_DATE]
    real_get_powerball_max = config.get_powerball_max

    monkeypatch.setattr(
        config,
        "get_powerball_max",
        lambda: real_get_powerball_max(today=date(2026, 9, 20)),
    )
    post_change_scores = compute_powerball_scores(df)
    expected_post_change_scores = compute_powerball_scores(post_change_df)
    pd.testing.assert_series_equal(
        post_change_scores,
        expected_post_change_scores,
    )
    assert list(post_change_scores.index) == list(range(1, 15))

    monkeypatch.setattr(
        config,
        "get_powerball_max",
        lambda: real_get_powerball_max(today=date(2026, 9, 1)),
    )
    pre_change_scores = compute_powerball_scores(df)
    pre_change_without_old_draws = compute_powerball_scores(post_change_df)
    assert not pre_change_scores.equals(pre_change_without_old_draws)
    assert list(pre_change_scores.index) == list(range(1, 11))


def test_generate_lines_expands_pool_without_crashing(monkeypatch):
    """
    Tiny SAMPLE_POOL_SIZE forces the sliding window to expand beyond the
    first slice when diversity (_too_similar) rejects nearby high-score combos.
    """
    monkeypatch.setattr(config, "SAMPLE_POOL_SIZE", 5)
    monkeypatch.setattr(config, "NUM_LINES", 8)

    # Top scores clustered on neighbouring numbers → early pool is too similar.
    main_score = pd.Series({n: 1.0 - (n * 0.001) for n in range(1, 41)})
    powerball_score = pd.Series({n: 0.5 for n in range(1, 11)})

    lines = generate_lines(main_score, powerball_score, seed=7)

    assert len(lines) <= config.NUM_LINES
    assert len(lines) >= 1
    assert set(lines.columns) >= {"line_no", "line", "powerball", "score"}


def _steep_main_score():
    return pd.Series({n: 1.0 - (n * 0.001) for n in range(1, 41)})


def _flat_powerball_score():
    return pd.Series({n: 0.5 for n in range(1, 11)})


def _unique_numbers_from_sampling(sampling_score, available, n_runs=20, seed=0):
    rng = np.random.default_rng(seed)
    numbers = set()

    for _ in range(n_runs):
        probs = _sampling_weights(available, sampling_score)
        idx = int(rng.choice(len(available), p=probs))
        numbers.update(_mains_from_row(available.iloc[idx]))

    return len(numbers)


def _write_fake_history(path, draws, number_in_every_line=7):
    rows = [
        "Draw,Line,Number 1,Number 2,Number 3,Number 4,Number 5,Number 6,"
        "Powerball,Score,Main Matches,Bonus Match,Powerball Match,Division,"
        "Prize Amount,Prize Note,Predicted At"
    ]
    for draw_idx, draw in enumerate(draws):
        predicted_at = f"2026-07-{10 + draw_idx:02d}T12:00:00+00:00"
        for line in range(1, 9):
            nums = [number_in_every_line] * 6
            rows.append(
                f"{draw},{line},{nums[0]},{nums[1]},{nums[2]},"
                f"{nums[3]},{nums[4]},{nums[5]},1,3.0,0,False,False,,,,"
                f"{predicted_at}"
            )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_temperature_flattens_distribution(monkeypatch):
    """Temperature scaling flattens sampling weights used inside generate_lines()."""
    sampling_score = pd.Series(
        {n: max(0.01, 1.5 - (n * 0.08)) for n in range(1, 41)}
    )
    available = pd.DataFrame(
        [
            {"m1": 1, "m2": 2, "m3": 3, "m4": 4, "m5": 5, "m6": 6, "score": 6.0},
            {"m1": 7, "m2": 8, "m3": 9, "m4": 10, "m5": 11, "m6": 12, "score": 5.0},
            {"m1": 13, "m2": 14, "m3": 15, "m4": 16, "m5": 17, "m6": 18, "score": 4.0},
        ]
    )

    monkeypatch.setattr(config, "SAMPLING_TEMPERATURE", 1.0)
    low_temp_probs = _sampling_weights(available, sampling_score)

    monkeypatch.setattr(config, "SAMPLING_TEMPERATURE", 3.0)
    high_temp_probs = _sampling_weights(available, sampling_score)

    assert high_temp_probs.max() < low_temp_probs.max()
    assert high_temp_probs.std() < low_temp_probs.std()

    monkeypatch.setattr(config, "SAMPLING_TEMPERATURE", 1.0)
    low_temp_variety = _unique_numbers_from_sampling(
        pd.Series({n: (100.0 if n <= 6 else 0.01) for n in range(1, 41)}),
        available,
    )

    monkeypatch.setattr(config, "SAMPLING_TEMPERATURE", 3.0)
    high_temp_variety = _unique_numbers_from_sampling(
        pd.Series({n: (100.0 if n <= 6 else 0.01) for n in range(1, 41)}),
        available,
    )

    assert high_temp_variety > low_temp_variety


def test_recency_penalty_reduces_score_for_frequent_numbers(tmp_path):
    history = tmp_path / "history.csv"
    _write_fake_history(history, draws=[2601, 2602, 2603, 2604])

    main_score = pd.Series({n: 0.8 for n in range(1, 41)})
    adjusted = apply_recency_penalty(
        main_score,
        history_path=history,
        lookback_draws=4,
        penalty_strength=0.25,
    )

    assert adjusted[7] < main_score[7]
    assert adjusted[33] == main_score[33]
    assert (main_score[7] - adjusted[7]) > (main_score[33] - adjusted[33])


def test_recency_penalty_no_history_file_returns_unchanged(tmp_path):
    main_score = pd.Series({n: 0.5 + (n * 0.01) for n in range(1, 41)})
    missing = tmp_path / "does_not_exist.csv"

    adjusted = apply_recency_penalty(main_score, history_path=missing)

    pd.testing.assert_series_equal(adjusted, main_score)
