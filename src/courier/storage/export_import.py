"""Full configuration export/import with optional encrypted auth payload."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from courier.exceptions import ConfigError
from courier.storage.config import AppState

EXPORT_VERSION = 1
KDF_ITERATIONS = 390_000


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt_blob(data: dict[str, Any], password: str) -> dict[str, str]:
    if not password:
        raise ConfigError("A password is required to include auth credentials.")
    salt = os.urandom(16)
    fernet = Fernet(_derive_key(password, salt))
    token = fernet.encrypt(json.dumps(data).encode("utf-8"))
    return {
        "salt": base64.urlsafe_b64encode(salt).decode("ascii"),
        "payload": token.decode("ascii"),
    }


def decrypt_blob(blob: dict[str, str], password: str) -> dict[str, Any]:
    try:
        salt = base64.urlsafe_b64decode(blob["salt"].encode("ascii"))
        fernet = Fernet(_derive_key(password, salt))
        raw = fernet.decrypt(blob["payload"].encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise ConfigError("Decrypted auth payload is invalid.")
        return data
    except (KeyError, InvalidToken, json.JSONDecodeError, ValueError) as exc:
        raise ConfigError(
            "Could not decrypt auth data. Check the password.",
            detail=str(exc),
        ) from exc


def export_config(
    state: AppState,
    path: Path,
    *,
    include_auth: bool = False,
    auth_secrets: dict[str, Any] | None = None,
    password: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "courier_export_version": EXPORT_VERSION,
        "include_auth": bool(include_auth),
        "state": state.to_dict(),
    }
    if include_auth:
        if not password:
            raise ConfigError("Password required when including auth credentials.")
        if not auth_secrets:
            raise ConfigError("No auth secrets available to export.")
        payload["auth_encrypted"] = encrypt_blob(auth_secrets, password)
        payload["auth_warning"] = (
            "This file contains encrypted OAuth client secrets and tokens. "
            "Keep the password safe. Anyone with both can send as your account."
        )
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def import_config(
    path: Path,
    *,
    password: str | None = None,
) -> tuple[AppState, dict[str, Any] | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Could not read config file: {exc}") from exc

    if not isinstance(data, dict) or "state" not in data:
        raise ConfigError("Not a Courier configuration export.")

    state = AppState.from_dict(data["state"])
    auth: dict[str, Any] | None = None
    if data.get("include_auth") and data.get("auth_encrypted"):
        if not password:
            raise ConfigError(
                "This export includes encrypted auth. Enter the password to import it, "
                "or import without auth by leaving the password empty and stripping auth."
            )
        auth = decrypt_blob(data["auth_encrypted"], password)
    return state, auth


def import_config_optional_auth(
    path: Path,
    *,
    password: str | None = None,
    load_auth: bool = False,
) -> tuple[AppState, dict[str, Any] | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Could not read config file: {exc}") from exc
    if not isinstance(data, dict) or "state" not in data:
        raise ConfigError("Not a Courier configuration export.")
    state = AppState.from_dict(data["state"])
    auth = None
    if load_auth and data.get("auth_encrypted"):
        if not password:
            raise ConfigError("Password required to import auth credentials.")
        auth = decrypt_blob(data["auth_encrypted"], password)
    return state, auth
