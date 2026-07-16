"""Tests for predictor filters, scoring, and generate_lines pool expansion."""

from datetime import datetime, timedelta

import pandas as pd
import pytest

import config
from predictor import (
    passes_filters,
    compute_main_scores,
    generate_lines,
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
