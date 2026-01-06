# -*- coding: utf-8 -*-
# ui/sidebar.py
import random
import os
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox, QInputDialog, 
                             QFrame, QColorDialog, QDialog, QVBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QHBoxLayout, QApplication, QWidget, QStyle)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QEvent, QTimer, QByteArray
from PyQt5.QtGui import QFont, QColor, QPixmap, QPainter, QIcon, QCursor, QPalette
from core.config import COLORS
from ui.advanced_tag_selector import AdvancedTagSelector

class ClickableLineEdit(QLineEdit):
    doubleClicked = pyqtSignal()
    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)

class Sidebar(QTreeWidget):
    filter_changed = pyqtSignal(str, object)
    data_changed = pyqtSignal()
    new_data_requested = pyqtSignal(int)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setHeaderHidden(True)
        self.setIndentation(15)
        self._icon_cache = {}
        
        # ==========================================
        # 🎨 专业配色方案 (在此处灵活调整颜色)
        # ==========================================
        self._icon_theme_colors = {
            'all_data.svg':      '#3498db',  # 蓝色 - 代表数据库/整体
            'today.svg':         '#2ecc71',  # 绿色 - 代表生机/今日活跃
            'uncategorized.svg': '#e67e22',  # 橙色 - 代表需要整理/注意
            'untagged.svg':      '#95a5a6',  # 蓝灰 - 代表空缺/冷淡
            'favorite.svg':      '#f1c40f',  # 金色 - 代表收藏/星标
            'trash.svg':         '#e74c3c'   # 红色 - 代表警告/删除
        }

        # 内置的高级双色调 SVG
        self._system_icons = {
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
            'favorite.svg': """
                <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M12 17.27L18.18 21L16.54 13.97L22 9.24L14.81 8.62L12 2L9.19 8.62L2 9.24L7.45 13.97L5.82 21L12 17.27Z" fill="currentColor" fill-opacity="0.2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M19 2L20 4L22 5L20 6L19 8L18 6L16 5L18 4L19 2Z" fill="currentColor"/>
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
        
        self.setCursor(Qt.ArrowCursor)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(self.InternalMove)

        # 稍微调整 CSS，让图标和文字更协调
        self.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLORS['bg_mid']};
                color: #e0e0e0;
                border: none;
                font-size: 13px;
                padding: 4px;
                outline: none;
            }}
            QTreeWidget::item {{
                height: 28px; /* 增加高度，给图标留呼吸空间 */
                padding: 1px 4px;
                border-radius: 6px;
                margin-bottom: 2px;
            }}
            QTreeWidget::item:hover {{
                background-color: #2a2d2e;
            }}
            QTreeWidget::item:selected {{
                background-color: #37373d;
                color: white;
            }}
            /* 滚动条样式保持不变 */
            QScrollBar:vertical {{ border: none; background: transparent; width: 6px; margin: 0px; }}
            QScrollBar::handle:vertical {{ background: #444; border-radius: 3px; min-height: 20px; }}
            QScrollBar::handle:vertical:hover {{ background: #555; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)

        self.itemClicked.connect(self._on_click)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self.refresh_sync()

    def _create_svg_icon(self, icon_name):
        # 默认使用文本颜色
        default_color = self.palette().color(QPalette.WindowText).name()

        # 智能着色：检查是否有预定义的专业配色
        # 如果 icon_name 在我们的配色表中，优先使用配色表颜色，否则使用默认文本色
        render_color = self._icon_theme_colors.get(icon_name, default_color)

        cache_key = (icon_name, render_color)

        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        svg_data = ""
        if icon_name in self._system_icons:
            svg_data = self._system_icons[icon_name]

        if not svg_data:
            icon_path = os.path.join("ui", "icons", icon_name)
            if os.path.exists(icon_path):
                try:
                    with open(icon_path, 'r', encoding='utf-8') as f:
                        svg_data = f.read()
                except Exception:
                    pass

        if not svg_data:
            return QIcon()

        # 关键修改：将 currentColor 替换为我们指定的 render_color (可能是彩色，也可能是灰色)
        # 这样 SVG 里的 fill-opacity 就会基于这个颜色生效，形成高级的双色调
        svg_data = svg_data.replace("currentColor", render_color)

        renderer = QSvgRenderer(QByteArray(svg_data.encode('utf-8')))

        icon_size = 20
        pixmap = QPixmap(icon_size, icon_size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        icon = QIcon(pixmap)
        self._icon_cache[cache_key] = icon
        return icon

    def enterEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super().enterEvent(event)

    def refresh(self):
        QTimer.singleShot(10, self.refresh_sync)

    def refresh_sync(self):
        self.blockSignals(True)
        try:
            self.clear()
            self.setColumnCount(1)
            counts = self.db.get_counts()

            # 系统菜单列表
            system_menu_items = [
                ("全部数据", 'all', 'all_data.svg'),
                ("今日数据", 'today', 'today.svg'),
                ("未分类", 'uncategorized', 'uncategorized.svg'),
                ("未标签", 'untagged', 'untagged.svg'),
                ("收藏", 'favorite', 'favorite.svg'),
                ("回收站", 'trash', 'trash.svg')
            ]

            for name, key, icon_filename in system_menu_items:
                item = QTreeWidgetItem(self, [f"{name} ({counts.get(key, 0)})"])
                icon = self._create_svg_icon(icon_filename)
                item.setIcon(0, icon)
                item.setData(0, Qt.UserRole, (key, None))
                item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled) # 禁止拖拽系统图标
                item.setExpanded(False)

            # 分割线
            sep_item = QTreeWidgetItem(self)
            sep_item.setFlags(Qt.NoItemFlags)
            sep_item.setSizeHint(0, QSize(0, 16)) 
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            layout = QVBoxLayout(container)
            layout.setContentsMargins(10, 0, 10, 0)
            layout.setAlignment(Qt.AlignCenter)
            line = QFrame()
            line.setFixedHeight(1) 
            line.setStyleSheet("background-color: #505050; border: none;") 
            layout.addWidget(line)
            self.setItemWidget(sep_item, 0, container)

            # 用户分区
            user_partitions_root = QTreeWidgetItem(self, ["🗃️ 我的分区"])
            user_partitions_root.setFlags(user_partitions_root.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsDragEnabled)
            font = user_partitions_root.font(0)
            font.setBold(True)
            user_partitions_root.setFont(0, font)
            user_partitions_root.setForeground(0, QColor("#FFFFFF"))
            
            partitions_tree = self.db.get_partitions_tree()
            self._add_partition_recursive(partitions_tree, user_partitions_root, counts.get('categories', {}))
            
            self.expandAll()
        finally:
            self.blockSignals(False)

    def _create_color_icon(self, color_str):
        pixmap = QPixmap(14, 14)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        c = QColor(color_str if color_str else "#808080")
        painter.setBrush(c)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(1, 1, 12, 12)
        painter.end()
        return QIcon(pixmap)

    def _add_partition_recursive(self, partitions, parent_item, counts):
        for p in partitions:
            count = counts.get(p.id, 0)
            child_counts = sum(counts.get(child.id, 0) for child in p.children)
            total_count = count + child_counts

            item = QTreeWidgetItem(parent_item, [f"{p.name} ({total_count})"])
            item.setIcon(0, self._create_color_icon(p.color))
            item.setData(0, Qt.UserRole, ('category', p.id))
            
            if p.children:
                self._add_partition_recursive(p.children, item, counts)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat('application/x-tree-widget-internal-move') or \
           e.mimeData().hasFormat('application/x-idea-id') or \
           e.mimeData().hasFormat('application/x-idea-ids'):
            e.accept()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        item = self.itemAt(e.pos())
        if item:
            d = item.data(0, Qt.UserRole)
            if d and d[0] in ['category', 'trash', 'favorite', 'uncategorized']:
                self.setCurrentItem(item)
                e.accept()
                return
            if e.mimeData().hasFormat('application/x-tree-widget-internal-move'):
                e.accept()
                return
        e.ignore()

    def dropEvent(self, e):
        ids_to_process = []
        if e.mimeData().hasFormat('application/x-idea-ids'):
            try:
                data = e.mimeData().data('application/x-idea-ids').data().decode('utf-8')
                ids_to_process = [int(x) for x in data.split(',') if x]
            except Exception: pass
        elif e.mimeData().hasFormat('application/x-idea-id'):
            try: 
                ids_to_process = [int(e.mimeData().data('application/x-idea-id'))]
            except Exception: pass
        
        if ids_to_process:
            try:
                item = self.itemAt(e.pos())
                if not item: return
                d = item.data(0, Qt.UserRole)
                if not d: return
                key, val = d
                
                for iid in ids_to_process:
                    if key == 'category': self.db.move_category(iid, val)
                    elif key == 'uncategorized': self.db.move_category(iid, None)
                    elif key == 'trash': self.db.set_deleted(iid, True)
                    elif key == 'favorite': self.db.set_favorite(iid, True)
                
                self.data_changed.emit()
                self.refresh()
                e.acceptProposedAction()
            except Exception as err:
                pass
        else:
            super().dropEvent(e)
            self._save_current_order()

    def _save_current_order(self):
        update_list = []
        def iterate_items(parent_item, parent_id):
            for i in range(parent_item.childCount()):
                item = parent_item.child(i)
                data = item.data(0, Qt.UserRole)
                if data and data[0] == 'category':
                    cat_id = data[1]
                    update_list.append({'id': cat_id, 'sort_order': i, 'parent_id': parent_id})
                    if item.childCount() > 0:
                        iterate_items(item, cat_id)
        iterate_items(self.invisibleRootItem(), None)
        if update_list:
            self.db.save_category_order(update_list)

    def _on_click(self, item):
        data = item.data(0, Qt.UserRole)
        if data: self.filter_changed.emit(*data)

    def _show_menu(self, pos):
        item = self.itemAt(pos)
        menu = QMenu(self)
        menu.setStyleSheet("background:#2d2d2d;color:white")

        if not item or item.text(0) == "🗃️ 我的分区":
            menu.addAction('➕ 组', self._new_group)
            menu.exec_(self.mapToGlobal(pos))
            return

        data = item.data(0, Qt.UserRole)
        if not data: return

        # 回收站右键菜单
        if data[0] == 'trash':
            menu.addAction('🗑️ 清空回收站', self._empty_trash)
            menu.exec_(self.mapToGlobal(pos))
            return

        if data[0] == 'category':
            cat_id = data[1]
            raw_text = item.text(0)
            current_name = raw_text.split(' (')[0]

            menu.addAction('➕ 数据', lambda: self._request_new_data(cat_id))
            menu.addSeparator()
            menu.addAction('🎨 设置颜色', lambda: self._change_color(cat_id))
            menu.addAction('🎲 随机颜色', lambda: self._set_random_color(cat_id))
            menu.addAction('🏷️ 设置预设标签', lambda: self._set_preset_tags(cat_id))
            menu.addSeparator()
            menu.addAction('➕ 组', self._new_group)
            menu.addAction('➕ 区', lambda: self._new_zone(cat_id))
            menu.addAction('✏️ 重命名', lambda: self._rename_category(cat_id, current_name))
            menu.addAction('🗑️ 删除', lambda: self._del_category(cat_id))
            menu.exec_(self.mapToGlobal(pos))

    def _empty_trash(self):
        if QMessageBox.Yes == QMessageBox.warning(self, '清空回收站', '⚠️ 确定要清空回收站吗？\n此操作将永久删除所有内容，不可恢复！', QMessageBox.Yes | QMessageBox.No):
            self.db.empty_trash()
            self.data_changed.emit()
            self.refresh()

    def _set_preset_tags(self, cat_id):
        current_tags = self.db.get_category_preset_tags(cat_id)
        
        dlg = QDialog(self)
        dlg.setWindowTitle("🏷️ 设置预设标签")
        dlg.setStyleSheet(f"background-color: {COLORS['bg_dark']}; color: #EEE;")
        dlg.setFixedSize(350, 150)
        
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 20, 20, 20)
        
        info = QLabel("拖入该分类时自动绑定以下标签：\n(双击输入框选择历史标签)")
        info.setStyleSheet("color: #888; font-size: 12px; margin-bottom: 5px;")
        layout.addWidget(info)
        
        inp = ClickableLineEdit()
        inp.setText(current_tags)
        inp.setPlaceholderText("例如: 工作, 重要 (逗号分隔)")
        inp.setStyleSheet(f"background-color: {COLORS['bg_mid']}; border: 1px solid #444; padding: 6px; border-radius: 4px; color: white;")
        layout.addWidget(inp)
        
        def open_tag_selector():
            initial_list = [t.strip() for t in inp.text().split(',') if t.strip()]
            selector = AdvancedTagSelector(self.db, idea_id=None, initial_tags=initial_list)
            def on_confirmed(tags):
                inp.setText(', '.join(tags))
            selector.tags_confirmed.connect(on_confirmed)
            selector.show_at_cursor()
            
        inp.doubleClicked.connect(open_tag_selector)
        
        btns = QHBoxLayout()
        btns.addStretch()
        btn_ok = QPushButton("完成")
        btn_ok.setStyleSheet(f"background-color: {COLORS['primary']}; border:none; padding: 5px 15px; border-radius: 4px; font-weight:bold;")
        btn_ok.clicked.connect(dlg.accept)
        btns.addWidget(btn_ok)
        layout.addLayout(btns)
        
        if dlg.exec_() == QDialog.Accepted:
            new_tags = inp.text().strip()
            self.db.set_category_preset_tags(cat_id, new_tags)
            
            tags_list = [t.strip() for t in new_tags.split(',') if t.strip()]
            if tags_list:
                self.db.apply_preset_tags_to_category_items(cat_id, tags_list)
                
            self.data_changed.emit()

    def _change_color(self, cat_id):
        color = QColorDialog.getColor(Qt.gray, self, "选择分类颜色")
        if color.isValid():
            color_name = color.name()
            self.db.set_category_color(cat_id, color_name)
            
            self.refresh()
            self.data_changed.emit()

    def _set_random_color(self, cat_id):
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        color = QColor(r, g, b)
        
        # 确保颜色不会太暗
        while color.lightness() < 80:
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            color = QColor(r, g, b)
            
        color_name = color.name()
        self.db.set_category_color(cat_id, color_name)
        
        self.refresh()
        self.data_changed.emit()

    def _request_new_data(self, cat_id):
        self.new_data_requested.emit(cat_id)

    def _new_group(self):
        text, ok = QInputDialog.getText(self, '新建组', '组名称:')
        if ok and text:
            self.db.add_category(text, parent_id=None)
            self.refresh()
            
    def _new_zone(self, parent_id):
        text, ok = QInputDialog.getText(self, '新建区', '区名称:')
        if ok and text:
            self.db.add_category(text, parent_id=parent_id)
            self.refresh()

    def _rename_category(self, cat_id, old_name):
        text, ok = QInputDialog.getText(self, '重命名', '新名称:', text=old_name)
        if ok and text and text.strip():
            self.db.rename_category(cat_id, text.strip())
            self.refresh()

    def _del_category(self, cid):
        c = self.db.conn.cursor()
        c.execute("SELECT COUNT(*) FROM categories WHERE parent_id = ?", (cid,))
        child_count = c.fetchone()[0]

        msg = '确认删除此分类? (其中的内容将移至未分类)'
        if child_count > 0:
            msg = f'此组包含 {child_count} 个区，确认一并删除?\n(所有内容都将移至未分类)'

        if QMessageBox.Yes == QMessageBox.question(self, '确认删除', msg):
            c.execute("SELECT id FROM categories WHERE parent_id = ?", (cid,))
            child_ids = [row[0] for row in c.fetchall()]
            for child_id in child_ids:
                self.db.delete_category(child_id)
            self.db.delete_category(cid)
            self.refresh()
