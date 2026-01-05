# -*- coding: utf-8 -*-
# ui/action_popup.py

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint, QSize
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QGraphicsDropShadowEffect, QApplication
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint, QSize
from PyQt5.QtGui import QCursor, QColor
from core.config import COLORS
from ui.common_tags import CommonTags
from ui.success_animation import SuccessAnimationWidget

class ActionPopup(QWidget):
    request_favorite = pyqtSignal(int)
    request_tag_toggle = pyqtSignal(int, str)
    request_manager = pyqtSignal()

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_idea_id = None
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self._init_ui()
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

    def _init_ui(self):
        self.container = QWidget(self)
        self.container.setStyleSheet(f"""
            QWidget {{
                background-color: #2D2D2D;
                border: 1px solid #444;
                border-radius: 18px;
            }}
        """)
        
        layout = QHBoxLayout(self.container)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        self.success_animation = SuccessAnimationWidget()
        layout.addWidget(self.success_animation)
        
        line = QLabel("|")
        line.setStyleSheet("color: #555; border:none; background: transparent;")
        layout.addWidget(line)

        self.btn_fav = QPushButton()
        self.btn_fav.setToolTip("收藏")
        self.btn_fav.setCursor(Qt.PointingHandCursor)
        self.btn_fav.clicked.connect(self._on_fav_clicked)
        layout.addWidget(self.btn_fav)

        self.common_tags_bar = CommonTags(self.db_manager)
        self.common_tags_bar.tag_clicked.connect(self._on_quick_tag_clicked)
        self.common_tags_bar.manager_requested.connect(self.request_manager.emit)
        self.common_tags_bar.refresh_requested.connect(self._adjust_size_dynamically)
        
        layout.addWidget(self.common_tags_bar)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.container.setGraphicsEffect(shadow)

    def _adjust_size_dynamically(self):
        if self.isVisible():
            self.container.adjustSize()
            self.resize(self.container.size() + QSize(10, 10))

    def _refresh_ui_state(self):
        if not self.current_idea_id: return
        idea_data = self.db_manager.get_idea(self.current_idea_id)
        if not idea_data: return

        is_favorite = idea_data[5] == 1
        active_tags = self.db_manager.get_tags(self.current_idea_id)

        self.common_tags_bar.reload_tags(active_tags)

        if is_favorite:
            self.btn_fav.setText("★")
            self.btn_fav.setStyleSheet(f"color: {COLORS['warning']}; border: none; font-size: 16px;")
        else:
            self.btn_fav.setText("☆")
            self.btn_fav.setStyleSheet(f"QPushButton {{ background: transparent; color: #BBB; border: none; font-size: 16px; }} QPushButton:hover {{ color: #FFFFFF; }}")

        self._adjust_size_dynamically()

    def show_at_mouse(self, idea_id):
        self.current_idea_id = idea_id
        
        self.success_animation.start()
        self._refresh_ui_state()

        cursor_pos = QCursor.pos()
        screen_geometry = QApplication.screenAt(cursor_pos).geometry()
        
        x = cursor_pos.x() - self.width() // 2
        y = cursor_pos.y() - self.height() - 20

        if x < screen_geometry.left(): x = screen_geometry.left()
        elif x + self.width() > screen_geometry.right(): x = screen_geometry.right() - self.width()

        if y < screen_geometry.top():
            y = cursor_pos.y() + 25
            if y + self.height() > screen_geometry.bottom(): y = screen_geometry.bottom() - self.height()

        self.move(x, y)
        self.show()
        self.hide_timer.start(3500)

    def _on_fav_clicked(self):
        if self.current_idea_id:
            self.request_favorite.emit(self.current_idea_id)
            self._refresh_ui_state()
            self.hide_timer.start(1500)

    def _on_quick_tag_clicked(self, tag_name):
        if self.current_idea_id:
            self.request_tag_toggle.emit(self.current_idea_id, tag_name)
            self._refresh_ui_state()
            self.hide_timer.start(3500)

    def enterEvent(self, event):
        self.hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hide_timer.start(1500)
        super().leaveEvent(event)
