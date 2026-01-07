# -*- coding: utf-8 -*-
# ui/filter_panel.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, 
                             QTreeWidgetItem, QPushButton, QLabel, QFrame, QApplication, QMenu)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QMimeData, QPoint
from PyQt5.QtGui import QDrag, QPixmap, QPainter, QCursor
from core.config import COLORS
from core.shared import get_color_icon
from ui.utils import create_svg_icon
import logging

log = logging.getLogger("FilterPanel")

class FilterPanel(QWidget):
    filterChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 自身样式
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {COLORS['bg_dark']}; border-top: 1px solid {COLORS['bg_light']};")

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 8, 15, 8)
        self.layout.setSpacing(10)
        
        # 1. 筛选器按钮
        self.buttons = {}
        button_style = f"""
            QPushButton {{
                background-color: {COLORS['bg_mid']};
                border: 1px solid #444;
                color: #AAA;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: #FFF;
                background-color: #333;
            }}
            QPushButton[isChecked="true"] {{
                background-color: {COLORS['primary']};
                color: white;
                font-weight: bold;
                border: 1px solid {COLORS['primary']};
            }}
        """
        
        order = [
            ('stars', '⭐  评级'),
            ('colors', '🎨  颜色'),
            ('types', '📂  类型'),
            ('date_create', '📅  创建时间'),
            ('tags', '🏷️  标签'),
        ]

        for key, label in order:
            btn = QPushButton(label.split('  ')[1])
            btn.setStyleSheet(button_style)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setProperty("isChecked", False)
            btn.clicked.connect(lambda _, k=key: self._show_filter_menu(k))
            self.buttons[key] = btn
            self.layout.addWidget(btn)

        self.layout.addStretch(1)

        # 2. 面包屑标签
        self.breadcrumb_label = QLabel("无筛选")
        self.breadcrumb_label.setStyleSheet("color: #777; font-size: 11px;")
        self.layout.addWidget(self.breadcrumb_label)
        
        # 3. 重置按钮
        self.btn_reset = QPushButton()
        self.btn_reset.setIcon(create_svg_icon("action_delete.svg", "#888"))
        self.btn_reset.setFixedSize(28, 28)
        self.btn_reset.setToolTip("重置所有筛选")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{ background-color: transparent; border-radius: 6px; }}
            QPushButton:hover {{ background-color: {COLORS['bg_light']}; }}
        """)
        self.btn_reset.clicked.connect(self.reset_filters)
        self.layout.addWidget(self.btn_reset)

        # --- 内部数据结构 ---
        self.tree = QTreeWidget() # 保持 tree 的逻辑，但不显示
        self.tree.hide()
        self.tree.itemChanged.connect(self._on_item_changed)

        self._block_item_click = False
        self.roots = {}
        
        # 定义结构
        order = [
            ('stars', '⭐  评级'),
            ('colors', '🎨  颜色'),
            ('types', '📂  类型'),
            ('date_create', '📅  创建时间'),
            ('tags', '🏷️  标签'),
        ]
        
        font_header = self.tree.font()
        font_header.setBold(True)
        
        for key, label in order:
            item = QTreeWidgetItem(self.tree)
            item.setText(0, label)
            item.setExpanded(True)
            item.setFlags(Qt.ItemIsEnabled) 
            item.setFont(0, font_header)
            item.setForeground(0, Qt.gray)
            self.roots[key] = item
            
        self._add_fixed_date_options('date_create')

    def _add_fixed_date_options(self, key):
        root = self.roots[key]
        options = [("today", "今日"), ("yesterday", "昨日"), ("week", "本周"), ("month", "本月")]
        for key_val, label in options:
            child = QTreeWidgetItem(root)
            child.setText(0, f"{label} (0)")
            child.setData(0, Qt.UserRole, key_val)
            child.setCheckState(0, Qt.Unchecked)

    def _show_filter_menu(self, key):
        btn = self.buttons[key]
        root = self.roots[key]

        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['bg_mid']};
                color: white;
                border: 1px solid {COLORS['bg_light']};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['primary']};
            }}
        """)

        for i in range(root.childCount()):
            child = root.child(i)
            action = menu.addAction(child.text(0))
            action.setCheckable(True)
            action.setChecked(child.checkState(0) == Qt.Checked)

            # 使用 lambda 捕获正确的 child item
            action.triggered.connect(lambda checked, item=child: self._on_menu_action_triggered(item, checked))

        # 计算菜单显示位置
        pos = btn.mapToGlobal(QPoint(0, btn.height()))
        menu.exec_(pos)

    def _on_menu_action_triggered(self, item, checked):
        # 这个方法用于同步 QMenu 的勾选状态到 QTreeWidget
        self._block_item_click = True
        item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
        self._block_item_click = False
        self.filterChanged.emit() # 手动触发，因为 itemChanged 被 block 了

    def _on_item_changed(self, item, col):
        if self._block_item_click: return
        self._update_ui_states()
        self.filterChanged.emit()

    def _update_ui_states(self):
        all_checked_texts = []
        for key, root in self.roots.items():
            has_checked = False
            for i in range(root.childCount()):
                child = root.child(i)
                if child.checkState(0) == Qt.Checked:
                    has_checked = True
                    text_only = child.text(0).split(' (')[0]
                    all_checked_texts.append(f"✓ {text_only}")

            btn = self.buttons.get(key)
            if btn:
                btn.setProperty("isChecked", has_checked)
                btn.style().polish(btn)

        if all_checked_texts:
            self.breadcrumb_label.setText(" · ".join(all_checked_texts))
        else:
            self.breadcrumb_label.setText("无筛选")

    def update_stats(self, stats):
        self.tree.blockSignals(True)
        self._block_item_click = True
        
        star_data = []
        for i in range(5, 0, -1):
            c = stats['stars'].get(i, 0)
            if c > 0: star_data.append((i, "★" * i, c))
        if stats['stars'].get(0, 0) > 0:
            star_data.append((0, "无评级", stats['stars'][0]))
        self._refresh_node('stars', star_data)

        color_data = []
        for c_hex, count in stats['colors'].items():
            if count > 0:
                color_data.append((c_hex, c_hex, count)) 
        self._refresh_node('colors', color_data, is_col=True)
        
        tag_data = []
        for name, count in stats.get('tags', []):
            tag_data.append((name, name, count))
        self._refresh_node('tags', tag_data)
        
        self._update_fixed_node('date_create', stats.get('date_create', {}))
        
        type_map = {'text': '文本', 'image': '图片', 'file': '文件'}
        type_data = []
        for t, count in stats.get('types', {}).items():
            if count > 0:
                type_data.append((t, type_map.get(t, t), count))
        self._refresh_node('types', type_data)
        
        self._block_item_click = False
        self.tree.blockSignals(False)
        self._update_ui_states()

    def _refresh_node(self, key, data_list, is_col=False):
        root = self.roots[key]
        checked_map = {}
        for i in range(root.childCount()):
            child = root.child(i)
            val = child.data(0, Qt.UserRole)
            checked_map[val] = child.checkState(0)
            
        root.takeChildren()
        
        for value, label, count in data_list:
            child = QTreeWidgetItem(root)
            child.setText(0, f"{label} ({count})")
            child.setData(0, Qt.UserRole, value)
            child.setCheckState(0, checked_map.get(value, Qt.Unchecked))
            
            if is_col:
                child.setIcon(0, get_color_icon(value))
                child.setText(0, f" {count}") 

    def _update_fixed_node(self, key, stats_dict):
        root = self.roots[key]
        labels = {"today": "今日", "yesterday": "昨日", "week": "本周", "month": "本月"}
        for i in range(root.childCount()):
            child = root.child(i)
            val = child.data(0, Qt.UserRole) 
            count = stats_dict.get(val, 0)
            child.setText(0, f"{labels.get(val, val)} ({count})")

    def get_checked_criteria(self):
        criteria = {}
        for key, root in self.roots.items():
            checked_values = []
            for i in range(root.childCount()):
                child = root.child(i)
                if child.checkState(0) == Qt.Checked:
                    checked_values.append(child.data(0, Qt.UserRole))
            if checked_values:
                criteria[key] = checked_values
        return criteria

    def reset_filters(self):
        self.tree.blockSignals(True)
        for key, root in self.roots.items():
            for i in range(root.childCount()):
                root.child(i).setCheckState(0, Qt.Unchecked)
        self.tree.blockSignals(False)
        self._update_ui_states()
        self.filterChanged.emit()