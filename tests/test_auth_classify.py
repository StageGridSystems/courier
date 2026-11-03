"""Tests for OAuth client JSON classification."""

from __future__ import annotations

import json
from pathlib import Path

from courier.auth.oauth import classify_client_json


def test_desktop_ok(tmp_path: Path) -> None:
    path = tmp_path / "client.json"
    path.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "abc.apps.googleusercontent.com",
                    "client_secret": "secret",
                    "project_id": "demo",
                }
            }
        ),
        encoding="utf-8",
    )
    kind, err = classify_client_json(path)
    assert kind == "desktop"
    assert err is None


def test_service_account_rejected(tmp_path: Path) -> None:
    path = tmp_path / "sa.json"
    path.write_text(
        json.dumps(
            {
                "type": "service_account",
                "private_key": "-----BEGIN PRIVATE KEY-----\nX\n-----END PRIVATE KEY-----\n",
                "client_email": "x@y.iam.gserviceaccount.com",
            }
        ),
        encoding="utf-8",
    )
    kind, err = classify_client_json(path)
    assert kind == "service_account"
    assert err is not None
    assert "Desktop" in err


def test_web_rejected(tmp_path: Path) -> None:
    path = tmp_path / "web.json"
    path.write_text(
        json.dumps({"web": {"client_id": "x", "client_secret": "y"}}),
        encoding="utf-8",
    )
    kind, err = classify_client_json(path)
    assert kind == "web"
    assert err is not None
