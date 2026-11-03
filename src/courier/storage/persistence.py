"""Autosave / restore of application state under the user data directory."""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
from pathlib import Path

from platformdirs import user_data_dir

from courier.branding import APP_ID, BRAND_NAME, PUBLISHER
from courier.storage.config import AppState

logger = logging.getLogger(__name__)

STATE_FILE = "state.json"
BACKUP_FILE = "state.bak.json"


def default_data_dir() -> Path:
    return Path(user_data_dir(BRAND_NAME, PUBLISHER, ensure_exists=True))


class Persistence:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else default_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.data_dir / STATE_FILE
        self.backup_path = self.data_dir / BACKUP_FILE
        self.log_path = self.data_dir / "courier.log"

    def load(self) -> AppState:
        for path in (self.state_path, self.backup_path):
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                state = AppState.from_dict(data)
                if state.settings.data_folder:
                    # Honor configured folder if it still exists
                    custom = Path(state.settings.data_folder)
                    if custom.exists() and custom.resolve() != self.data_dir.resolve():
                        self.set_data_dir(custom)
                        return self.load()
                return state
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                logger.error("Failed to load %s: %s", path.name, type(exc).__name__)
        state = AppState()
        state.audiences.ensure_default()
        return state

    def save(self, state: AppState) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(state.to_dict(), indent=2, ensure_ascii=False)
        # Atomic write
        fd, tmp_name = tempfile.mkstemp(dir=self.data_dir, suffix=".tmp")
        tmp_path = Path(tmp_name)
        try:
            with open(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            if self.state_path.exists():
                shutil.copy2(self.state_path, self.backup_path)
            tmp_path.replace(self.state_path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    def set_data_dir(self, path: Path) -> None:
        self.data_dir = Path(path)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.data_dir / STATE_FILE
        self.backup_path = self.data_dir / BACKUP_FILE
        self.log_path = self.data_dir / "courier.log"

    @property
    def app_id(self) -> str:
        return APP_ID
