"""Robust email extraction from free text and spreadsheet cells."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Name <email> (name must not contain @ so bare addresses are not swallowed)
ANGLE_EMAIL_RE = re.compile(
    r"(?:\"[^\"]{0,120}\"|'[^']{0,120}'|[^@<,\n;]{0,80})\s*<\s*"
    r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})"
    r"\s*>"
)

# Bare addresses (also used inside multi-email cells)
BARE_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)

# Split multi-email cells
SPLIT_RE = re.compile(r"[,;\s/\n\r|]+")

LOCAL_INVALID = re.compile(r"^\.|\.$|\.\.")


@dataclass
class ExtractionResult:
    found: list[str] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)
    invalid_skipped: list[str] = field(default_factory=list)

    @property
    def unique(self) -> list[str]:
        return list(self.found)


def normalize_email(value: str) -> str:
    return value.strip().lower()


def validate_email(value: str) -> bool:
    """Validate a single email address after normalization."""
    email = normalize_email(value)
    if not email or "@" not in email or len(email) > 254:
        return False
    local, _, domain = email.partition("@")
    if not local or not domain or "." not in domain:
        return False
    if LOCAL_INVALID.search(local):
        return False
    if domain.startswith(".") or domain.endswith(".") or ".." in domain:
        return False
    # Reject obvious non-emails that regex may still catch
    if email.endswith(".") or email.startswith("."):
        return False
    label = domain.rsplit(".", 1)[-1]
    if not label.isalpha() or len(label) < 2:
        return False
    return bool(
        re.fullmatch(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", email)
    )


def _candidates_from_blob(text: str) -> list[str]:
    results: list[str] = []
    seen_spans: list[tuple[int, int]] = []
    for match in ANGLE_EMAIL_RE.finditer(text or ""):
        addr = match.group(1)
        if addr:
            results.append(addr)
            seen_spans.append(match.span(1))
    for match in BARE_EMAIL_RE.finditer(text or ""):
        span = match.span()
        if any(span[0] >= s[0] and span[1] <= s[1] for s in seen_spans):
            continue
        results.append(match.group(0))
    return results


def extract_emails_from_text(text: str, *, existing: set[str] | None = None) -> ExtractionResult:
    """Extract valid emails from arbitrary text; merge case-insensitive duplicates."""
    seen: set[str] = set(existing or ())
    result = ExtractionResult()
    for raw in _candidates_from_blob(text or ""):
        norm = normalize_email(raw)
        if not validate_email(norm):
            result.invalid_skipped.append(raw)
            continue
        if norm in seen:
            result.duplicates.append(norm)
            continue
        seen.add(norm)
        result.found.append(norm)
    return result


def _cell_to_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def extract_emails_from_cells(cells: list[str], *, existing: set[str] | None = None) -> ExtractionResult:
    blob = "\n".join(_cell_to_str(c) for c in cells)
    return extract_emails_from_text(blob, existing=existing)


def extract_emails_from_csv(path: Path, *, existing: set[str] | None = None) -> ExtractionResult:
    cells: list[str] = []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.reader(fh)
        for row in reader:
            cells.extend(row)
    return extract_emails_from_cells(cells, existing=existing)


def extract_emails_from_txt(path: Path, *, existing: set[str] | None = None) -> ExtractionResult:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    return extract_emails_from_text(text, existing=existing)


def extract_emails_from_workbook(path: Path, *, existing: set[str] | None = None) -> ExtractionResult:
    """Scan every cell of every sheet in XLSX/XLS."""
    suffix = path.suffix.lower()
    cells: list[str] = []
    if suffix == ".xlsx":
        from openpyxl import load_workbook

        wb = load_workbook(path, read_only=True, data_only=True)
        try:
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    for value in row:
                        if value is not None:
                            cells.append(_cell_to_str(value))
        finally:
            wb.close()
    elif suffix == ".xls":
        import xlrd

        book = xlrd.open_workbook(str(path))
        for sheet in book.sheets():
            for r in range(sheet.nrows):
                for c in range(sheet.ncols):
                    cells.append(_cell_to_str(sheet.cell_value(r, c)))
    else:
        raise ValueError(f"Unsupported spreadsheet type: {suffix}")
    return extract_emails_from_cells(cells, existing=existing)


def extract_emails_from_file(path: Path, *, existing: set[str] | None = None) -> ExtractionResult:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return extract_emails_from_csv(path, existing=existing)
    if suffix in {".xlsx", ".xls"}:
        return extract_emails_from_workbook(path, existing=existing)
    if suffix in {".txt", ".text", ".md", ".log"}:
        return extract_emails_from_txt(path, existing=existing)
    # Fallback: treat as text
    return extract_emails_from_txt(path, existing=existing)
