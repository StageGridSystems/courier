"""Built-in how-to guide tab."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QScrollArea, QSizePolicy, QTextBrowser, QVBoxLayout, QWidget

from courier.branding import BRAND_NAME, PUBLISHER
from courier.guide.content import GUIDE_SECTIONS
from courier.ui.widgets.cards import make_card


class GuideTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 8, 14, 10)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel(f"How to use {BRAND_NAME}")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        intro = QLabel(
            f"{BRAND_NAME} by {PUBLISHER} sends campaigns through your own Gmail or "
            "Google Workspace account via the Gmail API. Follow these steps once, then "
            "reuse the same Desktop OAuth client."
        )
        intro.setObjectName("mutedLabel")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        for section in GUIDE_SECTIONS:
            card, body = make_card(section.title)
            body_view = QTextBrowser()
            body_view.setOpenExternalLinks(True)
            body_view.setHtml(section.body_html)
            body_view.setMinimumHeight(72)
            body_view.setMaximumHeight(220)
            body_view.setStyleSheet("border: none; background: transparent;")
            body.addWidget(body_view)
            layout.addWidget(card)

        layout.addStretch(1)
        scroll.setWidget(container)
        root.addWidget(scroll)
