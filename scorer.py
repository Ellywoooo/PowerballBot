"""
Compare predicted lines against the actual draw result.

save_predictions()                 → write predictions/latest.csv after generate_lines
compare_prediction_to_actual()     → main/PB match counts + division/prize per line
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
    "Score",
    "Main Matches",
    "Bonus Match",
    "Powerball Match",
    "Division",
    "Prize Amount",
    "Prize Note",
    "Predicted At",
]


def _history_cell(value):
    """Write blank cells for None/NaN instead of the string 'None'."""
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return value


def _predicted_mains(row):
    return [int(row[c]) for c in PRED_NUMBER_COLS]


def _actual_mains(actual_row):
    return [int(actual_row[c]) for c in ACTUAL_MAIN_COLS]


def determine_division(main_matches, bonus_match):
    """Return Lotto division 1-7 from main/bonus match counts, or None."""
    if main_matches == 6:
        return 1
    if main_matches == 5 and bonus_match:
        return 2
    if main_matches == 5:
        return 3
    if main_matches == 4 and bonus_match:
        return 4
    if main_matches == 4:
        return 5
    if main_matches == 3 and bonus_match:
        return 6
    if main_matches == 3:
        return 7
    return None


def parse_prize_value(value):
    """Convert API prizeValue string to float, or None for non-numeric values."""
    if value is None:
        return None
    text = str(value).strip()
    try:
        return float(text)
    except ValueError:
        return None


def _winner_by_division(winners, division):
    for entry in winners:
        if int(entry.get("division", -1)) == division:
            return entry
    return None


def _lookup_prize(dividends, division, powerball_match):
    """Return (prize_amount, prize_note) for a winning division."""
    if division is None:
        return None, None

    if powerball_match:
        winner = _winner_by_division(dividends.get("powerballWinners", []), division)
        if winner is None:
            return None, None
        combined = winner.get("combinedPrizeValue")
        amount = parse_prize_value(combined)
        if amount is not None:
            return amount, None
        raw = winner.get("prizeValue")
    else:
        winner = _winner_by_division(dividends.get("lottoWinners", []), division)
        if winner is None:
            return None, None
        raw = winner.get("prizeValue")

    amount = parse_prize_value(raw)
    if amount is not None:
        return amount, None
    return None, str(raw) if raw is not None else None


def division_one_status(dividends):
    """Report whether Lotto / Powerball division 1 was won this draw."""
    lotto_div1 = _winner_by_division(dividends.get("lottoWinners", []), 1)
    pb_div1 = _winner_by_division(dividends.get("powerballWinners", []), 1)

    lotto_won = lotto_div1 is not None and int(lotto_div1.get("numberOfWinners", 0)) > 0
    powerball_won = pb_div1 is not None and int(pb_div1.get("numberOfWinners", 0)) > 0

    return {"lotto_won": lotto_won, "powerball_won": powerball_won}


def _latest_completed_draw(draws_path=None):
    """Return the most recent draw number in draws_clean.csv."""
    column_names = [
        "draw_number",
        "draw_date",
        "main_1",
        "main_2",
        "main_3",
        "main_4",
        "main_5",
        "main_6",
        "bonus",
        "powerball",
    ]
    path = draws_path or config.DATA_PATH
    df = pd.read_csv(path, header=0, names=column_names)
    df["draw_date"] = pd.to_datetime(df["draw_date"])
    return int(df.sort_values("draw_date").iloc[-1]["draw_number"])


def should_skip_predict(
    draws_path=None,
    history_path=None,
    latest_path=None,
):
    """
    Return True when the latest completed draw is already archived but
    latest.csv still has a pending prediction (blank Draw).

    This blocks manual re-runs of predict mode after results have already
    archived that draw. When latest.csv Draw is filled (normal post-results
    state), predict proceeds so the next draw can be generated.
    """
    latest_draw = _latest_completed_draw(draws_path)

    hist_path = Path(history_path or config.PREDICTIONS_HISTORY_PATH)
    if not hist_path.exists() or hist_path.stat().st_size == 0:
        return False

    history = pd.read_csv(hist_path)
    if latest_draw not in history["Draw"].values:
        return False

    latest_file = Path(latest_path or config.PREDICTIONS_LATEST_PATH)
    if not latest_file.exists():
        return False

    latest_pred = pd.read_csv(latest_file)
    if latest_pred.empty:
        return False

    draw_val = latest_pred["Draw"].iloc[0]
    return pd.isna(draw_val)


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


def compare_prediction_to_actual(
    actual_row,
    path=config.PREDICTIONS_LATEST_PATH,
    dividends=None,
):
    """
    Compare each predicted line in latest.csv to the actual draw.

    Returns list of dicts per line, or None if latest.csv is missing.
    When dividends is provided, also computes division and prize info.
    """
    path = Path(path)
    if not path.exists():
        return None

    predictions = pd.read_csv(path)
    actual_mains = set(_actual_mains(actual_row))
    actual_bonus = int(actual_row["Bonus Number"])
    actual_pb = int(actual_row["Powerball"])

    comparison = []
    for _, row in predictions.iterrows():
        predicted_mains = set(_predicted_mains(row))
        main_matches = len(predicted_mains & actual_mains)
        bonus_match = actual_bonus in predicted_mains
        powerball_match = int(row["Powerball"]) == actual_pb

        entry = {
            "line": int(row["Line"]),
            "main_matches": main_matches,
            "bonus_match": bonus_match,
            "powerball_match": powerball_match,
        }

        if dividends is not None:
            division = determine_division(main_matches, bonus_match)
            prize_amount, prize_note = _lookup_prize(
                dividends, division, powerball_match
            )
            entry["division"] = division
            entry["prize_amount"] = prize_amount
            entry["prize_note"] = prize_note
        else:
            entry["division"] = None
            entry["prize_amount"] = None
            entry["prize_note"] = None

        comparison.append(entry)
    return comparison


def archive_predictions(actual_row, comparison, path=config.PREDICTIONS_LATEST_PATH):
    """
    Fill Draw on latest.csv and append scored rows to predictions/history.csv.
    Skips if this Draw is already archived. Returns True if appended, False if
    skipped, None if latest.csv is missing.
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

    if history_path.exists() and history_path.stat().st_size > 0:
        existing = pd.read_csv(history_path)
        if draw_number in existing["Draw"].values:
            print(f"Draw {draw_number} already archived, skipping")
            return False
    else:
        existing = None

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
                "Score": float(row["Score"]),
                "Main Matches": match["main_matches"],
                "Bonus Match": match["bonus_match"],
                "Powerball Match": match["powerball_match"],
                "Division": _history_cell(match.get("division")),
                "Prize Amount": _history_cell(match.get("prize_amount")),
                "Prize Note": _history_cell(match.get("prize_note")),
                "Predicted At": row["Predicted At"],
            }
        )

    history_df = pd.DataFrame(history_rows, columns=HISTORY_COLUMNS)
    if existing is not None:
        history_df = pd.concat([existing, history_df], ignore_index=True)

    history_df.to_csv(history_path, index=False)
    return True
