"""Application settings and aggregate state models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from courier.audience.models import AudienceStore
from courier.composer.draft import Draft, Template


@dataclass
class AppSettings:
    theme: str = "dark"  # dark | light | system
    test_audience: list[str] = field(default_factory=list)
    send_interval_seconds: float = 2.0
    daily_cap: int = 400
    default_footer_enabled: bool = True
    default_footer_html: str = (
        '<p style="color:#64748B;font-size:12px;">'
        "You received this email because you are on our list. "
        "Reply with UNSUBSCRIBE to be removed."
        "</p>"
    )
    confirm_destructive: bool = True
    # Send confirmation cannot be disabled; kept for clarity in UI.
    confirm_send: bool = True
    dry_run: bool = False
    data_folder: str = ""
    from_display_name: str = ""
    reply_to: str = ""
    autosave_minutes: int = 2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppSettings:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        # Force confirm_send always true
        filtered["confirm_send"] = True
        return cls(**filtered)


@dataclass
class SendJobState:
    """Resumable mid-send checkpoint."""

    active: bool = False
    job_id: str = ""
    subject: str = ""
    recipients: list[str] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)
    failed: list[dict[str, str]] = field(default_factory=list)
    paused: bool = False
    html_body: str = ""
    text_body: str = ""
    from_name: str = ""
    reply_to: str = ""
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    started_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SendJobState:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class AppState:
    settings: AppSettings = field(default_factory=AppSettings)
    audiences: AudienceStore = field(default_factory=AudienceStore)
    drafts: list[Draft] = field(default_factory=list)
    templates: list[Template] = field(default_factory=list)
    send_job: SendJobState = field(default_factory=SendJobState)
    send_log: list[dict[str, Any]] = field(default_factory=list)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "settings": self.settings.to_dict(),
            "audiences": self.audiences.to_dict(),
            "drafts": [d.to_dict() for d in self.drafts],
            "templates": [t.to_dict() for t in self.templates],
            "send_job": self.send_job.to_dict(),
            "send_log": list(self.send_log),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppState:
        return cls(
            version=int(data.get("version", 1)),
            settings=AppSettings.from_dict(data.get("settings") or {}),
            audiences=AudienceStore.from_dict(data.get("audiences") or {}),
            drafts=[Draft.from_dict(d) for d in data.get("drafts") or []],
            templates=[Template.from_dict(t) for t in data.get("templates") or []],
            send_job=SendJobState.from_dict(data.get("send_job") or {}),
            send_log=list(data.get("send_log") or []),
        )
