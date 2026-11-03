"""Tests for merge fields and HTML-to-text."""

from __future__ import annotations

from courier.composer.html_text import html_to_plain_text
from courier.composer.merge import apply_merge_fields


def test_merge_fields() -> None:
    out = apply_merge_fields("Hello {{ email }}, id={{missing}}", {"email": "a@b.co"})
    assert out == "Hello a@b.co, id="


def test_html_to_text() -> None:
    text = html_to_plain_text("<p>Hello <b>world</b></p><script>x()</script><p>Line2</p>")
    assert "Hello world" in text
    assert "Line2" in text
    assert "x()" not in text
