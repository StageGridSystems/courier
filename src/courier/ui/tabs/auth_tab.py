"""Authentication tab."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from courier.auth.oauth import AuthManager, classify_client_json
from courier.exceptions import AuthError


class _OAuthWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, auth: AuthManager) -> None:
        super().__init__()
        self.auth = auth

    def run(self) -> None:
        try:
            email = self.auth.run_oauth_flow()
            self.succeeded.emit(email)
        except AuthError as exc:
            self.failed.emit(exc.message)
        except Exception as exc:
            self.failed.emit(f"Sign-in failed: {exc}")


class AuthTab(QWidget):
    status_changed = Signal()

    def __init__(self, auth: AuthManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.auth = auth
        self._worker: _OAuthWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        title = QLabel("Authentication")
        title.setObjectName("sectionTitle")
        root.addWidget(title)
        hint = QLabel(
            "Connect a Google Cloud Desktop OAuth client, then sign in with the Gmail "
            "account you will send from. Courier only requests gmail.send plus your email."
        )
        hint.setObjectName("mutedLabel")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.status_card = QFrame()
        self.status_card.setObjectName("statusWarn")
        status_layout = QVBoxLayout(self.status_card)
        self.status_title = QLabel("Not connected")
        self.status_title.setStyleSheet("font-weight: 700; font-size: 15px; border: none;")
        self.status_detail = QLabel("Load a Desktop client JSON, then sign in.")
        self.status_detail.setObjectName("mutedLabel")
        self.status_detail.setWordWrap(True)
        self.status_detail.setStyleSheet("border: none;")
        status_layout.addWidget(self.status_title)
        status_layout.addWidget(self.status_detail)
        root.addWidget(self.status_card)

        drop = QFrame()
        drop.setObjectName("card")
        drop.setAcceptDrops(True)
        drop_layout = QVBoxLayout(drop)
        drop_label = QLabel("Drop OAuth client JSON here")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_label.setStyleSheet("border: none; font-weight: 600;")
        drop_layout.addWidget(drop_label)
        browse_row = QHBoxLayout()
        self.browse_btn = QPushButton("Browse JSON…")
        self.browse_btn.clicked.connect(self._browse)
        browse_row.addStretch()
        browse_row.addWidget(self.browse_btn)
        browse_row.addStretch()
        drop_layout.addLayout(browse_row)
        self._drop_frame = drop
        drop.dragEnterEvent = self._drag_enter  # type: ignore[method-assign]
        drop.dropEvent = self._drop  # type: ignore[method-assign]
        root.addWidget(drop)

        manual = QFrame()
        manual.setObjectName("card")
        form_wrap = QVBoxLayout(manual)
        form_wrap.addWidget(QLabel("Or enter credentials manually"))
        form = QFormLayout()
        self.client_id = QLineEdit()
        self.client_secret = QLineEdit()
        self.client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.project_id = QLineEdit()
        form.addRow("Client ID", self.client_id)
        form.addRow("Client secret", self.client_secret)
        form.addRow("Project ID", self.project_id)
        form_wrap.addLayout(form)
        save_manual = QPushButton("Save credentials")
        save_manual.clicked.connect(self._save_manual)
        form_wrap.addWidget(save_manual, alignment=Qt.AlignmentFlag.AlignLeft)
        root.addWidget(manual)

        actions = QHBoxLayout()
        self.sign_in_btn = QPushButton("Sign in with Google")
        self.sign_in_btn.setObjectName("primaryButton")
        self.sign_in_btn.clicked.connect(self._sign_in)
        self.sign_out_btn = QPushButton("Sign out")
        self.sign_out_btn.clicked.connect(self._sign_out)
        actions.addWidget(self.sign_in_btn)
        actions.addWidget(self.sign_out_btn)
        actions.addStretch()
        root.addLayout(actions)
        root.addStretch(1)
        self.refresh_status()

    def _drag_enter(self, event: object) -> None:
        mime = getattr(event, "mimeData", lambda: None)()
        if mime and mime.hasUrls():
            event.acceptProposedAction()  # type: ignore[union-attr]

    def _drop(self, event: object) -> None:
        mime = getattr(event, "mimeData", lambda: None)()
        if not mime:
            return
        for url in mime.urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() == ".json":
                self._load_json(path)
                break

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select OAuth client JSON", "", "JSON (*.json)"
        )
        if path:
            self._load_json(Path(path))

    def _load_json(self, path: Path) -> None:
        kind, err = classify_client_json(path)
        if err:
            QMessageBox.warning(self, "Client JSON", err)
            if kind != "desktop":
                return
        try:
            client = self.auth.load_client_from_file(path)
            self.client_id.setText(client.client_id)
            self.client_secret.setText(client.client_secret)
            self.project_id.setText(client.project_id)
            QMessageBox.information(
                self,
                "Client loaded",
                "Desktop OAuth client saved securely. Click Sign in with Google.",
            )
            self.refresh_status()
            self.status_changed.emit()
        except AuthError as exc:
            QMessageBox.warning(self, "Client JSON", exc.message)

    def _save_manual(self) -> None:
        try:
            self.auth.set_client_manual(
                self.client_id.text(),
                self.client_secret.text(),
                self.project_id.text(),
            )
            QMessageBox.information(self, "Saved", "Credentials saved. You can sign in now.")
            self.refresh_status()
            self.status_changed.emit()
        except AuthError as exc:
            QMessageBox.warning(self, "Credentials", exc.message)

    def _sign_in(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        self.sign_in_btn.setEnabled(False)
        self.sign_in_btn.setText("Waiting for browser…")
        self._worker = _OAuthWorker(self.auth)
        self._worker.succeeded.connect(self._on_signed_in)
        self._worker.failed.connect(self._on_sign_in_failed)
        self._worker.start()

    def _on_signed_in(self, email: str) -> None:
        self.sign_in_btn.setEnabled(True)
        self.sign_in_btn.setText("Sign in with Google")
        QMessageBox.information(self, "Connected", f"Signed in as {email}.")
        self.refresh_status()
        self.status_changed.emit()

    def _on_sign_in_failed(self, message: str) -> None:
        self.sign_in_btn.setEnabled(True)
        self.sign_in_btn.setText("Sign in with Google")
        QMessageBox.warning(self, "Sign-in failed", message)
        self.refresh_status()

    def _sign_out(self) -> None:
        self.auth.sign_out()
        self.refresh_status()
        self.status_changed.emit()

    def refresh_status(self) -> None:
        st = self.auth.status()
        if st["connected"]:
            self.status_card.setObjectName("statusOk")
            self.status_title.setText(f"Connected as {st['email']}")
            self.status_detail.setText("Token valid. Ready to send from this account.")
        elif st["has_client"]:
            self.status_card.setObjectName("statusWarn")
            self.status_title.setText("Client loaded, not signed in")
            self.status_detail.setText("Click Sign in with Google to complete OAuth.")
        else:
            self.status_card.setObjectName("statusWarn")
            self.status_title.setText("Not connected")
            self.status_detail.setText("Load a Desktop client JSON, then sign in.")
        # Force style refresh
        self.status_card.style().unpolish(self.status_card)
        self.status_card.style().polish(self.status_card)
