# -*- coding: utf-8 -*-
# ui/cards.py
import sys
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QApplication
from PyQt5.QtCore import Qt, pyqtSignal, QMimeData
from PyQt5.QtGui import QDrag
from core.config import STYLES

class IdeaCard(QFrame):
    selection_requested = pyqtSignal(int, bool)
    double_clicked = pyqtSignal(int)

    def __init__(self, data, db, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground)
        
        self.data = data
        self.db = db
        self.id = data[0]
        self.setCursor(Qt.PointingHandCursor)
        
        # --- 状态变量 ---
        self._drag_start_pos = None
        self._is_potential_click = False
        
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(8)
        
        top = QHBoxLayout()
        top.setSpacing(8)
        
        title = QLabel(self.data[1])
        title.setStyleSheet("font-size:16px; font-weight:bold; background:transparent; color:white;")
        title.setWordWrap(True)
        top.addWidget(title, stretch=1)
        
        icon_layout = QHBoxLayout()
        icon_layout.setSpacing(4)
        if self.data[4]:  # is_pinned
            pin_icon = QLabel('📌')
            pin_icon.setStyleSheet("background:transparent; font-size:14px;")
            icon_layout.addWidget(pin_icon)
        if self.data[5]:  # is_favorite
            fav_icon = QLabel('⭐')
            fav_icon.setStyleSheet("background:transparent; font-size:14px;")
            icon_layout.addWidget(fav_icon)
            
        top.addLayout(icon_layout)
        layout.addLayout(top)
        
        if self.data[2]:
            content_preview = self.data[2].strip()
            lines = content_preview.split('\n')
            first_para = lines[0] if lines else ""
            
            if len(first_para) > 80:
                preview_text = first_para[:80] + '...'
            elif len(lines) > 1:
                preview_text = first_para + '...'
            else:
                preview_text = first_para
                
            content = QLabel(preview_text.replace('\n', ' '))
            content.setStyleSheet("""
                color:rgba(255,255,255,180); 
                margin-top:2px; 
                background:transparent; 
                font-size:13px;
                line-height:1.4;
            """)
            content.setWordWrap(True)
            content.setMaximumHeight(60)
            layout.addWidget(content)
            
        bot = QHBoxLayout()
        bot.setSpacing(6)
        
        time_str = self.data[7][:16]
        time_label = QLabel(f'🕒 {time_str}')
        time_label.setStyleSheet("color:rgba(255,255,255,120); font-size:11px; background:transparent;")
        bot.addWidget(time_label)
        
        bot.addStretch()
        
        tags = self.db.get_tags(self.id)
        visible_tags = tags[:3]
        remaining = len(tags) - 3
        
        for tag in visible_tags:
            tag_label = QLabel(f"#{tag}")
            tag_label.setStyleSheet("""
                background:rgba(0,0,0,50); 
                border-radius:8px; 
                padding:3px 8px; 
                font-size:10px; 
                color:rgba(255,255,255,200);
                font-weight:bold;
            """)
            bot.addWidget(tag_label)
            
        if remaining > 0:
            more_label = QLabel(f'+{remaining}')
            more_label.setStyleSheet("""
                background:rgba(74,144,226,0.3); 
                border-radius:8px; 
                padding:3px 6px; 
                font-size:10px; 
                color:#4a90e2;
                font-weight:bold;
            """)
            bot.addWidget(more_label)
            
        layout.addLayout(bot)
        self.update_selection(False)

    def update_selection(self, selected):
        bg_color = self.data[3]
        
        if selected:
            # 当被选中时,无论是否悬停,都保持白色边框
            style = f"""
                IdeaCard {{
                    background-color: {bg_color};
                    {STYLES['card_base']}
                    border: 2px solid white;
                    padding: 0px;
                }}
                IdeaCard:hover {{
                    border: 2px solid white; /* 覆盖默认的hover效果 */
                }}
            """
        else:
            # 未选中时的默认行为
            style = f"""
                IdeaCard {{
                    background-color: {bg_color};
                    {STYLES['card_base']}
                    border: 1px solid rgba(255,255,255,0.1);
                    padding: 0px;
                }}
                IdeaCard:hover {{
                    border: 2px solid rgba(255,255,255,0.4);
                }}
            """
            
        # 通用的QLabel样式,避免重复
        style += """
            QLabel {
                background-color: transparent;
                border: none;
            }
        """
        self.setStyleSheet(style)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_start_pos = e.pos()
            self._is_potential_click = True
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.LeftButton) or not self._drag_start_pos:
            return
        
        if (e.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
        
        # Drag started, so it's not a click anymore
        self._is_potential_click = False
        
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData('application/x-idea-id', str(self.id).encode())
        drag.setMimeData(mime)
        
        pixmap = self.grab().scaledToWidth(200, Qt.SmoothTransformation)
        drag.setPixmap(pixmap)
        drag.setHotSpot(e.pos())
        
        drag.exec_(Qt.MoveAction)
        
    def mouseReleaseEvent(self, e):
        if self._is_potential_click and e.button() == Qt.LeftButton:
            is_ctrl_pressed = QApplication.keyboardModifiers() == Qt.ControlModifier
            self.selection_requested.emit(self.id, is_ctrl_pressed)

        self._drag_start_pos = None
        self._is_potential_click = False
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.double_clicked.emit(self.id)
        super().mouseDoubleClickEvent(e)
