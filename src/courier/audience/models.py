"""Audience list models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from courier.audience.extract import normalize_email, validate_email


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class AudienceList:
    name: str
    emails: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=_utcnow_iso)

    def add(self, emails: list[str]) -> tuple[int, int]:
        """Add emails; return (added, duplicates)."""
        seen = {normalize_email(e) for e in self.emails}
        added = 0
        dupes = 0
        for raw in emails:
            norm = normalize_email(raw)
            if not validate_email(norm):
                continue
            if norm in seen:
                dupes += 1
                continue
            seen.add(norm)
            self.emails.append(norm)
            added += 1
        self.updated_at = _utcnow_iso()
        return added, dupes

    def remove(self, emails: list[str]) -> int:
        remove_set = {normalize_email(e) for e in emails}
        before = len(self.emails)
        self.emails = [e for e in self.emails if e not in remove_set]
        self.updated_at = _utcnow_iso()
        return before - len(self.emails)

    def filtered(self, query: str) -> list[str]:
        q = query.strip().lower()
        if not q:
            return list(self.emails)
        return [e for e in self.emails if q in e]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AudienceList:
        return cls(
            name=str(data.get("name", "Untitled")),
            emails=[normalize_email(e) for e in data.get("emails", []) if validate_email(str(e))],
            updated_at=str(data.get("updated_at") or _utcnow_iso()),
        )


@dataclass
class ImportPreview:
    found: list[str]
    duplicates: list[str]
    invalid_skipped: list[str]

    @property
    def summary(self) -> str:
        return (
            f"{len(self.found)} new, {len(self.duplicates)} duplicates, "
            f"{len(self.invalid_skipped)} invalid skipped"
        )


@dataclass
class AudienceStore:
    lists: list[AudienceList] = field(default_factory=list)
    suppression: list[str] = field(default_factory=list)
    active_list: str = "Default"

    def ensure_default(self) -> AudienceList:
        if not self.lists:
            self.lists.append(AudienceList(name="Default"))
            self.active_list = "Default"
        return self.get(self.active_list) or self.lists[0]

    def get(self, name: str) -> AudienceList | None:
        for item in self.lists:
            if item.name == name:
                return item
        return None

    def get_or_create(self, name: str) -> AudienceList:
        existing = self.get(name)
        if existing:
            return existing
        created = AudienceList(name=name)
        self.lists.append(created)
        return created

    def rename(self, old: str, new: str) -> bool:
        item = self.get(old)
        if not item or self.get(new):
            return False
        item.name = new
        if self.active_list == old:
            self.active_list = new
        return True

    def delete(self, name: str) -> bool:
        if len(self.lists) <= 1:
            return False
        self.lists = [x for x in self.lists if x.name != name]
        if self.active_list == name:
            self.active_list = self.lists[0].name
        return True

    def effective_recipients(self, list_name: str | None = None) -> list[str]:
        target = self.get(list_name or self.active_list) or self.ensure_default()
        suppressed = {normalize_email(e) for e in self.suppression}
        return [e for e in target.emails if e not in suppressed]

    def add_suppression(self, emails: list[str]) -> int:
        seen = {normalize_email(e) for e in self.suppression}
        added = 0
        for raw in emails:
            norm = normalize_email(raw)
            if validate_email(norm) and norm not in seen:
                seen.add(norm)
                self.suppression.append(norm)
                added += 1
        return added

    def to_dict(self) -> dict[str, Any]:
        return {
            "lists": [x.to_dict() for x in self.lists],
            "suppression": list(self.suppression),
            "active_list": self.active_list,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AudienceStore:
        store = cls(
            lists=[AudienceList.from_dict(x) for x in data.get("lists", [])],
            suppression=[
                normalize_email(e)
                for e in data.get("suppression", [])
                if validate_email(str(e))
            ],
            active_list=str(data.get("active_list") or "Default"),
        )
        store.ensure_default()
        return store
