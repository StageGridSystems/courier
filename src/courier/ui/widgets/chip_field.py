"""Gmail-style recipient chip input field."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from courier.audience.extract import normalize_email, validate_email
from courier.branding import COLORS


class Chip(QFrame):
    removed = Signal(str)

    def __init__(self, email: str, *, valid: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.email = email
        self.valid = valid
        self.setObjectName("chipValid" if valid else "chipInvalid")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 4, 2)
        layout.setSpacing(4)
        self.label = QLabel(email)
        self.label.setStyleSheet("border: none; background: transparent;")
        remove = QLabel("×")
        remove.setCursor(Qt.CursorShape.PointingHandCursor)
        remove.setStyleSheet("border: none; background: transparent; font-weight: 700;")
        remove.mousePressEvent = self._on_remove  # type: ignore[method-assign]
        layout.addWidget(self.label)
        layout.addWidget(remove)
        bg = "rgba(13, 148, 136, 0.25)" if valid else "rgba(220, 38, 38, 0.25)"
        border = COLORS["primary"] if valid else COLORS["danger"]
        self.setStyleSheet(
            f"QFrame {{ background: {bg}; border: 1px solid {border}; border-radius: 12px; }}"
        )

    def _on_remove(self, _event: object) -> None:
        self.removed.emit(self.email)


class ChipField(QWidget):
    """Type emails; Enter/comma/semicolon/space commits; backspace removes last chip."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._emails: list[str] = []
        self._invalid: list[str] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumHeight(48)
        scroll.setMaximumHeight(120)

        self.container = QWidget()
        self.flow = QHBoxLayout(self.container)
        self.flow.setContentsMargins(6, 6, 6, 6)
        self.flow.setSpacing(6)
        self.flow.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Type an email, then Enter")
        self.input.setFrame(False)
        self.input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.input.returnPressed.connect(self._commit_input)
        self.input.textChanged.connect(self._on_text_changed)
        self.input.installEventFilter(self)
        self.flow.addWidget(self.input)
        self.flow.addStretch(1)

        scroll.setWidget(self.container)
        outer.addWidget(scroll)
        self._chips: list[Chip] = []

    def eventFilter(self, obj: object, event: object) -> bool:
        if obj is self.input and isinstance(event, QKeyEvent):
            if event.type() == event.Type.KeyPress:
                if event.key() == Qt.Key.Key_Backspace and not self.input.text():
                    if self._emails or self._invalid:
                        self._remove_last()
                        return True
                text = event.text()
                if text in {",", ";", " "}:
                    if self.input.text().strip():
                        self._commit_input()
                        return True
        return super().eventFilter(obj, event)  # type: ignore[arg-type]

    def _on_text_changed(self, text: str) -> None:
        if not text:
            return
        if text[-1] in ",;":
            self.input.setText(text[:-1])
            self._commit_input()

    def _commit_input(self) -> None:
        raw = self.input.text().strip().strip(",;")
        self.input.clear()
        if not raw:
            return
        self.add_emails([raw])

    def add_emails(self, emails: list[str]) -> None:
        import re

        existing = {normalize_email(e) for e in self._emails}
        for raw in emails:
            candidate = raw.strip()
            if not candidate:
                continue
            if validate_email(candidate):
                pieces = [candidate]
            else:
                pieces = [p for p in re.split(r"[,;\s]+", candidate) if p]
            for piece in pieces:
                norm = normalize_email(piece)
                if validate_email(norm):
                    if norm in existing:
                        continue
                    existing.add(norm)
                    self._emails.append(norm)
                elif piece and piece not in self._invalid:
                    self._invalid.append(piece)
        self._rebuild()
        self.changed.emit()

    def set_emails(self, emails: list[str]) -> None:
        self._emails = []
        self._invalid = []
        self.add_emails(emails)

    def emails(self) -> list[str]:
        return list(self._emails)

    def clear(self) -> None:
        self._emails.clear()
        self._invalid.clear()
        self._rebuild()
        self.changed.emit()

    def _remove_last(self) -> None:
        if self._invalid:
            self._invalid.pop()
        elif self._emails:
            self._emails.pop()
        self._rebuild()
        self.changed.emit()

    def _remove_email(self, email: str) -> None:
        norm = normalize_email(email)
        self._emails = [e for e in self._emails if e != norm]
        self._invalid = [e for e in self._invalid if e != email]
        self._rebuild()
        self.changed.emit()

    def _rebuild(self) -> None:
        while self.flow.count():
            item = self.flow.takeAt(0)
            w = item.widget()
            if w and w is not self.input:
                w.deleteLater()
        self._chips.clear()
        for email in self._emails:
            chip = Chip(email, valid=True)
            chip.removed.connect(self._remove_email)
            self.flow.insertWidget(self.flow.count(), chip)
            self._chips.append(chip)
        for email in self._invalid:
            chip = Chip(email, valid=False)
            chip.removed.connect(self._remove_email)
            self.flow.insertWidget(self.flow.count(), chip)
            self._chips.append(chip)
        self.flow.addWidget(self.input)
        self.flow.addStretch(1)
        self.input.setFocus()
