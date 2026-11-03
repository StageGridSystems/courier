"""Gmail-style recipient chip input with wrapping flow layout."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from courier.audience.extract import normalize_email, validate_email
from courier.branding import COLORS
from courier.ui.widgets.flow_layout import FlowLayout


class Chip(QFrame):
    removed = Signal(str)

    def __init__(self, email: str, *, valid: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.email = email
        self.valid = valid
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 6, 4)
        layout.setSpacing(6)
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
            f"QFrame {{ background: {bg}; border: 1px solid {border}; border-radius: 14px; }}"
        )
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.adjustSize()

    def sizeHint(self):  # type: ignore[override]
        return self.layout().sizeHint() if self.layout() else super().sizeHint()

    def minimumSizeHint(self):  # type: ignore[override]
        return self.sizeHint()

    def _on_remove(self, _event: object) -> None:
        self.removed.emit(self.email)


class ChipField(QFrame):
    """Type emails; Enter/comma/semicolon/space commits; backspace removes last chip."""

    changed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        min_height: int = 72,
        max_height: int = 220,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("chipField")
        self._emails: list[str] = []
        self._invalid: list[str] = []
        self._chips: list[Chip] = []
        self._min_height = min_height
        self._max_height = max_height

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(0)

        self.container = QWidget()
        self.flow = FlowLayout(self.container, margin=0, spacing=6)
        self.container.setLayout(self.flow)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Type an email, then Enter")
        self.input.setFrame(False)
        self.input.setMinimumWidth(180)
        self.input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.input.setStyleSheet("QLineEdit { background: transparent; border: none; padding: 4px; }")
        self.input.returnPressed.connect(self._commit_input)
        self.input.textChanged.connect(self._on_text_changed)
        self.input.installEventFilter(self)
        self.flow.addWidget(self.input)

        outer.addWidget(self.container)
        self.setMinimumHeight(min_height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.setAcceptDrops(False)

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

    def _clear_flow(self) -> None:
        while self.flow.count():
            item = self.flow.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w is not None and w is not self.input:
                w.deleteLater()

    def _rebuild(self) -> None:
        self._clear_flow()
        self._chips.clear()
        for email in self._emails:
            chip = Chip(email, valid=True)
            chip.removed.connect(self._remove_email)
            self.flow.addWidget(chip)
            self._chips.append(chip)
        for email in self._invalid:
            chip = Chip(email, valid=False)
            chip.removed.connect(self._remove_email)
            self.flow.addWidget(chip)
            self._chips.append(chip)
        self.flow.addWidget(self.input)
        self.flow.invalidate()
        self.container.setMinimumWidth(0)
        self.container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self._relayout()
        self.input.setFocus()

    def _relayout(self) -> None:
        """Apply flow geometry using the field width (never shrink-wrap)."""
        target = self.contentsRect()
        width = max(target.width(), 200)
        if self.container.width() != width:
            self.container.resize(width, self.container.height())
        needed = self.flow.heightForWidth(width) + 16
        height = max(self._min_height, min(self._max_height, needed))
        if self.minimumHeight() != height:
            self.setMinimumHeight(height)
        self.setMaximumHeight(self._max_height)
        self.flow.activate()
        self.flow.setGeometry(self.container.rect())

    def resizeEvent(self, event: object) -> None:  # type: ignore[override]
        super().resizeEvent(event)  # type: ignore[misc]
        self._relayout()

