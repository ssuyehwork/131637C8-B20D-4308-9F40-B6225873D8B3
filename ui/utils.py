# -*- coding: utf-8 -*-
# ui/utils.py

import os
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtCore import Qt, QByteArray
from PyQt5.QtGui import QPalette, QIcon, QPixmap, QPainter
from PyQt5.QtWidgets import QApplication

# ==========================================
# 🎨 专业配色方案
# ==========================================
_icon_theme_colors = {
    'all_data.svg':      '#3498db',
    'today.svg':         '#2ecc71',
    'uncategorized.svg': '#e67e22',
    'untagged.svg':      '#95a5a6',
    'bookmark.svg':      '#ff6b81',
    'trash.svg':         '#e74c3c',
    'select.svg':        '#1abc9c',
    'calendar.svg':      '#9b59b6',
    'folder.svg':        '#f1c40f',
    'pin.svg':           '#3498db',
    'lock.svg':          '#e74c3c',
    'star.svg':          '#f39c12',
    'tag.svg':           '#1abc9c'
}

# ==========================================
# 💎 内置 SVG 图标数据
# ==========================================
_system_icons = {
    'calendar.svg': """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="4" y="5" width="16" height="16" rx="2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M16 3v4M8 3v4M4 11h16" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>""",
    'folder.svg': """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
        </svg>""",
    'pin.svg': """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="12" cy="10" r="3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>""",
    'lock.svg': """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>""",
    'star.svg': """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.77 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>""",
    'tag.svg': """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <line x1="7" y1="7" x2="7.01" y2="7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>""",
    'select.svg': """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M9.5 13.75L6.5 10.75" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M17.5 8.75L9.5 16.75" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M20 12.5V15.22C20 18.88 18.88 20 15.22 20H8.78C5.12 20 4 18.88 4 15.22V8.78C4 5.12 5.12 4 8.78 4H12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>""",
    'all_data.svg': """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M4 14.5C4 12.5 7.58 11 12 11C16.42 11 20 12.5 20 14.5V17.5C20 19.5 16.42 21 12 21C7.58 21 4 19.5 4 17.5V14.5Z" fill="currentColor" fill-opacity="0.2"/>
            <path d="M4 14.5C4 16.5 7.58 18 12 18C16.42 18 20 16.5 20 14.5V17.5C20 19.5 16.42 21 12 21C7.58 21 4 19.5 4 17.5V14.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <ellipse cx="12" cy="7.5" rx="8" ry="3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M4 7.5V10.5M20 7.5V10.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>""",
    'today.svg': """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="3" y="6" width="16" height="15" rx="2" fill="currentColor" fill-opacity="0.2"/>
            <rect x="3" y="6" width="16" height="15" rx="2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M3 10H19" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M7 4V8M15 4V8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="18" cy="18" r="3" stroke="currentColor" stroke-width="2"/>
            <circle cx="18" cy="18" r="1" fill="currentColor"/>
        </svg>""",
    'uncategorized.svg': """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M20 12V20C20 21.1 19.1 22 18 22H6C4.9 22 4 21.1 4 20V12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="currentColor" fill-opacity="0.1"/>
            <path d="M22 7L20 12H4L2 7H22Z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>
            <circle cx="12" cy="3" r="1.5" fill="currentColor"/>
            <path d="M16 6L17 8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M7 6L8 5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>""",
    'untagged.svg': """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M20.59 13.41L13.42 20.58C12.64 21.36 11.37 21.36 10.59 20.58L2 12V2H12L20.59 10.59C21.37 11.37 21.37 12.63 20.59 13.41Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="4 3"/>
            <circle cx="7" cy="7" r="1.5" fill="currentColor"/>
        </svg>""",
    'bookmark.svg': """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M19 21L12 17L5 21V5C5 3.89543 5.89543 3 7 3H17C18.1046 3 19 3.89543 19 5V21Z" fill="currentColor" fill-opacity="0.2"/>
            <path d="M19 21L12 17L5 21V5C5 3.89543 5.89543 3 7 3H17C18.1046 3 19 3.89543 19 5V21Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <line x1="8" y1="7" x2="16" y2="7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>""",
    'trash.svg': """
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M19 9L18.13 19.43C18.04 20.45 17.18 21.21 16.16 21.21H7.84C6.82 21.21 5.96 20.45 5.87 19.43L5 9" fill="currentColor" fill-opacity="0.2"/>
            <path d="M19 9L18.13 19.43C18.04 20.45 17.18 21.21 16.16 21.21H7.84C6.82 21.21 5.96 20.45 5.87 19.43L5 9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M20 5H4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M15 5V3C15 2.45 14.55 2 14 2H10C9.45 2 9 2.45 9 3V5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M10 12V17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M14 12V17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>"""
}

# 全局图标缓存
_icon_cache = {}

def create_svg_icon(icon_name):
    """
    创建一个基于 SVG 的 QIcon，具有智能着色和缓存功能。
    :param icon_name: SVG 图标的文件名 (例如 'all_data.svg')
    :return: QIcon 对象
    """
    # 默认使用当前应用程序调色板的文本颜色
    default_color = QApplication.palette().color(QPalette.WindowText).name()
    
    # 智能着色：检查是否有预定义的专业配色
    render_color = _icon_theme_colors.get(icon_name, default_color)

    cache_key = (icon_name, render_color)

    if cache_key in _icon_cache:
        return _icon_cache[cache_key]

    svg_data = ""
    if icon_name in _system_icons:
        svg_data = _system_icons[icon_name]
    
    if not svg_data:
        # 作为备用，尝试从文件系统加载
        icon_path = os.path.join("ui", "icons", icon_name)
        if os.path.exists(icon_path):
            try:
                with open(icon_path, 'r', encoding='utf-8') as f:
                    svg_data = f.read()
            except Exception:
                pass

    if not svg_data:
        return QIcon()  # 返回一个空图标

    # 将 SVG 中的 "currentColor" 替换为我们指定的颜色
    svg_data = svg_data.replace("currentColor", render_color)

    renderer = QSvgRenderer(QByteArray(svg_data.encode('utf-8')))
    
    icon_size = 20  # 标准图标尺寸
    pixmap = QPixmap(icon_size, icon_size)
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    icon = QIcon(pixmap)
    _icon_cache[cache_key] = icon
    return icon
