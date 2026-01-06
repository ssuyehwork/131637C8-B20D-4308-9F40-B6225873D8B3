# -*- coding: utf-8 -*-
# ui/utils.py
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtCore import QByteArray, QSize, Qt
from core.config import COLORS

_ICONS = {
    'all_data.svg': """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
</svg>
    """,
    'today.svg': """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
    <line x1="16" y1="2" x2="16" y2="6"></line>
    <line x1="8" y1="2" x2="8" y2="6"></line>
    <line x1="3" y1="10" x2="21" y2="10"></line>
</svg>
    """,
    'clipboard.svg': """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
    <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
</svg>
    """,
    'uncategorized.svg': """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 16.25"></path>
    <line x1="8" y1="18" x2="21" y2="18"></line>
</svg>
    """,
    'untagged.svg': """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 2L2 7l10 5 10-5-10-5z"></path>
    <path d="M2 17l10 5 10-5"></path>
    <path d="M2 12l10 5 10-5"></path>
</svg>
    """,
    'bookmark.svg': """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
</svg>
    """,
    'trash.svg': """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 6h18"/>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
</svg>
    """,
    'rating.svg': """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
</svg>
    """,
    'archive.svg': """
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="21 8 21 21 3 21 3 8"></polyline>
    <rect x="1" y="3" width="22" height="5"></rect>
    <line x1="10" y1="12" x2="14" y2="12"></line>
</svg>
    """
}

_ICON_THEME_COLORS = {
    'all_data.svg': COLORS.get('primary'),
    'today.svg': COLORS.get('info'),
    'clipboard.svg': COLORS.get('success'),
    'uncategorized.svg': COLORS.get('warning'),
    'untagged.svg': '#DAA520', # GoldenRod
    'bookmark.svg': '#ff6b81', # Pink from MainWindow
    'trash.svg': COLORS.get('danger'),
    'rating.svg': '#FFD700', # Gold
    'archive.svg': '#a29bfe' # A light purple
}

_icon_cache = {}

def create_svg_icon(name, size=16, color=None):
    cache_key = (name, size, color)
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    svg_data = _ICONS.get(name)
    if not svg_data:
        return QIcon()

    final_color = color if color else _ICON_THEME_COLORS.get(name, '#FFFFFF')

    q_byte_array = QByteArray(svg_data.encode('utf-8'))
    q_byte_array.replace(b'currentColor', QByteArray(final_color.encode('utf-8')))

    pixmap = QPixmap()
    pixmap.loadFromData(q_byte_array)

    icon = QIcon(pixmap.scaled(QSize(size, size), Qt.KeepAspectRatio, Qt.SmoothTransformation))
    _icon_cache[cache_key] = icon
    return icon
