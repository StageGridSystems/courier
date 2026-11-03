"""Build and send a single Gmail API message (one recipient in To)."""

from __future__ import annotations

import base64
import mimetypes
import time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from courier.composer.merge import apply_merge_fields
from courier.exceptions import SendError

GMAIL_ATTACHMENT_LIMIT = 25 * 1024 * 1024  # 25 MB message size guideline


def total_attachment_size(paths: list[str]) -> int:
    total = 0
    for p in paths:
        path = Path(p)
        if path.is_file():
            total += path.stat().st_size
    return total


def build_raw_message(
    *,
    to: str,
    subject: str,
    html_body: str,
    text_body: str,
    sender_email: str,
    from_name: str = "",
    reply_to: str = "",
    cc: list[str] | None = None,
    bcc: list[str] | None = None,
    attachments: list[str] | None = None,
    merge_fields: dict[str, str] | None = None,
) -> dict[str, str]:
    """Construct a base64url raw message. Never puts the audience list in headers."""
    fields = {"email": to, **(merge_fields or {})}
    subj = apply_merge_fields(subject, fields)
    html = apply_merge_fields(html_body, fields)
    text = apply_merge_fields(text_body, fields)

    attachments = attachments or []
    size = total_attachment_size(attachments)
    # Rough overhead allowance
    if size > GMAIL_ATTACHMENT_LIMIT - 100_000:
        raise SendError(
            f"Attachments are too large ({size / (1024 * 1024):.1f} MB). "
            "Gmail limits messages to about 25 MB including encoding overhead."
        )

    if attachments:
        root = MIMEMultipart("mixed")
        alt = MIMEMultipart("alternative")
        root.attach(alt)
    else:
        root = MIMEMultipart("alternative")
        alt = root

    if text:
        alt.attach(MIMEText(text, "plain", "utf-8"))
    if html:
        alt.attach(MIMEText(html, "html", "utf-8"))

    for path_str in attachments:
        path = Path(path_str)
        if not path.is_file():
            continue
        ctype, _ = mimetypes.guess_type(str(path))
        maintype, _, subtype = (ctype or "application/octet-stream").partition("/")
        data = path.read_bytes()
        if maintype == "text":
            part = MIMEText(data.decode("utf-8", errors="replace"), _subtype=subtype or "plain")
        else:
            part = MIMEApplication(data, _subtype=subtype or "octet-stream")
        part.add_header("Content-Disposition", "attachment", filename=path.name)
        if attachments:
            root.attach(part)

    if from_name.strip():
        root["From"] = f"{from_name.strip()} <{sender_email}>"
    else:
        root["From"] = sender_email
    root["To"] = to  # single recipient only
    root["Subject"] = subj
    if reply_to.strip():
        root["Reply-To"] = reply_to.strip()
    if cc:
        root["Cc"] = ", ".join(cc)
    if bcc:
        root["Bcc"] = ", ".join(bcc)

    raw = base64.urlsafe_b64encode(root.as_bytes()).decode("ascii")
    return {"raw": raw}


def send_one(
    service: Any,
    raw_message: dict[str, str],
    *,
    dry_run: bool = False,
    max_retries: int = 4,
) -> dict[str, Any]:
    """Send with retries/backoff on 429 and 5xx."""
    if dry_run:
        return {"id": "dry-run", "labelIds": [], "dry_run": True}

    delay = 1.0
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return service.users().messages().send(userId="me", body=raw_message).execute()
        except Exception as exc:  # googleapiclient errors
            last_error = exc
            status = _http_status(exc)
            if status in {429, 500, 502, 503, 504} and attempt < max_retries:
                time.sleep(delay)
                delay = min(delay * 2, 30.0)
                continue
            raise SendError(
                f"Gmail API send failed (HTTP {status or 'n/a'}).",
                detail=str(exc),
            ) from exc
    raise SendError("Gmail API send failed after retries.", detail=str(last_error))


def _http_status(exc: Exception) -> int | None:
    for attr in ("resp", "response"):
        resp = getattr(exc, attr, None)
        if resp is not None and hasattr(resp, "status"):
            try:
                return int(resp.status)
            except (TypeError, ValueError):
                pass
    status = getattr(exc, "status_code", None)
    if status is not None:
        try:
            return int(status)
        except (TypeError, ValueError):
            pass
    # googleapiclient.errors.HttpError string often contains "HttpError 429"
    text = str(exc)
    for code in (429, 500, 502, 503, 504):
        if str(code) in text:
            return code
    return None
