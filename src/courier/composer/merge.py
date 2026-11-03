"""Simple merge-field substitution."""

from __future__ import annotations

import re

FIELD_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")


def apply_merge_fields(template: str, fields: dict[str, str]) -> str:
    """Replace {{name}} tokens; unknown fields become empty string."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(fields.get(key, ""))

    return FIELD_RE.sub(repl, template or "")
