"""Gmail OAuth 2.0 (installed desktop app) with gmail.send scope."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from courier.auth.token_store import TokenStore
from courier.branding import SCOPES
from courier.exceptions import AuthError

logger = logging.getLogger(__name__)


@dataclass
class ClientCredentials:
    client_id: str
    client_secret: str
    project_id: str = ""
    auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    token_uri: str = "https://oauth2.googleapis.com/token"
    redirect_uris: list[str] | None = None

    def to_installed_dict(self) -> dict[str, Any]:
        return {
            "installed": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "project_id": self.project_id,
                "auth_uri": self.auth_uri,
                "token_uri": self.token_uri,
                "redirect_uris": self.redirect_uris
                or ["http://localhost"],
            }
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClientCredentials:
        installed = data.get("installed") or data.get("web") or data
        return cls(
            client_id=str(installed.get("client_id", "")),
            client_secret=str(installed.get("client_secret", "")),
            project_id=str(installed.get("project_id", "")),
            auth_uri=str(
                installed.get("auth_uri", "https://accounts.google.com/o/oauth2/auth")
            ),
            token_uri=str(
                installed.get("token_uri", "https://oauth2.googleapis.com/token")
            ),
            redirect_uris=list(installed.get("redirect_uris") or ["http://localhost"]),
        )


def classify_client_json(path: Path) -> tuple[str, str | None]:
    """
    Classify a client secret JSON file.

    Returns (kind, error_message).
    kind is one of: desktop, web, service_account, unknown
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return "unknown", f"Could not read JSON: {exc}"

    if not isinstance(data, dict):
        return "unknown", "File is not a JSON object."

    if data.get("type") == "service_account" or "private_key" in data:
        return (
            "service_account",
            "This looks like a service account key. Service accounts need Google Workspace "
            "domain-wide delegation and cannot use the simple installed-app OAuth flow. "
            "Create an OAuth client of type Desktop app in Google Cloud Console, download "
            "that JSON, and connect it here instead.",
        )

    if "installed" in data:
        installed = data["installed"]
        if isinstance(installed, dict) and installed.get("client_id"):
            return "desktop", None
        return "unknown", "installed block is missing client_id."

    if "web" in data:
        return (
            "web",
            "This is a Web application OAuth client. Courier needs a Desktop app client "
            "(installed). In Google Cloud Console create credentials of type Desktop app "
            "and download that JSON.",
        )

    if data.get("client_id") and data.get("client_secret"):
        return "desktop", None

    return (
        "unknown",
        "Unrecognized client JSON. Expected a Desktop OAuth client secret file "
        "with an 'installed' block containing client_id and client_secret.",
    )


class AuthManager:
    def __init__(self, token_store: TokenStore) -> None:
        self.token_store = token_store
        self._creds: Credentials | None = None
        self._email: str | None = None

    @property
    def email(self) -> str | None:
        return self._email

    @property
    def is_connected(self) -> bool:
        return bool(self._creds and self._creds.valid)

    def load_saved(self) -> bool:
        client = self.token_store.load_client()
        token = self.token_store.load_token()
        if not client or not token:
            return False
        try:
            self._creds = Credentials.from_authorized_user_info(token, SCOPES)
            if self._creds and self._creds.expired and self._creds.refresh_token:
                self._creds.refresh(Request())
                self._persist_creds()
            if self._creds and self._creds.valid:
                self._email = self._fetch_email()
                return True
        except Exception as exc:
            logger.warning("Could not restore credentials: %s", type(exc).__name__)
        return False

    def set_client(self, client: ClientCredentials) -> None:
        if not client.client_id or not client.client_secret:
            raise AuthError("Client ID and Client Secret are required.")
        self.token_store.save_client(client.to_dict())

    def load_client_from_file(self, path: Path) -> ClientCredentials:
        kind, err = classify_client_json(path)
        if err:
            raise AuthError(err)
        if kind != "desktop":
            raise AuthError(err or "Unsupported client type.")
        data = json.loads(path.read_text(encoding="utf-8"))
        client = ClientCredentials.from_dict(data)
        self.set_client(client)
        return client

    def set_client_manual(
        self, client_id: str, client_secret: str, project_id: str = ""
    ) -> ClientCredentials:
        client = ClientCredentials(
            client_id=client_id.strip(),
            client_secret=client_secret.strip(),
            project_id=project_id.strip(),
        )
        self.set_client(client)
        return client

    def run_oauth_flow(self, *, port: int = 0) -> str:
        client_data = self.token_store.load_client()
        if not client_data:
            raise AuthError("Load a Desktop OAuth client JSON (or enter credentials) first.")
        client = ClientCredentials.from_dict(client_data)
        flow = InstalledAppFlow.from_client_config(client.to_installed_dict(), SCOPES)
        try:
            creds = flow.run_local_server(
                port=port,
                prompt="consent",
                authorization_prompt_message="",
                success_message="Courier is connected. You can close this browser tab.",
                open_browser=True,
            )
        except Exception as exc:
            raise AuthError(
                "OAuth sign-in failed. Check that the OAuth consent screen includes you "
                "as a test user and that Gmail API is enabled.",
                detail=str(exc),
            ) from exc
        self._creds = creds
        self._persist_creds()
        self._email = self._fetch_email()
        if not self._email:
            raise AuthError("Signed in, but could not read the account email.")
        return self._email

    def _persist_creds(self) -> None:
        if not self._creds:
            return
        self.token_store.save_token(json.loads(self._creds.to_json()))

    def _fetch_email(self) -> str | None:
        if not self._creds or not self._creds.valid:
            return None
        try:
            service = build("oauth2", "v2", credentials=self._creds, cache_discovery=False)
            info = service.userinfo().get().execute()
            return str(info.get("email") or "") or None
        except Exception as exc:
            logger.warning("userinfo failed: %s", type(exc).__name__)
            return None

    def credentials(self) -> Credentials:
        if not self._creds or not self._creds.valid:
            if self._creds and self._creds.expired and self._creds.refresh_token:
                try:
                    self._creds.refresh(Request())
                    self._persist_creds()
                except Exception as exc:
                    raise AuthError("Token expired. Sign in again.", detail=str(exc)) from exc
        if not self._creds or not self._creds.valid:
            raise AuthError("Not connected. Sign in with Google first.")
        return self._creds

    def status(self) -> dict[str, Any]:
        valid = bool(self._creds and self._creds.valid)
        return {
            "connected": valid,
            "email": self._email,
            "has_client": bool(self.token_store.load_client()),
            "token_valid": valid,
        }

    def sign_out(self) -> None:
        self._creds = None
        self._email = None
        self.token_store.clear_token()

    def build_gmail_service(self) -> Any:
        return build("gmail", "v1", credentials=self.credentials(), cache_discovery=False)
