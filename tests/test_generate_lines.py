"""Tests for weighted random sampling in generate_lines."""

import numpy as np
import pandas as pd
import pytest

from predictor import generate_lines


def _fake_scores():
    """Build synthetic score Series so tests do not depend on the CSV."""
    # Slightly varying scores keep combination ranking interesting.
    main_score = pd.Series(
        {n: 0.4 + (n % 7) * 0.05 + (n % 3) * 0.02 for n in range(1, 41)}
    )
    powerball_score = pd.Series(
        {n: 0.3 + (n % 5) * 0.1 for n in range(1, 11)}
    )
    return main_score, powerball_score


def test_same_seed_produces_identical_results():
    main_score, powerball_score = _fake_scores()

    first = generate_lines(main_score, powerball_score, seed=42)
    second = generate_lines(main_score, powerball_score, seed=42)

    pd.testing.assert_frame_equal(first.reset_index(drop=True), second.reset_index(drop=True))


def test_unseeded_runs_produce_different_results():
    main_score, powerball_score = _fake_scores()

    results = [
        generate_lines(main_score, powerball_score, seed=None)
        for _ in range(8)
    ]

    # Encode each result as a comparable tuple of (line, powerball).
    signatures = [
        tuple(zip(df["line"].tolist(), df["powerball"].tolist()))
        for df in results
    ]

    # With weighted random sampling, identical full outputs across many
    # unseeded runs are extremely unlikely.
    assert len(set(signatures)) > 1
