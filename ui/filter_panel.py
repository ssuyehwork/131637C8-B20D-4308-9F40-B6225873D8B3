# -*- coding: utf-8 -*-
# ui/filter_panel.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from core.config import COLORS
from core.shared import get_color_icon
import logging

log = logging.getLogger("FilterPanel")

class FilterPanel(QWidget):
    filterChanged = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setFocusPolicy(Qt.NoFocus)
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setAnimated(True)
        self.tree.setAllColumnsShowFocus(True)
        
        # 样式美化，保持与 Sidebar 一致
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLORS['bg_mid']};
                color: #ddd;
                border: none;
                font-size: 13px;
            }}
            QTreeWidget::item {{
                height: 26px;
                border-radius: 4px;
                padding-right: 5px;
            }}
            QTreeWidget::item:hover {{ background-color: #2a2d2e; }}
            QTreeWidget::item:selected {{ background-color: #37373d; color: white; }}
        """)
        
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.layout.addWidget(self.tree)
        
        # 重置按钮样式
        self.btn_reset = QPushButton("重置筛选")
        self.btn_reset.setCursor(Qt.PointingHandCursor)
        self.btn_reset.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_dark']};
                border: 1px solid #444;
                color: #888;
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }}
            QPushButton:hover {{ color: #ddd; background-color: #333; }}
        """)
        self.btn_reset.clicked.connect(self.reset_filters)
        self.layout.addWidget(self.btn_reset)

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
            # 根节点不可选中，只作为标题容器
            item.setFlags(Qt.ItemIsEnabled) 
            item.setFont(0, font_header)
            item.setForeground(0, Qt.gray)
            self.roots[key] = item
            
        self._add_fixed_date_options('date_create')

    def _add_fixed_date_options(self, key):
        root = self.roots[key]
        # 对应 DB 的 filter key
        options = [("today", "今日"), ("yesterday", "昨日"), ("week", "本周"), ("month", "本月")]
        for key_val, label in options:
            child = QTreeWidgetItem(root)
            child.setText(0, f"{label} (0)")
            child.setData(0, Qt.UserRole, key_val)
            child.setCheckState(0, Qt.Unchecked)

    def _on_item_changed(self, item, col):
        if self._block_item_click: return
        self.filterChanged.emit()

    def _on_item_clicked(self, item, column):
        # 根节点折叠逻辑
        if item.parent() is None:
            item.setExpanded(not item.isExpanded())
        # 子节点勾选逻辑
        elif item.flags() & Qt.ItemIsUserCheckable:
            # 简单的防抖动
            self._block_item_click = True
            state = item.checkState(0)
            item.setCheckState(0, Qt.Unchecked if state == Qt.Checked else Qt.Checked)
            self._block_item_click = False
            self.filterChanged.emit()

    def update_stats(self, stats):
        self.tree.blockSignals(True)
        self._block_item_click = True
        
        # 1. 星级
        star_data = []
        for i in range(5, 0, -1):
            c = stats['stars'].get(i, 0)
            if c > 0: star_data.append((i, "★" * i, c))
        # 0星通常不展示或者叫"无评级"
        if stats['stars'].get(0, 0) > 0:
            star_data.append((0, "无评级", stats['stars'][0]))
        self._refresh_node('stars', star_data)

        # 2. 颜色
        # 转换颜色字典为列表
        color_data = []
        for c_hex, count in stats['colors'].items():
            if count > 0:
                color_data.append((c_hex, c_hex, count)) # label暂时用hex，或者你可以映射颜色名
        self._refresh_node('colors', color_data, is_col=True)
        
        # 3. 标签 (tags 是列表 [(name, count), ...])
        tag_data = []
        for name, count in stats.get('tags', []):
            tag_data.append((name, name, count))
        self._refresh_node('tags', tag_data)
        
        # 4. 日期 (固定选项，只更新数字)
        self._update_fixed_node('date_create', stats.get('date_create', {}))
        
        # 5. 类型
        type_map = {'text': '文本', 'image': '图片', 'file': '文件'}
        type_data = []
        for t, count in stats.get('types', {}).items():
            if count > 0:
                type_data.append((t, type_map.get(t, t), count))
        self._refresh_node('types', type_data)
        
        self._block_item_click = False
        self.tree.blockSignals(False)

    def _refresh_node(self, key, data_list, is_col=False):
        """
        动态刷新子节点，保持勾选状态
        data_list: [(value, display_label, count), ...]
        """
        root = self.roots[key]
        
        # 1. 保存当前勾选状态 {value: check_state}
        checked_map = {}
        for i in range(root.childCount()):
            child = root.child(i)
            val = child.data(0, Qt.UserRole)
            checked_map[val] = child.checkState(0)
            
        # 2. 清除旧节点 (简单粗暴，或者你可以做更复杂的 diff 更新)
        root.takeChildren()
        
        # 3. 重建节点
        for value, label, count in data_list:
            child = QTreeWidgetItem(root)
            child.setText(0, f"{label} ({count})")
            child.setData(0, Qt.UserRole, value)
            # 恢复勾选，默认未勾选
            child.setCheckState(0, checked_map.get(value, Qt.Unchecked))
            
            if is_col:
                child.setIcon(0, get_color_icon(value))
                child.setText(0, f" {count}") # 颜色只显示数量，省空间

    def _update_fixed_node(self, key, stats_dict):
        """更新固定选项的计数（如日期）"""
        root = self.roots[key]
        labels = {"today": "今日", "yesterday": "昨日", "week": "本周", "month": "本月"}
        for i in range(root.childCount()):
            child = root.child(i)
            val = child.data(0, Qt.UserRole) # e.g. 'today'
            count = stats_dict.get(val, 0)
            child.setText(0, f"{labels.get(val, val)} ({count})")

    def get_checked_criteria(self):
        """获取所有筛选条件"""
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
        self.filterChanged.emit()