from functools import lru_cache
from pathlib import Path as _Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_LOGO_FILE = _Path(__file__).resolve().parent.parent.parent / "doc" / "RectChr_logo.svg"
LOGO_SVG = _LOGO_FILE.read_text(encoding="utf-8")


def logo_pixmap(square=False, size=64):
    renderer = QSvgRenderer(QByteArray(LOGO_SVG.encode("utf-8")))
    if not renderer.isValid():
        raise ValueError("Invalid RectChr logo SVG")
    if square:
        renderer.setViewBox(QRectF(0, 0, 86, 86))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
    else:
        pixmap = QPixmap(538, 172)
        pixmap.fill(Qt.white)
    painter = QPainter(pixmap)
    try:
        renderer.render(painter, QRectF(pixmap.rect()))
    finally:
        painter.end()
    if not square:
        pixmap.setDevicePixelRatio(2)
    return pixmap


@lru_cache(maxsize=1)
def application_icon():
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(logo_pixmap(square=True, size=size))
    return icon
