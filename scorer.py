"""
Compare predicted lines against the actual draw result.

save_predictions()                 → write predictions/latest.csv after generate_lines
compare_prediction_to_actual()     → main/PB match counts per line
archive_predictions()              → fill Draw on latest + append to history.csv
"""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import config

PRED_NUMBER_COLS = [
    "Number 1",
    "Number 2",
    "Number 3",
    "Number 4",
    "Number 5",
    "Number 6",
]
ACTUAL_MAIN_COLS = [
    "Winning Number 1",
    "2",
    "3",
    "4",
    "5",
    "6",
]
LATEST_COLUMNS = [
    "Line",
    *PRED_NUMBER_COLS,
    "Powerball",
    "Score",
    "Draw",
    "Predicted At",
]
HISTORY_COLUMNS = [
    "Draw",
    "Line",
    *PRED_NUMBER_COLS,
    "Powerball",
    "Main Matches",
    "Powerball Match",
    "Predicted At",
]


def _predicted_mains(row):
    return [int(row[c]) for c in PRED_NUMBER_COLS]


def _actual_mains(actual_row):
    return [int(actual_row[c]) for c in ACTUAL_MAIN_COLS]


def save_predictions(lines_df, path=config.PREDICTIONS_LATEST_PATH):
    """
    Save generate_lines() output to predictions/latest.csv.
    Draw is left blank until the 9:30pm results run fills it in.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    predicted_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for _, line in lines_df.iterrows():
        mains = [int(n) for n in str(line["line"]).split()]
        rows.append(
            {
                "Line": int(line["line_no"]),
                "Number 1": mains[0],
                "Number 2": mains[1],
                "Number 3": mains[2],
                "Number 4": mains[3],
                "Number 5": mains[4],
                "Number 6": mains[5],
                "Powerball": int(line["powerball"]),
                "Score": float(line["score"]),
                "Draw": pd.NA,
                "Predicted At": predicted_at,
            }
        )

    pd.DataFrame(rows, columns=LATEST_COLUMNS).to_csv(path, index=False)
    return path


def compare_prediction_to_actual(actual_row, path=config.PREDICTIONS_LATEST_PATH):
    """
    Compare each predicted line in latest.csv to the actual draw.

    Returns:
        list[dict] like
        [{"line": 1, "main_matches": 3, "powerball_match": False}, ...]
        or None if predictions/latest.csv does not exist yet.
    """
    path = Path(path)
    if not path.exists():
        return None

    predictions = pd.read_csv(path)
    actual_mains = set(_actual_mains(actual_row))
    actual_pb = int(actual_row["Powerball"])

    comparison = []
    for _, row in predictions.iterrows():
        predicted_mains = set(_predicted_mains(row))
        comparison.append(
            {
                "line": int(row["Line"]),
                "main_matches": len(predicted_mains & actual_mains),
                "powerball_match": int(row["Powerball"]) == actual_pb,
            }
        )
    return comparison


def archive_predictions(actual_row, comparison, path=config.PREDICTIONS_LATEST_PATH):
    """
    Fill Draw on latest.csv and append scored rows to predictions/history.csv.
    No-op if latest.csv is missing.
    """
    latest_path = Path(path)
    if not latest_path.exists() or comparison is None:
        return None

    history_path = Path(config.PREDICTIONS_HISTORY_PATH)
    history_path.parent.mkdir(parents=True, exist_ok=True)

    predictions = pd.read_csv(latest_path)
    draw_number = actual_row["Draw"]
    predictions["Draw"] = draw_number
    predictions.to_csv(latest_path, index=False)

    match_by_line = {item["line"]: item for item in comparison}
    history_rows = []
    for _, row in predictions.iterrows():
        line_no = int(row["Line"])
        match = match_by_line[line_no]
        history_rows.append(
            {
                "Draw": draw_number,
                "Line": line_no,
                "Number 1": int(row["Number 1"]),
                "Number 2": int(row["Number 2"]),
                "Number 3": int(row["Number 3"]),
                "Number 4": int(row["Number 4"]),
                "Number 5": int(row["Number 5"]),
                "Number 6": int(row["Number 6"]),
                "Powerball": int(row["Powerball"]),
                "Main Matches": match["main_matches"],
                "Powerball Match": match["powerball_match"],
                "Predicted At": row["Predicted At"],
            }
        )

    history_df = pd.DataFrame(history_rows, columns=HISTORY_COLUMNS)
    if history_path.exists() and history_path.stat().st_size > 0:
        history_df.to_csv(history_path, mode="a", header=False, index=False)
    else:
        history_df.to_csv(history_path, index=False)

    return history_path
