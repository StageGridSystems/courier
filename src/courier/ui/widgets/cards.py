"""Simple card section helper for consistent tab chrome."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget


def make_card(
    title: str,
    *,
    subtitle: str | None = None,
    parent: QWidget | None = None,
) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame(parent)
    card.setObjectName("card")
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(10)
    heading = QLabel(title)
    heading.setObjectName("cardHeading")
    layout.addWidget(heading)
    if subtitle:
        sub = QLabel(subtitle)
        sub.setObjectName("mutedLabel")
        sub.setWordWrap(True)
        layout.addWidget(sub)
    return card, layout


def empty_state(text: str, parent: QWidget | None = None) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName("emptyState")
    label.setWordWrap(True)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label
