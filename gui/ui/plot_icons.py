"""Embedded SVG icons rasterized at twice the requested size before scaling."""
import re

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QPalette
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

_HEX = re.compile(r"#[0-9A-Fa-f]{6}")

# one icon per live plot type (gui/resources/params_schema.json -> plot_types);
# 'link' is legacy and never offered in the combo
_SVGS = {
    "heatmap": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<g stroke="#176B87" stroke-width="1" stroke-linejoin="round">'
        '<rect x="3" y="3" width="5" height="5" rx="1" fill="#D9F1F2"/>'
        '<rect x="9.5" y="3" width="5" height="5" rx="1" fill="#74C7C4"/>'
        '<rect x="16" y="3" width="5" height="5" rx="1" fill="#F3A65A"/>'
        '<rect x="3" y="9.5" width="5" height="5" rx="1" fill="#9BD6DA"/>'
        '<rect x="9.5" y="9.5" width="5" height="5" rx="1" fill="#277DA1"/>'
        '<rect x="16" y="9.5" width="5" height="5" rx="1" fill="#F6D365"/>'
        '<rect x="3" y="16" width="5" height="5" rx="1" fill="#F6D365"/>'
        '<rect x="9.5" y="16" width="5" height="5" rx="1" fill="#F3A65A"/>'
        '<rect x="16" y="16" width="5" height="5" rx="1" fill="#D95D5D"/>'
        "</g></svg>"
    ),
    "highlights": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M4 3v18M8 3v18M16 3v18M20 3v18" stroke="#91A4B7" '
        'stroke-width="1.5"/>'
        '<rect x="8" y="4" width="8" height="16" rx="2" fill="#FFE48A" '
        'stroke="#F3A712" stroke-width="1.5"/>'
        '<path d="M10.5 8h3M10.5 12h3M10.5 16h3" stroke="#C47D00" '
        'stroke-width="1.5" stroke-linecap="round"/></svg>'
    ),
    "point": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M4 20V4M4 20h16" fill="none" stroke="#697B8C" '
        'stroke-width="1.5" stroke-linecap="round"/>'
        '<g fill="#11998E" stroke="#0B6F75" stroke-width="1">'
        '<circle cx="7" cy="16" r="1.7"/><circle cx="10" cy="12" r="1.7"/>'
        '<circle cx="13.5" cy="14" r="1.7"/><circle cx="16" cy="8" r="1.7"/>'
        '<circle cx="19" cy="6" r="1.7"/></g></svg>'
    ),
    "line": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M3.5 19.5V4M3.5 19.5H21" fill="none" stroke="#697B8C" '
        'stroke-width="1.5" stroke-linecap="round"/>'
        '<path d="M5.5 16.5 9 12l3 2 4-7 3 2" fill="none" stroke="#168AAD" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<g fill="#FFF" stroke="#168AAD" stroke-width="1.5">'
        '<circle cx="5.5" cy="16.5" r="1.2"/><circle cx="9" cy="12" r="1.2"/>'
        '<circle cx="12" cy="14" r="1.2"/><circle cx="16" cy="7" r="1.2"/>'
        '<circle cx="19" cy="9" r="1.2"/></g></svg>'
    ),
    "hist": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M3 20.5V4M3 20.5h18" fill="none" stroke="#697B8C" '
        'stroke-width="1.5" stroke-linecap="round"/>'
        '<rect x="5" y="14" width="3" height="6" rx=".7" fill="#9BD6DA"/>'
        '<rect x="9" y="9" width="3" height="11" rx=".7" fill="#54B6B2"/>'
        '<rect x="13" y="5" width="3" height="15" rx=".7" fill="#168AAD"/>'
        '<rect x="17" y="11" width="3" height="9" rx=".7" fill="#F3A65A"/>'
        "</svg>"
    ),
    "text": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M5 5h14M12 5v14M8.5 19h7" fill="none" stroke="#176B87" '
        'stroke-width="2" stroke-linecap="round"/>'
        '<path d="m7 5-1 3M17 5l1 3" fill="none" stroke="#176B87" '
        'stroke-width="1.5" stroke-linecap="round"/></svg>'
    ),
    "shape": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<circle cx="7" cy="7" r="3" fill="#75C9C5" stroke="#176B87" '
        'stroke-width="1.4"/>'
        '<rect x="13" y="4" width="6" height="6" rx="1" fill="#FFD166" '
        'stroke="#B97800" stroke-width="1.4"/>'
        '<path d="m7 13 4 7H3z" fill="#F28C8C" stroke="#A84848" '
        'stroke-width="1.4" stroke-linejoin="round"/>'
        '<path d="m16 13 4 3.5-4 3.5-4-3.5z" fill="#A58AD7" stroke="#625095" '
        'stroke-width="1.4" stroke-linejoin="round"/></svg>'
    ),
    "ridgeline": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<g fill="none" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 18h18" stroke="#697B8C" stroke-width="1.2"/>'
        '<path d="M3 17c3 0 3-5 6-5s3 5 6 5 3-2 6-2" stroke="#9BD6DA" '
        'stroke-width="2"/>'
        '<path d="M3 13c3 0 3-6 6-6s3 6 6 6 3-3 6-3" stroke="#4CB8B2" '
        'stroke-width="2"/>'
        '<path d="M3 9c3 0 3-5 6-5s3 5 6 5 3-2 6-2" stroke="#176B87" '
        'stroke-width="2"/></g></svg>'
    ),
    "PairWiseLink": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M3 19h18" stroke="#697B8C" stroke-width="1.4" '
        'stroke-linecap="round"/>'
        '<g fill="none" stroke-width="2" stroke-linecap="round">'
        '<path d="M5 18C5 8 19 8 19 18" stroke="#D95D5D"/>'
        '<path d="M7.5 18c0-7 9-7 9 0" stroke="#F3A712"/>'
        '<path d="M10 18c0-4 4-4 4 0" stroke="#168AAD"/></g>'
        '<g fill="#176B87">'
        '<circle cx="5" cy="19" r="1.5"/><circle cx="10" cy="19" r="1.5"/>'
        '<circle cx="14" cy="19" r="1.5"/><circle cx="19" cy="19" r="1.5"/>'
        "</g></svg>"
    ),
    "PairWiseLinkV2": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M3 20h18" stroke="#697B8C" stroke-width="1.3" '
        'stroke-linecap="round"/>'
        '<g fill="none" stroke-width="1.8" stroke-linecap="round">'
        '<path d="M4 19C4 6 20 6 20 19" stroke="#7B61A8"/>'
        '<path d="M6.5 19C6.5 9 17.5 9 17.5 19" stroke="#168AAD"/>'
        '<path d="M9 19C9 13 15 13 15 19" stroke="#3DBB9C"/>'
        '<path d="M4 19C7 14 9 14 12 19" stroke="#F3A712"/>'
        '<path d="M12 19c3-5 5-5 8 0" stroke="#D95D5D"/></g>'
        '<g fill="#263746">'
        '<circle cx="4" cy="20" r="1.25"/><circle cx="9" cy="20" r="1.25"/>'
        '<circle cx="12" cy="20" r="1.25"/><circle cx="15" cy="20" r="1.25"/>'
        '<circle cx="20" cy="20" r="1.25"/></g></svg>'
    ),
    "LinkS": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M5 19h14" stroke="#697B8C" stroke-width="1.4" '
        'stroke-linecap="round"/>'
        '<path d="M8 18C2 8 9 3 14 5c4 1.5 5 6 2 8.5-2.5 2-6 .5-5-2.5.5-1.6 '
        '2.5-1.6 3.5-.5" fill="none" stroke="#168AAD" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        '<circle cx="8" cy="19" r="1.6" fill="#176B87"/></svg>'
    ),
    "heatmapAnimated": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<g stroke="#176B87" stroke-width=".9">'
        '<rect x="3" y="3" width="5" height="5" rx="1" fill="#D9F1F2"/>'
        '<rect x="9.5" y="3" width="5" height="5" rx="1" fill="#74C7C4"/>'
        '<rect x="16" y="3" width="5" height="5" rx="1" fill="#F3A65A"/>'
        '<rect x="3" y="9.5" width="5" height="5" rx="1" fill="#9BD6DA"/>'
        '<rect x="9.5" y="9.5" width="5" height="5" rx="1" fill="#277DA1"/>'
        '<rect x="16" y="9.5" width="5" height="5" rx="1" fill="#F6D365"/></g>'
        '<circle cx="17.5" cy="17.5" r="4.7" fill="#FFFFFF" stroke="#11998E" '
        'stroke-width="1.4"/>'
        '<path d="m16.3 15 3.2 2.5-3.2 2.5z" fill="#11998E"/></svg>'
    ),
    "histAnimated": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M3 20.5V4M3 20.5h18" fill="none" stroke="#697B8C" '
        'stroke-width="1.4" stroke-linecap="round"/>'
        '<rect x="5" y="14" width="3" height="6" rx=".7" fill="#9BD6DA"/>'
        '<rect x="9" y="9" width="3" height="11" rx=".7" fill="#54B6B2"/>'
        '<rect x="13" y="5" width="3" height="15" rx=".7" fill="#168AAD"/>'
        '<circle cx="18" cy="16" r="4.5" fill="#FFFFFF" stroke="#11998E" '
        'stroke-width="1.4"/>'
        '<path d="m16.8 13.6 3.2 2.4-3.2 2.4z" fill="#11998E"/></svg>'
    ),
    "highlightsAnimated": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path d="M4 3v18M8 3v18M16 3v18M20 3v18" stroke="#91A4B7" '
        'stroke-width="1.4"/>'
        '<rect x="8" y="4" width="8" height="16" rx="2" fill="#FFE48A" '
        'stroke="#F3A712" stroke-width="1.4"/>'
        '<circle cx="17.5" cy="17.5" r="4.7" fill="#FFFFFF" stroke="#11998E" '
        'stroke-width="1.4"/>'
        '<path d="m16.3 15 3.2 2.5-3.2 2.5z" fill="#11998E"/></svg>'
    ),
}

_CACHE = {}


def _lift_dark_colors(doc):
    """Lift dark strokes/fills toward white (a dark popup swallows them)."""

    def _adj(m):
        c = QColor(m.group(0))
        if c.lightness() < 90:
            c = c.lighter(175)
        return c.name()

    return _HEX.sub(_adj, doc)


def plot_type_icon(name, size=22):
    """QIcon for a plot type (empty icon when the type has no artwork)."""
    svg = _SVGS.get(name)
    if svg is None:
        return QIcon()
    app = QApplication.instance()
    dark = (app is not None
            and app.palette().color(QPalette.Base).lightness() < 128)
    key = (name, dark, size)
    icon = _CACHE.get(key)
    if icon is None:
        doc = _lift_dark_colors(svg) if dark else svg
        renderer = QSvgRenderer(QByteArray(doc.encode("utf-8")))
        if not renderer.isValid():
            return QIcon()
        pm = QPixmap(size * 2, size * 2)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        try:
            renderer.render(p, QRectF(pm.rect()))
        finally:
            p.end()
        icon = QIcon(pm)
        _CACHE[key] = icon
    return icon


def PLOT_ICON_NAMES():
    return set(_SVGS)
