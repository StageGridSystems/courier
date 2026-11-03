"""Tests for sender rate limiting and mocked Gmail send."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from courier.exceptions import SendError
from courier.sender.gmail_send import build_raw_message, send_one
from courier.sender.queue import SendQueue
from courier.sender.rate_limit import RateLimiter, estimate_send_seconds, format_duration


def test_estimate_and_format() -> None:
    assert estimate_send_seconds(1, 2.0) == 0.0
    assert estimate_send_seconds(3, 2.0) == 4.0
    assert "m" in format_duration(125)


def test_rate_limiter_daily_cap() -> None:
    limiter = RateLimiter(interval_seconds=0.0, daily_cap=2)
    limiter.reset_day_if_needed("2026-01-01")
    assert limiter.can_send()[0]
    limiter.mark_sent()
    limiter.mark_sent()
    ok, msg = limiter.can_send()
    assert not ok
    assert "Daily cap" in msg


def test_build_raw_message_single_recipient() -> None:
    raw = build_raw_message(
        to="user@example.com",
        subject="Hi {{email}}",
        html_body="<p>Hello {{email}}</p>",
        text_body="Hello {{email}}",
        sender_email="me@example.com",
        from_name="Courier",
    )
    assert "raw" in raw
    # Decode enough to ensure To is single address (base64url)
    import base64

    decoded = base64.urlsafe_b64decode(raw["raw"] + "==").decode("utf-8", errors="replace")
    assert "To: user@example.com" in decoded
    assert "Hi user@example.com" in decoded
    # HTML part may be base64-encoded by the email package; check payload too
    assert (
        "Hello user@example.com" in decoded
        or "SGVsbG8gdXNlckBleGFtcGxlLmNvbQ" in decoded  # base64 fragment
    )



def test_send_one_dry_run() -> None:
    service = MagicMock()
    result = send_one(service, {"raw": "abc"}, dry_run=True)
    assert result["dry_run"] is True
    service.users.assert_not_called()


def test_send_one_retries_429() -> None:
    service = MagicMock()
    error = Exception("HttpError 429 rateLimitExceeded")
    ok = {"id": "msg1"}
    service.users.return_value.messages.return_value.send.return_value.execute.side_effect = [
        error,
        ok,
    ]
    result = send_one(service, {"raw": "abc"}, dry_run=False, max_retries=2)
    assert result["id"] == "msg1"


def test_send_one_gives_up() -> None:
    service = MagicMock()
    service.users.return_value.messages.return_value.send.return_value.execute.side_effect = (
        Exception("HttpError 400 badRequest")
    )
    with pytest.raises(SendError):
        send_one(service, {"raw": "abc"}, dry_run=False, max_retries=1)


def test_queue_dry_run() -> None:
    limiter = RateLimiter(interval_seconds=0.0, daily_cap=100)

    def factory() -> Any:
        raise AssertionError("should not build service in dry-run")

    queue = SendQueue(
        service_factory=factory,
        sender_email="me@example.com",
        rate_limiter=limiter,
        dry_run=True,
    )
    results = queue.run(
        ["a@example.com", "b@example.com"],
        subject="Test",
        html_body="<p>Hi</p>",
        text_body="Hi",
    )
    assert len(results) == 2
    assert all(r.status == "sent" for r in results)
