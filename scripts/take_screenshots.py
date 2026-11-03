#!/usr/bin/env python3
"""Capture offscreen screenshots of each main tab for docs/screenshots."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtGui import QColor, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from courier.auth.oauth import AuthManager  # noqa: E402
from courier.auth.token_store import TokenStore  # noqa: E402
from courier.sender.rate_limit import estimate_send_seconds, format_duration  # noqa: E402
from courier.storage.persistence import Persistence  # noqa: E402
from courier.ui.main_window import MainWindow  # noqa: E402
from courier.ui.tabs.compose_tab import ConfirmSendDialog  # noqa: E402


def main() -> int:
    out = ROOT / "docs" / "screenshots"
    out.mkdir(parents=True, exist_ok=True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    data = ROOT / ".screenshot-data"
    data.mkdir(exist_ok=True)
    persistence = Persistence(data)
    token_store = TokenStore(data)
    auth = AuthManager(token_store)
    state = persistence.load()
    state.settings.theme = "dark"
    state.audiences.ensure_default()
    state.audiences.lists[0].emails = []
    state.audiences.lists[0].add(
        [
            "alice@example.com",
            "bob@example.com",
            "carol@example.com",
            "dave@example.com",
            "erin@example.com",
            "frank@example.com",
        ]
    )
    state.audiences.add_suppression(["frank@example.com"])
    state.settings.test_audience = ["admin@example.com", "ops@example.com"]

    window = MainWindow(state, persistence, auth, token_store)
    window.resize(1280, 800)
    window.show()

    # Seed compose + audience chips for richer shots
    window.compose_tab.subject.setText("March product update")
    window.compose_tab.html_edit.setPlainText(
        "<h2>Hello {{email}}</h2><p>Here is what is new this month at StageGrid.</p>"
    )
    window.compose_tab.from_name.setText("StageGrid Courier")
    window.settings_tab.test_audience.set_emails(state.settings.test_audience)
    window.audience_tab._refresh_emails()  # noqa: SLF001

    names = [
        "01-authentication",
        "02-audience",
        "03-compose",
        "04-settings",
        "05-guide",
    ]

    def grab(name: str) -> None:
        app.processEvents()
        pix = window.grab()
        path = out / f"{name}.png"
        pix.save(str(path))
        print(f"Wrote {path}")

    def seed_audience_chips() -> None:
        # Set chips after the tab has a real width so FlowLayout can wrap
        window.audience_tab.chips.set_emails(
            ["new.person@example.com", "also@example.com", "bad-not-email"]
        )
        window.audience_tab.suppression.set_emails(["frank@example.com"])
        window.audience_tab._refresh_emails()  # noqa: SLF001
        app.processEvents()

    def capture(index: int) -> None:
        if index >= window.tabs.count():
            window.tabs.setCurrentIndex(2)
            app.processEvents()
            recipients = state.audiences.effective_recipients()
            estimate = format_duration(
                estimate_send_seconds(len(recipients), state.settings.send_interval_seconds)
            )
            dlg = ConfirmSendDialog(
                count=len(recipients),
                subject=window.compose_tab.subject.text(),
                estimate=estimate,
                parent=window,
            )
            dlg.setStyleSheet(window.styleSheet())
            dlg.resize(520, 280)
            dlg.show()
            app.processEvents()
            dlg_pix = dlg.grab()
            win_pix = window.grab()
            painter = QPainter(win_pix)
            x = (win_pix.width() - dlg_pix.width()) // 2
            y = (win_pix.height() - dlg_pix.height()) // 2
            painter.fillRect(win_pix.rect(), QColor(0, 0, 0, 120))
            painter.drawPixmap(x, y, dlg_pix)
            painter.end()
            path = out / "06-send-confirm-modal.png"
            win_pix.save(str(path))
            print(f"Wrote {path}")
            dlg.close()
            app.quit()
            return
        window.tabs.setCurrentIndex(index)
        app.processEvents()
        if index == 1:
            seed_audience_chips()
        if index == 3:
            window.settings_tab.test_audience.set_emails(
                ["admin@example.com", "ops@example.com"]
            )
            app.processEvents()
        grab(names[index])
        QTimer.singleShot(120, lambda: capture(index + 1))

    QTimer.singleShot(150, lambda: capture(0))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
