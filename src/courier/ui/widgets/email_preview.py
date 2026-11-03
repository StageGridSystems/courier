"""Live HTML email preview via QtWebEngine, with a QTextBrowser fallback."""

from __future__ import annotations

import base64
import logging
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QTextBrowser, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)

_IMG_SRC_RE = re.compile(
    r"""(<img\b[^>]*\bsrc\s*=\s*)(["'])(https?://[^"']+)\2""",
    re.IGNORECASE,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView

    _HAS_WEBENGINE = True
except ImportError:  # pragma: no cover - depends on optional Qt build
    QWebEngineView = None  # type: ignore[misc, assignment]
    _HAS_WEBENGINE = False


class EmailPreview(QWidget):
    """Render campaign HTML. Prefer WebEngine for remote images and full CSS."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._web: QWebEngineView | None = None
        self._browser: QTextBrowser | None = None
        if _HAS_WEBENGINE and QWebEngineView is not None:
            self._web = QWebEngineView(self)
            layout.addWidget(self._web)
        else:
            self._browser = QTextBrowser(self)
            self._browser.setOpenExternalLinks(True)
            layout.addWidget(self._browser)

    def setHtml(self, html: str) -> None:  # noqa: N802 - Qt naming
        if self._web is not None:
            # Base URL lets relative paths resolve; remote https images load normally.
            self._web.setHtml(html, QUrl("https://preview.local/"))
            return
        assert self._browser is not None
        self._browser.setHtml(self._inline_remote_images(html))

    def _inline_remote_images(self, html: str) -> str:
        """Fetch remote images and embed as data URIs for QTextBrowser."""

        def repl(match: re.Match[str]) -> str:
            prefix, quote, url = match.group(1), match.group(2), match.group(3)
            try:
                req = Request(url, headers={"User-Agent": "CourierPreview/0.1"})
                with urlopen(req, timeout=5) as resp:  # noqa: S310 - preview only
                    data = resp.read()
                    ctype = resp.headers.get_content_type() or "image/png"
                b64 = base64.b64encode(data).decode("ascii")
                return f"{prefix}{quote}data:{ctype};base64,{b64}{quote}"
            except (URLError, TimeoutError, OSError, ValueError) as exc:
                logger.debug(
                    "Preview image fetch failed for %s: %s", url, type(exc).__name__
                )
                return match.group(0)

        return _IMG_SRC_RE.sub(repl, html)
