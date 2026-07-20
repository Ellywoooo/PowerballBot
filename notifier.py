import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

def _format_jackpot_millions(jackpot_amount):
    """Turn 35_000_000 into '$35 million' (supports fractional millions)."""
    millions = jackpot_amount / 1_000_000
    if millions == int(millions):
        return f"${int(millions)} million"
    return f"${millions:g} million"


# Format the message for the Slack webhook
# Input: DataFrame with columns 'line_no', 'line', and 'powerball'
#        optional jackpot_amount in whole dollars (e.g. 35_000_000)
# Output: String formatted for Slack webhook
def format_message(lines_df, jackpot_amount=None):
    lines = ["Today's Lotto Powerball Suggestions!\n"]
    if jackpot_amount is not None:
        lines.append(
            f"💰 This draw's Powerball jackpot: {_format_jackpot_millions(jackpot_amount)}\n"
        )
    lines.extend(
        f"{int(row['line_no'])}. {row['line']} + PB {int(row['powerball'])}"
        for _, row in lines_df.iterrows()
    )
    lines.append("\nStatistical analysis only - does not guarantee a win.")
    return "\n".join(lines)

# Send the message to the Slack webhook
# Input: String message and Slack webhook URL (POST request)
# Output: Response from the Slack webhook
def send_slack(message, webhook_url):
    response = requests.post(
        webhook_url,
        json={"text": message},
        timeout=10,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Slack webhook failed: {response.status_code} {response.text}"
        )
    return response

# Format the latest winning results into a Slack message.
# Input: dict row from crawler.parse_draw()
# Output: String formatted for Slack webhook
def format_results_message(draw_row):
    mains = [
        int(draw_row["Winning Number 1"]),
        int(draw_row["2"]),
        int(draw_row["3"]),
        int(draw_row["4"]),
        int(draw_row["5"]),
        int(draw_row["6"]),
    ]
    bonus = int(draw_row["Bonus Number"])
    powerball = int(draw_row["Powerball"])

    mains_text = " ".join(f"{n:02d}" for n in sorted(mains))
    return "\n".join(
        [
            "Latest NZ Lotto results",
            f"Draw {draw_row['Draw']} ({draw_row['Date']})",
            f"Mains: {mains_text}",
            f"Bonus: {bonus:02d}",
            f"Powerball: {powerball}",
        ]
    )

# Load URL from .env -> format -> send.
def notify(lines_df, jackpot_amount=None):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise ValueError("SLACK_WEBHOOK_URL not set in .env")
    message = format_message(lines_df, jackpot_amount=jackpot_amount)
    send_slack(message, webhook_url)


def notify_results(draw_row, comparison=None, dividends=None):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise ValueError("SLACK_WEBHOOK_URL not set in .env")
    if comparison is None:
        message = format_results_message(draw_row)
    else:
        message = format_result_message(draw_row, comparison, dividends)
    send_slack(message, webhook_url)


def notify_error(step, error, mode):
    """
    Send a Slack alert when a pipeline step fails.
    Failures here are printed only — never raise secondary errors.
    """
    try:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if not webhook_url:
            raise ValueError("SLACK_WEBHOOK_URL not set in .env")

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        message = (
            f"⚠️ Lotto bot failed (mode: {mode})\n"
            f"\n"
            f"Step: {step}\n"
            f"Error: {error}\n"
            f"\n"
            f"Time: {timestamp}"
        )
        send_slack(message, webhook_url)
    except Exception as exc:
        print(f"Failed to send error notification: {exc}")


def _format_prize_amount(amount):
    """Format a prize dollar amount for Slack (e.g. $22 or $1.0M)."""
    if amount >= 1_000_000:
        millions = amount / 1_000_000
        if millions == int(millions):
            return f"${int(millions)}M"
        return f"${millions:.1f}M"
    if amount == int(amount):
        return f"${int(amount):,}"
    return f"${amount:,.2f}"


def _division_one_line(dividends):
    """Build the Division 1 status line from draw dividend data."""
    from scorer import division_one_status, parse_prize_value, _winner_by_division

    status = division_one_status(dividends)
    lotto_div1 = _winner_by_division(dividends.get("lottoWinners", []), 1)
    pb_div1 = _winner_by_division(dividends.get("powerballWinners", []), 1)

    if status["lotto_won"]:
        lotto_prize = parse_prize_value(lotto_div1.get("prizeValue"))
        lotto_text = f"WON {_format_prize_amount(lotto_prize)}" if lotto_prize else "WON"
    else:
        lotto_text = "not won"

    if status["powerball_won"]:
        pb_raw = pb_div1.get("combinedPrizeValue") or pb_div1.get("prizeValue")
        pb_prize = parse_prize_value(pb_raw)
        pb_text = f"WON {_format_prize_amount(pb_prize)}" if pb_prize else "WON"
    else:
        pb_note = (pb_div1 or {}).get("prizeValue", "")
        pb_text = "not won, rolls over" if str(pb_note).upper() == "ROLLOVER" else "not won"

    return f"🎰 Division 1: Lotto {lotto_text} | Powerball {pb_text}"


def format_result_message(actual_row, comparison, dividends=None):
    """
    Build a Slack message with winning numbers, division 1 status,
    and per-line match/prize breakdown.
    """
    mains = [
        int(actual_row["Winning Number 1"]),
        int(actual_row["2"]),
        int(actual_row["3"]),
        int(actual_row["4"]),
        int(actual_row["5"]),
        int(actual_row["6"]),
    ]
    mains_text = " ".join(f"{n:02d}" for n in sorted(mains))
    powerball = int(actual_row["Powerball"])

    lines = [
        f"🎯 Today's Result: {mains_text} + PB {powerball}",
    ]

    if dividends is not None:
        lines.append(_division_one_line(dividends))

    lines.append("")
    lines.append("Your predictions:")

    for item in comparison:
        line_no = item["line"]
        bonus = "Yes" if item.get("bonus_match") else "No"
        pb = "Yes" if item["powerball_match"] else "No"
        base = (
            f"{line_no}. Main: {item['main_matches']} matched | "
            f"Bonus: {bonus} | Powerball: {pb}"
        )

        division = item.get("division")
        prize_amount = item.get("prize_amount")
        prize_note = item.get("prize_note")

        if division is not None and prize_amount is not None:
            suffix = f" — Won {_format_prize_amount(prize_amount)}!"
            if item["powerball_match"]:
                suffix = f" — Won {_format_prize_amount(prize_amount)} (Div {division})!"
            lines.append(base + suffix)
        elif division is not None and prize_note:
            lines.append(base + f" — Division {division} (prize: {prize_note})")
        else:
            lines.append(base)

    return "\n".join(lines)

# Test the notifier
if __name__ == "__main__":
    from predictor import (
        load_draws,
        compute_main_scores,
        compute_powerball_scores,
        generate_lines,
    )

    df = load_draws()
    main_score = compute_main_scores(df)
    powerball_score = compute_powerball_scores(df)
    lines = generate_lines(main_score, powerball_score)

    notify(lines)
    print("Sent to Slack!")