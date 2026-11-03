#!/usr/bin/env python3
"""Generate packaging/windows/courier.ico from the brand SVG."""

from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = ROOT / "src" / "courier" / "resources" / "icons" / "courier.svg"
PNG_FALLBACK = ROOT / "src" / "courier" / "resources" / "icons" / "courier.png"
OUT_PATH = ROOT / "packaging" / "windows" / "courier.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def _render_via_qt() -> list:
    """Rasterize courier.svg at each ICO size using QtSvg."""
    from PIL import Image
    from PySide6.QtCore import QBuffer, QByteArray, QCoreApplication, QIODevice, Qt
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseSoftwareOpenGL, True)
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    renderer = QSvgRenderer(QByteArray(SVG_PATH.read_bytes()))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG: {SVG_PATH}")

    frames = []
    for size in SIZES:
        image = QImage(size, size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "PNG"):
            raise RuntimeError(f"Failed to encode PNG at {size}x{size}")
        frames.append(Image.open(io.BytesIO(bytes(buffer.data()))).convert("RGBA"))
    _ = app
    return frames


def _render_via_png_fallback() -> list:
    """Resize the committed PNG (exported from the same SVG) into ICO frames."""
    from PIL import Image

    if not PNG_FALLBACK.is_file():
        raise FileNotFoundError(PNG_FALLBACK)
    base = Image.open(PNG_FALLBACK).convert("RGBA")
    return [base.resize((s, s), Image.Resampling.LANCZOS) for s in SIZES]


def main() -> int:
    try:
        frames = _render_via_qt()
        source = "SVG via QtSvg"
    except Exception as exc:
        print(f"QtSvg render unavailable ({type(exc).__name__}: {exc}); using PNG fallback")
        frames = _render_via_png_fallback()
        source = f"PNG fallback ({PNG_FALLBACK.name})"

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    largest = frames[-1]
    largest.save(
        OUT_PATH,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=frames[:-1],
    )
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size} bytes) from {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
