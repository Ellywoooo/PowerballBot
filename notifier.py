import os

import requests
from dotenv import load_dotenv

load_dotenv()

# Format the message for the Slack webhook
# Input: DataFrame with columns 'line_no', 'line', and 'powerball'
# Output: String formatted for Slack webhook
def format_message(lines_df):
    lines = ["Today's Lotto Powerball Suggestions!\n"]
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
def notify(lines_df):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise ValueError("SLACK_WEBHOOK_URL not set in .env")
    message = format_message(lines_df)
    send_slack(message, webhook_url)


def notify_results(draw_row):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise ValueError("SLACK_WEBHOOK_URL not set in .env")
    message = format_results_message(draw_row)
    send_slack(message, webhook_url)

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