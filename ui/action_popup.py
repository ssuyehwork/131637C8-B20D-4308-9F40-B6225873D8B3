# -*- coding: utf-8 -*-
# ui/action_popup.py

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QGraphicsDropShadowEffect, QApplication
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint, QSize
from PyQt5.QtGui import QCursor, QColor
from core.config import COLORS
from ui.common_tags import CommonTags
from ui.writing_animation import WritingAnimationWidget
from ui.utils import create_svg_icon

class ActionPopup(QWidget):
    request_favorite = pyqtSignal(int)
    request_tag_toggle = pyqtSignal(int, str)
    request_manager = pyqtSignal()

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service 
        self.current_idea_id = None
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 【关键修复】设置焦点策略，使其能捕获焦点
        self.setFocusPolicy(Qt.StrongFocus)
        
        self._init_ui()
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._animate_hide)

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

        self.success_animation = WritingAnimationWidget()
        layout.addWidget(self.success_animation)
        
        line = QLabel("|")
        line.setStyleSheet("color: #555; border:none; background: transparent;")
        layout.addWidget(line)

        self.btn_fav = QPushButton()
        self.btn_fav.setToolTip("收藏")
        self.btn_fav.setFixedSize(20, 20)
        self.btn_fav.setCursor(Qt.PointingHandCursor)
        self.btn_fav.setStyleSheet("background: transparent; border: none;")
        self.btn_fav.clicked.connect(self._on_fav_clicked)
        layout.addWidget(self.btn_fav)

        self.common_tags_bar = CommonTags(self.service) 
        self.common_tags_bar.tag_clicked.connect(self._on_quick_tag_clicked)
        self.common_tags_bar.manager_requested.connect(self._on_manager_clicked)
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
        idea_data = self.service.get_idea(self.current_idea_id)
        if not idea_data: return
        # 使用字典访问，更安全
        is_favorite = idea_data['is_favorite'] == 1
        active_tags = self.service.get_tags(self.current_idea_id)
        self.common_tags_bar.reload_tags(active_tags)
        if is_favorite: self.btn_fav.setIcon(create_svg_icon("star_filled.svg", COLORS['warning']))
        else: self.btn_fav.setIcon(create_svg_icon("star.svg", "#BBB"))
        self.container.adjustSize()
        self.resize(self.container.size() + QSize(10, 10))

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
        if y < screen_geometry.top(): y = cursor_pos.y() + 25
        if y + self.height() > screen_geometry.bottom(): y = screen_geometry.bottom() - self.height()
        self.move(x, y)
        
        self.show()
        # 【关键修复】激活并强制获取焦点，触发 focusOutEvent 的必要条件
        self.activateWindow()
        self.setFocus()
        
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

    def _on_manager_clicked(self):
        self.request_manager.emit()
        self.hide() 

    def _animate_hide(self):
        self.hide()

    # 失去焦点时立即关闭
    def focusOutEvent(self, event):
        self._animate_hide()
        super().focusOutEvent(event)

    def enterEvent(self, event):
        self.hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        # 鼠标移出后也开始计时，防止一直不关闭
        self.hide_timer.start(1500)
        super().leaveEvent(event)