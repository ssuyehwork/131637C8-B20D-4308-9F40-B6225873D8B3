# -*- coding: utf-8 -*-
# ui/cards.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QColor, QPainter, QBrush, QPen, QLinearGradient
from domain.entities import Idea

class IdeaCard(QWidget):
    selection_requested = pyqtSignal(int, bool, bool)
    double_clicked = pyqtSignal(int)

    def __init__(self, idea_entity: Idea, parent=None):
        super().__init__(parent)
        self.idea = idea_entity
        self.is_selected = False
        
        self.setMinimumHeight(120)
        self.setFixedWidth(300) # Initial width, will be adjusted by layout
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Color bar
        self.color_bar = QFrame()
        self.color_bar.setFixedWidth(5)
        
        # Content layout
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 10, 12, 10)
        content_layout.setSpacing(6)
        
        # Title
        self.title = QLabel()
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-size: 14px; font-weight: bold; color: #e0e0e0;")
        
        # Content snippet
        self.content = QLabel()
        self.content.setWordWrap(True)
        self.content.setStyleSheet("font-size: 12px; color: #a0a0a0;")
        
        # Footer layout (for icons and tags)
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 5, 0, 0)
        
        self.icon_area = QLabel() # To display icons like pin, lock, bookmark
        self.rating_area = QLabel() # To display stars
        
        footer_layout.addWidget(self.icon_area)
        footer_layout.addWidget(self.rating_area)
        footer_layout.addStretch()
        
        content_layout.addWidget(self.title)
        content_layout.addWidget(self.content)
        content_layout.addStretch()
        content_layout.addLayout(footer_layout)
        
        # Combine color bar and content
        body_layout = QHBoxLayout()
        body_layout.setContentsMargins(0,0,0,0); body_layout.setSpacing(0)
        body_layout.addWidget(self.color_bar)
        body_layout.addWidget(content_widget, 1)
        
        main_layout.addLayout(body_layout)
        
        self.update_data(self.idea)

    def update_data(self, idea_entity: Idea):
        self.idea = idea_entity
        
        self.title.setText(self.idea.title)
        
        # Generate a concise content snippet
        snippet = self.idea.content.replace('\n', ' ').strip()
        if len(snippet) > 100:
            snippet = snippet[:100] + '...'
        self.content.setText(snippet)
        
        # Update color bar and background based on idea color
        base_color = QColor(self.idea.color)
        self.color_bar.setStyleSheet(f"background-color: {base_color.name()};")
        
        # Update icons
        icons_str = ""
        if self.idea.is_pinned: icons_str += "📌 "
        if self.idea.is_locked: icons_str += "🔒 "
        if self.idea.is_favorite: icons_str += "⭐ " # Using star for bookmark for simplicity
        self.icon_area.setText(icons_str)
        
        # Update rating
        rating_str = '★' * self.idea.rating + '☆' * (5 - self.idea.rating)
        self.rating_area.setText(rating_str)
        self.rating_area.setStyleSheet(f"color: {COLORS.get('star', '#FFD700')};")

        self.update_selection(self.is_selected) # Refresh visual state

    def update_selection(self, is_selected):
        self.is_selected = is_selected
        if self.is_selected:
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {COLORS['bg_light']};
                    border: 1px solid {COLORS['primary']};
                    border-radius: 6px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {COLORS['bg_mid']};
                    border: 1px solid {COLORS['bg_light']};
                    border-radius: 6px;
                }}
                QWidget:hover {{
                    background-color: #3a3a3a;
                }}
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            is_ctrl = event.modifiers() & Qt.ControlModifier
            is_shift = event.modifiers() & Qt.ShiftModifier
            self.selection_requested.emit(self.idea.id, bool(is_ctrl), bool(is_shift))
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.idea.id)
        super().mouseDoubleClickEvent(event)
