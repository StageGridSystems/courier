"""Draft and template models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class Draft:
    id: str = field(default_factory=lambda: uuid4().hex)
    name: str = "Untitled draft"
    subject: str = ""
    html_body: str = ""
    text_body: str = ""
    from_name: str = ""
    reply_to: str = ""
    cc: list[str] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)
    attachments: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=_utcnow_iso)

    def touch(self) -> None:
        self.updated_at = _utcnow_iso()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Draft:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class Template:
    id: str = field(default_factory=lambda: uuid4().hex)
    name: str = "Untitled template"
    subject: str = ""
    html_body: str = ""
    text_body: str = ""
    updated_at: str = field(default_factory=_utcnow_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Template:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})
