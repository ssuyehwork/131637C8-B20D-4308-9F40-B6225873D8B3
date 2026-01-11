# -*- coding: utf-8 -*-
# ui/common_tags.py

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal
from core.config import COLORS
from core.settings import load_setting
from ui.utils import create_svg_icon

class CommonTags(QWidget):
    tag_clicked = pyqtSignal(str) 
    manager_requested = pyqtSignal()
    refresh_requested = pyqtSignal() 

    # 【核心修改】构造函数接收 service
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self._init_ui()
        self.reload_tags()

    def _init_ui(self):
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def reload_tags(self, active_tags=None):
        if active_tags is None:
            active_tags = []
            
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        raw_tags = load_setting('manual_common_tags', ['工作', '待办', '重要'])
        limit = load_setting('common_tags_limit', 5)

        processed_tags = []
        for item in raw_tags:
            if isinstance(item, str):
                processed_tags.append({'name': item, 'visible': True})
            elif isinstance(item, dict):
                processed_tags.append(item)
        
        visible_tags = [t for t in processed_tags if t.get('visible', True)]
        display_tags = visible_tags[:limit]

        for tag in display_tags:
            name = tag['name']
            btn = QPushButton(f"{name}")
            btn.setCursor(Qt.PointingHandCursor)
            
            is_active = name in active_tags
            
            if is_active:
                style = f"""
                    QPushButton {{
                        background-color: {COLORS['primary']};
                        color: white;
                        border: 1px solid {COLORS['primary']};
                        border-radius: 10px; padding: 2px 8px; font-size: 11px; min-height: 20px; max-width: 80px;
                    }}
                    QPushButton:hover {{
                        background-color: #D32F2F; border-color: #D32F2F;
                    }}
                """
            else:
                style = f"""
                    QPushButton {{
                        background-color: #3E3E42; color: #DDD; border: 1px solid #555;
                        border-radius: 10px; padding: 2px 8px; font-size: 11px; min-height: 20px; max-width: 80px;
                    }}
                    QPushButton:hover {{
                        background-color: {COLORS['primary']}; border-color: {COLORS['primary']}; color: white;
                    }}
                """
            
            btn.setStyleSheet(style)
            btn.clicked.connect(lambda _, n=name: self.tag_clicked.emit(n))
            self.layout.addWidget(btn)

        btn_edit = QPushButton()
        btn_edit.setIcon(create_svg_icon("pencil.svg", "#888"))
        btn_edit.setToolTip("管理常用标签")
        btn_edit.setCursor(Qt.PointingHandCursor)
        btn_edit.setFixedSize(20, 20)
        btn_edit.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #666;
                border-radius: 10px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #444;
                border-color: #888;
            }
        """)
        btn_edit.clicked.connect(self.manager_requested.emit)
        self.layout.addWidget(btn_edit)
        
        self.refresh_requested.emit()