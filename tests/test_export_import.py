"""Tests for config export/import and auth encryption."""

from __future__ import annotations

from pathlib import Path

import pytest

from courier.audience.models import AudienceList, AudienceStore
from courier.exceptions import ConfigError
from courier.storage.config import AppSettings, AppState
from courier.storage.export_import import (
    decrypt_blob,
    encrypt_blob,
    export_config,
    import_config_optional_auth,
)


def test_encrypt_roundtrip() -> None:
    blob = encrypt_blob({"token": {"refresh_token": "secret"}}, "correct horse")
    data = decrypt_blob(blob, "correct horse")
    assert data["token"]["refresh_token"] == "secret"
    with pytest.raises(ConfigError):
        decrypt_blob(blob, "wrong")


def test_export_import_without_auth(tmp_path: Path) -> None:
    state = AppState(
        settings=AppSettings(daily_cap=123, theme="light"),
        audiences=AudienceStore(
            lists=[AudienceList(name="VIP", emails=["a@example.com"])],
            active_list="VIP",
        ),
    )
    path = tmp_path / "cfg.json"
    export_config(state, path, include_auth=False)
    loaded, auth = import_config_optional_auth(path, load_auth=False)
    assert auth is None
    assert loaded.settings.daily_cap == 123
    assert loaded.settings.theme == "light"
    assert loaded.audiences.get("VIP") is not None
    assert loaded.audiences.get("VIP").emails == ["a@example.com"]  # type: ignore[union-attr]


def test_export_import_with_auth(tmp_path: Path) -> None:
    state = AppState()
    path = tmp_path / "cfg-auth.json"
    secrets = {"token": {"token": "x"}, "client": {"client_id": "cid"}}
    export_config(
        state,
        path,
        include_auth=True,
        auth_secrets=secrets,
        password="pw-test-123",
    )
    loaded, auth = import_config_optional_auth(
        path, password="pw-test-123", load_auth=True
    )
    assert loaded is not None
    assert auth is not None
    assert auth["client"]["client_id"] == "cid"


def test_export_auth_requires_password(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        export_config(
            AppState(),
            tmp_path / "x.json",
            include_auth=True,
            auth_secrets={"token": {}},
            password=None,
        )
