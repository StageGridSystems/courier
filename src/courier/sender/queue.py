"""Background-friendly send queue with pause/resume/cancel and resume state."""

from __future__ import annotations

import csv
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from courier.sender.gmail_send import build_raw_message, send_one
from courier.sender.rate_limit import RateLimiter


@dataclass
class SendResult:
    email: str
    status: str  # sent | failed | skipped | cancelled
    detail: str = ""
    at: str = field(default_factory=lambda: datetime.now(UTC).replace(microsecond=0).isoformat())


ProgressCallback = Callable[[int, int, SendResult], None]
CheckpointCallback = Callable[[dict[str, Any]], None]


class SendQueue:
    """
    Sequential one-recipient-at-a-time sender.

    Thread-safe control flags for pause / resume / cancel.
    Designed to run inside a worker thread; callbacks must be thread-safe or marshalled to UI.
    """

    def __init__(
        self,
        *,
        service_factory: Callable[[], Any],
        sender_email: str,
        rate_limiter: RateLimiter,
        dry_run: bool = False,
    ) -> None:
        self.service_factory = service_factory
        self.sender_email = sender_email
        self.rate_limiter = rate_limiter
        self.dry_run = dry_run
        self._pause = threading.Event()
        self._pause.set()  # not paused
        self._cancel = threading.Event()
        self.results: list[SendResult] = []
        self._sending = False

    @property
    def is_sending(self) -> bool:
        return self._sending

    def pause(self) -> None:
        self._pause.clear()

    def resume(self) -> None:
        self._pause.set()

    def cancel(self) -> None:
        self._cancel.set()
        self._pause.set()

    def reset_controls(self) -> None:
        self._cancel.clear()
        self._pause.set()

    def run(
        self,
        recipients: list[str],
        *,
        subject: str,
        html_body: str,
        text_body: str,
        from_name: str = "",
        reply_to: str = "",
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        attachments: list[str] | None = None,
        already_completed: list[str] | None = None,
        on_progress: ProgressCallback | None = None,
        on_checkpoint: CheckpointCallback | None = None,
        job_id: str | None = None,
    ) -> list[SendResult]:
        self.reset_controls()
        self._sending = True
        self.results = []
        done = {e.lower() for e in (already_completed or [])}
        pending = [e for e in recipients if e.lower() not in done]
        total = len(recipients)
        completed_count = len(done)
        jid = job_id or uuid4().hex
        day_key = datetime.now(UTC).strftime("%Y-%m-%d")
        self.rate_limiter.reset_day_if_needed(day_key)

        try:
            service = None if self.dry_run else self.service_factory()
            for email in pending:
                while not self._pause.is_set():
                    if self._cancel.is_set():
                        break
                    time.sleep(0.1)
                if self._cancel.is_set():
                    result = SendResult(email=email, status="cancelled", detail="Cancelled by user")
                    self.results.append(result)
                    if on_progress:
                        on_progress(completed_count, total, result)
                    break

                ok, reason = self.rate_limiter.can_send()
                if not ok:
                    result = SendResult(email=email, status="skipped", detail=reason)
                    self.results.append(result)
                    if on_progress:
                        on_progress(completed_count, total, result)
                    # Stop further sends when daily cap hit
                    break

                wait = self.rate_limiter.wait_seconds()
                end_wait = time.monotonic() + wait
                while time.monotonic() < end_wait:
                    if self._cancel.is_set():
                        break
                    while not self._pause.is_set():
                        if self._cancel.is_set():
                            break
                        time.sleep(0.1)
                    time.sleep(0.05)
                if self._cancel.is_set():
                    result = SendResult(email=email, status="cancelled", detail="Cancelled by user")
                    self.results.append(result)
                    if on_progress:
                        on_progress(completed_count, total, result)
                    break

                try:
                    raw = build_raw_message(
                        to=email,
                        subject=subject,
                        html_body=html_body,
                        text_body=text_body,
                        sender_email=self.sender_email,
                        from_name=from_name,
                        reply_to=reply_to,
                        cc=cc,
                        bcc=bcc,
                        attachments=attachments,
                        merge_fields={"email": email},
                    )
                    send_one(service, raw, dry_run=self.dry_run)
                    self.rate_limiter.mark_sent()
                    result = SendResult(email=email, status="sent", detail="OK")
                    completed_count += 1
                    done.add(email.lower())
                except Exception as exc:
                    result = SendResult(email=email, status="failed", detail=str(exc))
                    completed_count += 1

                self.results.append(result)
                if on_progress:
                    on_progress(completed_count, total, result)
                if on_checkpoint:
                    on_checkpoint(
                        {
                            "job_id": jid,
                            "completed": sorted(done),
                            "last": result.email,
                            "status": result.status,
                        }
                    )
        finally:
            self._sending = False
        return self.results


def export_results_csv(results: list[SendResult], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["email", "status", "detail", "at"])
        writer.writeheader()
        for r in results:
            writer.writerow(
                {"email": r.email, "status": r.status, "detail": r.detail, "at": r.at}
            )
