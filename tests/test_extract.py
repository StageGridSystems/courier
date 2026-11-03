"""Tests for audience email extraction."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from courier.audience.extract import (
    extract_emails_from_file,
    extract_emails_from_text,
    validate_email,
)


def test_validate_email() -> None:
    assert validate_email("a@b.co")
    assert validate_email("Name <user@example.com>") is False  # full form not bare
    assert validate_email("user@example.com")
    assert not validate_email("not-an-email")
    assert not validate_email("a@b")
    assert not validate_email(".user@example.com")


def test_extract_from_blob() -> None:
    text = """
    Hello Alice <alice@example.com>, and bob@Example.COM
    also carol@test.org;dave@test.org/erin@test.org
    junk@@@invalid and Name <frank@stagegrid.example>
    """
    result = extract_emails_from_text(text)
    assert "alice@example.com" in result.found
    assert "bob@example.com" in result.found
    assert "carol@test.org" in result.found
    assert "dave@test.org" in result.found
    assert "erin@test.org" in result.found
    assert "frank@stagegrid.example" in result.found
    # duplicate case
    again = extract_emails_from_text("bob@example.com", existing=set(result.found))
    assert again.duplicates == ["bob@example.com"]
    assert again.found == []


def test_extract_workbook_every_cell(tmp_path: Path) -> None:
    path = tmp_path / "book.xlsx"
    wb = Workbook()
    ws1 = wb.active
    ws1.title = "A"
    ws1["A1"] = "hello"
    ws1["B2"] = "one@example.com, two@example.com"
    ws2 = wb.create_sheet("B")
    ws2["C3"] = "Name <three@example.com>"
    ws2["D4"] = "bad@@"
    wb.save(path)
    result = extract_emails_from_file(path)
    assert set(result.found) == {
        "one@example.com",
        "two@example.com",
        "three@example.com",
    }


def test_extract_csv(tmp_path: Path) -> None:
    path = tmp_path / "list.csv"
    path.write_text("name,email\nAda,ada@example.com\n", encoding="utf-8")
    result = extract_emails_from_file(path)
    assert result.found == ["ada@example.com"]
