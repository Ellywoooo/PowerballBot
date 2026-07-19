"""Tests for Slack notifier helpers — no real network calls."""

from unittest.mock import MagicMock, patch

from notifier import notify_error


@patch("notifier.requests.post")
@patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=False)
def test_notify_error_message_format(mock_post):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    notify_error("crawler", "Rate limited / server busy: 429", "results")

    mock_post.assert_called_once()
    payload = mock_post.call_args.kwargs["json"]
    message = payload["text"]

    assert "⚠️ Lotto bot failed (mode: results)" in message
    assert "Step: crawler" in message
    assert "Error: Rate limited / server busy: 429" in message
    assert "Time:" in message
    assert "UTC" in message


@patch("notifier.requests.post", side_effect=RuntimeError("webhook down"))
@patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}, clear=False)
def test_notify_error_swallows_secondary_failure(mock_post, capsys):
    # Must not raise — failure to alert should only print.
    notify_error("notifier", "boom", "predict")

    captured = capsys.readouterr()
    assert "Failed to send error notification:" in captured.out
