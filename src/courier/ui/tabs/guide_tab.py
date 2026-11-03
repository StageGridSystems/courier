"""Built-in how-to guide tab."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QScrollArea, QTextBrowser, QVBoxLayout, QWidget

from courier.branding import BRAND_NAME, PUBLISHER
from courier.guide.content import GUIDE_SECTIONS


class GuideTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

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
            heading = QLabel(section.title)
            heading.setStyleSheet("font-weight: 700; font-size: 15px;")
            layout.addWidget(heading)
            body = QTextBrowser()
            body.setOpenExternalLinks(True)
            body.setHtml(section.body_html)
            body.setMinimumHeight(80)
            layout.addWidget(body)

        layout.addStretch(1)
        scroll.setWidget(container)
        root.addWidget(scroll)
