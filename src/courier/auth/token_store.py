"""Secure token storage via OS keyring with encrypted-file fallback."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from courier.branding import APP_ID

logger = logging.getLogger(__name__)

SERVICE_NAME = APP_ID
TOKEN_KEY = "oauth_token"
CLIENT_KEY = "oauth_client"
FERNET_KEY_NAME = "file_fallback_key"


class TokenStore:
    """Store secrets in the OS keyring; fall back to an encrypted local file."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._fallback_path = self.data_dir / "secrets.enc"
        self._key_path = self.data_dir / ".fallback.key"
        self._use_keyring = self._probe_keyring()

    def _probe_keyring(self) -> bool:
        try:
            import keyring

            keyring.get_password(SERVICE_NAME, "__probe__")
            return True
        except Exception:
            logger.info("Keyring unavailable; using encrypted file fallback")
            return False

    def _fernet(self) -> Fernet:
        if self._key_path.exists():
            key = self._key_path.read_bytes().strip()
        else:
            key = Fernet.generate_key()
            self._key_path.write_bytes(key)
            try:
                self._key_path.chmod(0o600)
            except OSError:
                pass
        return Fernet(key)

    def _set(self, name: str, value: str | None) -> None:
        if self._use_keyring:
            try:
                import keyring

                if value is None:
                    try:
                        keyring.delete_password(SERVICE_NAME, name)
                    except Exception:
                        pass
                else:
                    keyring.set_password(SERVICE_NAME, name, value)
                return
            except Exception:
                logger.warning("Keyring write failed; switching to file fallback")
                self._use_keyring = False
        self._set_file(name, value)

    def _get(self, name: str) -> str | None:
        if self._use_keyring:
            try:
                import keyring

                return keyring.get_password(SERVICE_NAME, name)
            except Exception:
                self._use_keyring = False
        return self._get_file(name)

    def _load_file_map(self) -> dict[str, str]:
        if not self._fallback_path.exists():
            return {}
        try:
            raw = self._fernet().decrypt(self._fallback_path.read_bytes())
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except (InvalidToken, json.JSONDecodeError, OSError) as exc:
            logger.error("Could not read encrypted secrets file: %s", type(exc).__name__)
        return {}

    def _save_file_map(self, data: dict[str, str]) -> None:
        payload = self._fernet().encrypt(json.dumps(data).encode("utf-8"))
        self._fallback_path.write_bytes(payload)
        try:
            self._fallback_path.chmod(0o600)
        except OSError:
            pass

    def _set_file(self, name: str, value: str | None) -> None:
        data = self._load_file_map()
        if value is None:
            data.pop(name, None)
        else:
            data[name] = value
        self._save_file_map(data)

    def _get_file(self, name: str) -> str | None:
        return self._load_file_map().get(name)

    def save_token(self, token_info: dict[str, Any]) -> None:
        # Never log token contents
        self._set(TOKEN_KEY, json.dumps(token_info))

    def load_token(self) -> dict[str, Any] | None:
        raw = self._get(TOKEN_KEY)
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    def clear_token(self) -> None:
        self._set(TOKEN_KEY, None)

    def save_client(self, client_info: dict[str, Any]) -> None:
        self._set(CLIENT_KEY, json.dumps(client_info))

    def load_client(self) -> dict[str, Any] | None:
        raw = self._get(CLIENT_KEY)
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None

    def clear_client(self) -> None:
        self._set(CLIENT_KEY, None)

    def clear_all(self) -> None:
        self.clear_token()
        self.clear_client()

    def export_secrets(self) -> dict[str, Any]:
        return {
            "token": self.load_token(),
            "client": self.load_client(),
        }

    def import_secrets(self, data: dict[str, Any]) -> None:
        if data.get("token"):
            self.save_token(data["token"])
        if data.get("client"):
            self.save_client(data["client"])
