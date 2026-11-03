"""Application entry point with global exception handling."""

from __future__ import annotations

import logging
import sys
import traceback
from types import TracebackType

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from courier.auth.oauth import AuthManager
from courier.auth.token_store import TokenStore
from courier.branding import BRAND_NAME
from courier.storage.persistence import Persistence
from courier.ui.main_window import MainWindow


def _configure_logging(log_path: object) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )
    logging.getLogger("google.auth").setLevel(logging.WARNING)
    logging.getLogger("google_auth_oauthlib").setLevel(logging.WARNING)


def _install_excepthook(log_path: object) -> None:
    def handle(
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        logging.getLogger("courier").error("Unhandled exception:\n%s", text)
        try:
            QMessageBox.critical(
                None,
                f"{BRAND_NAME} error",
                "Something went wrong. Details were written to the log file:\n"
                f"{log_path}\n\n{exc}",
            )
        except Exception:
            pass

    sys.excepthook = handle


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(BRAND_NAME)
    app.setOrganizationName("StageGrid Systems")
    app.setStyle("Fusion")

    persistence = Persistence()
    _configure_logging(persistence.log_path)
    _install_excepthook(persistence.log_path)

    token_store = TokenStore(persistence.data_dir)
    auth = AuthManager(token_store)
    auth.load_saved()

    state = persistence.load()
    window = MainWindow(state, persistence, auth, token_store)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
