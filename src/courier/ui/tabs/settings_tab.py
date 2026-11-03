"""Settings and preferences tab."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from courier.auth.token_store import TokenStore
from courier.exceptions import ConfigError
from courier.storage.config import AppState
from courier.storage.export_import import export_config, import_config_optional_auth
from courier.storage.persistence import Persistence
from courier.ui.widgets.chip_field import ChipField


class SettingsTab(QWidget):
    changed = Signal()
    theme_changed = Signal(str)
    data_dir_changed = Signal(str)
    state_imported = Signal(object)

    def __init__(
        self,
        state: AppState,
        persistence: Persistence,
        token_store: TokenStore,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.state = state
        self.persistence = persistence
        self.token_store = token_store
        s = state.settings

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title = QLabel("Settings / Prefs")
        title.setObjectName("sectionTitle")
        root.addWidget(title)

        form = QFormLayout()
        self.test_audience = ChipField()
        self.test_audience.set_emails(s.test_audience)
        form.addRow("Test audience (admins)", self.test_audience)

        self.rate = QDoubleSpinBox()
        self.rate.setRange(0.5, 60.0)
        self.rate.setSingleStep(0.5)
        self.rate.setSuffix(" s between emails")
        self.rate.setValue(s.send_interval_seconds)
        form.addRow("Send rate", self.rate)

        self.daily_cap = QSpinBox()
        self.daily_cap.setRange(1, 10000)
        self.daily_cap.setValue(s.daily_cap)
        form.addRow("Daily cap", self.daily_cap)

        limits = QLabel(
            "Gmail consumer accounts: about 500/day. Google Workspace: about 2000/day. "
            "Courier defaults are conservative (2s interval, 400/day)."
        )
        limits.setObjectName("mutedLabel")
        limits.setWordWrap(True)
        form.addRow("", limits)

        self.footer_enabled = QCheckBox("Append default unsubscribe footer")
        self.footer_enabled.setChecked(s.default_footer_enabled)
        form.addRow("Footer", self.footer_enabled)
        self.footer_html = QTextEdit()
        self.footer_html.setPlainText(s.default_footer_html)
        self.footer_html.setMaximumHeight(90)
        form.addRow("Footer HTML", self.footer_html)

        self.theme = QComboBox()
        self.theme.addItems(["dark", "light"])
        self.theme.setCurrentText(s.theme if s.theme in {"dark", "light"} else "dark")
        form.addRow("Theme", self.theme)

        self.confirm_destructive = QCheckBox("Confirm destructive actions")
        self.confirm_destructive.setChecked(s.confirm_destructive)
        form.addRow("Dialogs", self.confirm_destructive)
        send_note = QLabel("Send confirmation cannot be disabled.")
        send_note.setObjectName("mutedLabel")
        form.addRow("", send_note)

        self.dry_run = QCheckBox("Dry-run mode (do not call Gmail API)")
        self.dry_run.setChecked(s.dry_run)
        form.addRow("Safety", self.dry_run)

        self.data_folder = QLineEdit(s.data_folder or str(self.persistence.data_dir))
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse_data)
        row = QHBoxLayout()
        row.addWidget(self.data_folder)
        row.addWidget(browse)
        form.addRow("Data folder", row)

        root.addLayout(form)

        save = QPushButton("Save settings")
        save.setObjectName("primaryButton")
        save.clicked.connect(self._save)
        root.addWidget(save)

        root.addWidget(QLabel("Configuration backup"))
        self.include_auth = QCheckBox(
            "Include auth (client secret + token). Requires a password and encrypts the payload."
        )
        root.addWidget(self.include_auth)
        self.auth_password = QLineEdit()
        self.auth_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.auth_password.setPlaceholderText("Password for encrypted auth (export/import)")
        root.addWidget(self.auth_password)
        warn = QLabel(
            "Warning: an export with auth can send as your account if the password is known. "
            "Store it like a secret."
        )
        warn.setObjectName("mutedLabel")
        warn.setWordWrap(True)
        root.addWidget(warn)

        io_row = QHBoxLayout()
        export_btn = QPushButton("Export configuration…")
        export_btn.clicked.connect(self._export)
        import_btn = QPushButton("Import configuration…")
        import_btn.clicked.connect(self._import)
        io_row.addWidget(export_btn)
        io_row.addWidget(import_btn)
        io_row.addStretch()
        root.addLayout(io_row)
        root.addStretch(1)

    def bind_state(self, state: AppState) -> None:
        self.state = state
        s = state.settings
        self.test_audience.set_emails(s.test_audience)
        self.rate.setValue(s.send_interval_seconds)
        self.daily_cap.setValue(s.daily_cap)
        self.footer_enabled.setChecked(s.default_footer_enabled)
        self.footer_html.setPlainText(s.default_footer_html)
        self.theme.setCurrentText(s.theme if s.theme in {"dark", "light"} else "dark")
        self.confirm_destructive.setChecked(s.confirm_destructive)
        self.dry_run.setChecked(s.dry_run)
        self.data_folder.setText(s.data_folder or str(self.persistence.data_dir))

    def _browse_data(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Data folder", self.data_folder.text())
        if path:
            self.data_folder.setText(path)

    def _save(self) -> None:
        s = self.state.settings
        s.test_audience = self.test_audience.emails()
        s.send_interval_seconds = float(self.rate.value())
        s.daily_cap = int(self.daily_cap.value())
        s.default_footer_enabled = self.footer_enabled.isChecked()
        s.default_footer_html = self.footer_html.toPlainText()
        s.theme = self.theme.currentText()
        s.confirm_destructive = self.confirm_destructive.isChecked()
        s.confirm_send = True
        s.dry_run = self.dry_run.isChecked()
        s.data_folder = self.data_folder.text().strip()
        self.theme_changed.emit(s.theme)
        if s.data_folder:
            self.data_dir_changed.emit(s.data_folder)
        self.changed.emit()
        QMessageBox.information(self, "Settings", "Settings saved.")

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export configuration", "courier-config.json", "JSON (*.json)"
        )
        if not path:
            return
        include = self.include_auth.isChecked()
        password = self.auth_password.text()
        try:
            secrets = self.token_store.export_secrets() if include else None
            export_config(
                self.state,
                Path(path),
                include_auth=include,
                auth_secrets=secrets,
                password=password if include else None,
            )
            QMessageBox.information(self, "Export", "Configuration exported.")
        except ConfigError as exc:
            QMessageBox.warning(self, "Export", exc.message)

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import configuration", "", "JSON (*.json)"
        )
        if not path:
            return
        load_auth = self.include_auth.isChecked()
        password = self.auth_password.text() or None
        try:
            state, auth = import_config_optional_auth(
                Path(path), password=password, load_auth=load_auth
            )
            if auth:
                self.token_store.import_secrets(auth)
            self.state_imported.emit(state)
            QMessageBox.information(self, "Import", "Configuration imported.")
        except ConfigError as exc:
            QMessageBox.warning(self, "Import", exc.message)
