"""Main application window."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from courier.auth.oauth import AuthManager
from courier.auth.token_store import TokenStore
from courier.branding import BRAND_NAME, PUBLISHER, TAGLINE
from courier.storage.config import AppState
from courier.storage.persistence import Persistence
from courier.ui.tabs.audience_tab import AudienceTab
from courier.ui.tabs.auth_tab import AuthTab
from courier.ui.tabs.compose_tab import ComposeTab
from courier.ui.tabs.guide_tab import GuideTab
from courier.ui.tabs.settings_tab import SettingsTab
from courier.ui.theme import stylesheet

logger = logging.getLogger(__name__)


def _icon_path() -> Path:
    return Path(__file__).resolve().parent.parent / "resources" / "icons" / "courier.svg"


class MainWindow(QMainWindow):
    def __init__(
        self,
        state: AppState,
        persistence: Persistence,
        auth: AuthManager,
        token_store: TokenStore,
    ) -> None:
        super().__init__()
        self.state = state
        self.persistence = persistence
        self.auth = auth
        self.token_store = token_store

        self.setWindowTitle(f"{BRAND_NAME} · {PUBLISHER}")
        self.resize(1100, 760)
        icon = _icon_path()
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        brand_col = QVBoxLayout()
        brand = QLabel(BRAND_NAME)
        brand.setObjectName("brandTitle")
        brand_col.addWidget(brand)
        sub = QLabel(f"{PUBLISHER} · {TAGLINE}")
        sub.setObjectName("mutedLabel")
        brand_col.addWidget(sub)
        header.addLayout(brand_col)
        header.addStretch()
        self.account_badge = QLabel("Not signed in")
        self.account_badge.setObjectName("mutedLabel")
        header.addWidget(self.account_badge, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.auth_tab = AuthTab(auth)
        self.audience_tab = AudienceTab(state.audiences)
        self.compose_tab = ComposeTab(state, auth)
        self.settings_tab = SettingsTab(state, persistence, token_store)
        self.guide_tab = GuideTab()
        self.tabs.addTab(self.auth_tab, "Authentication")
        self.tabs.addTab(self.audience_tab, "Audience")
        self.tabs.addTab(self.compose_tab, "Compose / Send")
        self.tabs.addTab(self.settings_tab, "Settings")
        self.tabs.addTab(self.guide_tab, "How-to guide")
        layout.addWidget(self.tabs)

        self.auth_tab.status_changed.connect(self._refresh_account_badge)
        self.audience_tab.changed.connect(self._autosave)
        self.compose_tab.state_changed.connect(self._autosave)
        self.settings_tab.changed.connect(self._autosave)
        self.settings_tab.theme_changed.connect(self.apply_theme)
        self.settings_tab.data_dir_changed.connect(self._on_data_dir)
        self.settings_tab.state_imported.connect(self._on_imported)

        self.apply_theme(state.settings.theme)
        self._refresh_account_badge()

        self._fade = QPropertyAnimation(self, b"windowOpacity")
        self._fade.setDuration(280)
        self._fade.setStartValue(0.0)
        self._fade.setEndValue(1.0)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setWindowOpacity(0.0)
        QTimer.singleShot(0, self._fade.start)

        self._autosave_timer = QTimer(self)
        minutes = max(1, int(state.settings.autosave_minutes or 2))
        self._autosave_timer.setInterval(minutes * 60 * 1000)
        self._autosave_timer.timeout.connect(self._autosave)
        self._autosave_timer.start()

    def apply_theme(self, theme: str) -> None:
        self.state.settings.theme = theme
        self.setStyleSheet(stylesheet(theme))

    def _refresh_account_badge(self) -> None:
        st = self.auth.status()
        if st["connected"]:
            self.account_badge.setText(f"Signed in as {st['email']}")
        else:
            self.account_badge.setText("Not signed in")

    def _autosave(self) -> None:
        try:
            self.persistence.save(self.state)
        except Exception:
            logger.exception("Autosave failed")

    def _on_data_dir(self, path: str) -> None:
        self.persistence.set_data_dir(Path(path))
        self._autosave()

    def _on_imported(self, state: object) -> None:
        if not isinstance(state, AppState):
            return
        self.state = state
        self.audience_tab.bind_store(state.audiences)
        self.compose_tab.bind_state(state)
        self.settings_tab.bind_state(state)
        self.apply_theme(state.settings.theme)
        self._autosave()
        self.auth.load_saved()
        self._refresh_account_badge()

    def closeEvent(self, event: object) -> None:  # type: ignore[override]
        if self.compose_tab._send_lock:  # noqa: SLF001
            reply = QMessageBox.question(
                self,
                "Send in progress",
                "A send job is running. Quit anyway? Progress will be saved for resume.",
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()  # type: ignore[union-attr]
                return
            if self.compose_tab._queue:  # noqa: SLF001
                self.compose_tab._queue.cancel()  # noqa: SLF001
        self._autosave()
        event.accept()  # type: ignore[union-attr]
