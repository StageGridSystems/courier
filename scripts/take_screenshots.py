#!/usr/bin/env python3
"""Capture offscreen screenshots of each main tab for docs/screenshots."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Prefer offscreen Qt before importing Qt
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QTimer, Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from courier.auth.oauth import AuthManager  # noqa: E402
from courier.auth.token_store import TokenStore  # noqa: E402
from courier.storage.persistence import Persistence  # noqa: E402
from courier.ui.main_window import MainWindow  # noqa: E402


def main() -> int:
    out = ROOT / "docs" / "screenshots"
    out.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Isolated temp data so screenshots do not touch the user profile
    data = ROOT / ".screenshot-data"
    data.mkdir(exist_ok=True)
    persistence = Persistence(data)
    token_store = TokenStore(data)
    auth = AuthManager(token_store)
    state = persistence.load()
    state.settings.theme = "dark"
    state.audiences.ensure_default()
    state.audiences.lists[0].add(
        ["alice@example.com", "bob@example.com", "carol@example.com"]
    )
    state.settings.test_audience = ["admin@example.com"]

    window = MainWindow(state, persistence, auth, token_store)
    window.resize(1100, 760)
    window.show()

    names = [
        "01-authentication",
        "02-audience",
        "03-compose",
        "04-settings",
        "05-guide",
    ]

    def capture(index: int) -> None:
        if index >= window.tabs.count():
            app.quit()
            return
        window.tabs.setCurrentIndex(index)
        # Seed compose content for a nicer shot
        if index == 2:
            window.compose_tab.subject.setText("March product update")
            window.compose_tab.html_edit.setPlainText(
                "<h2>Hello {{email}}</h2><p>Here is what is new this month.</p>"
            )
            window.compose_tab.from_name.setText("StageGrid Courier")
        app.processEvents()
        pix = window.grab()
        path = out / f"{names[index]}.png"
        pix.save(str(path))
        print(f"Wrote {path}")
        QTimer.singleShot(80, lambda: capture(index + 1))

    QTimer.singleShot(120, lambda: capture(0))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
