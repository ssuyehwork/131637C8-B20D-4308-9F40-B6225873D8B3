# -*- coding: utf-8 -*-
# ui/sidebar.py
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox, QInputDialog, QFrame
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QColor
from core.config import COLORS

class Sidebar(QTreeWidget):
    filter_changed = pyqtSignal(str, object)
    data_changed = pyqtSignal()
    new_data_requested = pyqtSignal(int)

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setHeaderHidden(True)
        self.setIndentation(15)
        
        # --- 拖拽设置 ---
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(self.InternalMove) # 关键：设置为内部拖拽移动

        # 优化样式：极简紧凑布局
        self.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLORS['bg_mid']};
                color: #ddd;
                border: none;
                font-size: 13px;
                padding: 2px;
                outline: none;
            }}
            QTreeWidget::item {{
                height: 24px;
                padding: 1px 4px;
                border-radius: 4px;
                margin-bottom: 0px;
            }}
            QTreeWidget::item:hover {{
                background-color: #2a2d2e;
            }}
            QTreeWidget::item:selected {{
                background-color: #37373d;
                color: white;
            }}
        """)

        self.itemClicked.connect(self._on_click)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self.refresh()

    def refresh(self):
        self.clear()
        self.setColumnCount(1)
        counts = self.db.get_counts()

        # --- 1. 固定的系统分类 ---
        system_menu_items = [
            ("全部数据", 'all', '🗂️'), ("今日数据", 'today', '📅'),
            ("剪贴板数据", 'clipboard', '📋'),
            ("未分类", 'uncategorized', '⚠️'), ("未标签", 'untagged', '🏷️'),
            ("收藏", 'favorite', '⭐'), ("回收站", 'trash', '🗑️')
        ]

        for name, key, icon in system_menu_items:
            item = QTreeWidgetItem(self, [f"{icon}  {name} ({counts.get(key, 0)})"])
            item.setData(0, Qt.UserRole, (key, None))
            # 系统项不可拖拽、不可折叠
            item.setFlags(item.flags() & ~Qt.ItemIsDragEnabled)
            item.setExpanded(False)

        # --- 2. 分割线 ---
        sep_item = QTreeWidgetItem(self)
        sep_item.setFlags(Qt.NoItemFlags)
        sep_item.setSizeHint(0, QSize(0, 15))
        line_frame = QFrame()
        line_frame.setFixedHeight(1)
        line_frame.setStyleSheet(f"background-color: {COLORS['bg_light']}; margin: 0px 8px;")
        self.setItemWidget(sep_item, 0, line_frame)

        # --- 3. 用户自定义分区 ---
        user_partitions_root = QTreeWidgetItem(self, ["🗃️ 我的分区"])
        user_partitions_root.setFlags(user_partitions_root.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsDragEnabled)
        font = user_partitions_root.font(0)
        font.setBold(True)
        user_partitions_root.setFont(0, font)
        user_partitions_root.setForeground(0, QColor("#FFFFFF"))
        
        partitions_tree = self.db.get_partitions_tree()
        self._add_partition_recursive(partitions_tree, user_partitions_root, counts.get('categories', {}))
        
        self.expandAll()

    def _add_partition_recursive(self, partitions, parent_item, counts):
        for p in partitions:
            count = counts.get(p.id, 0)
            # 子项也需要计入父项的总数
            child_counts = sum(counts.get(child.id, 0) for child in p.children)
            total_count = count + child_counts

            icon = "📦" if not p.children else "🗃️"  # 更改图标以区分
            item = QTreeWidgetItem(parent_item, [f"{icon} {p.name} ({total_count})"])
            item.setData(0, Qt.UserRole, ('category', p.id))
            
            if p.children:
                self._add_partition_recursive(p.children, item, counts)

    # --- 其余逻辑保持不变 ---
    def dragEnterEvent(self, e):
        # 同时接受内部移动和外部笔记拖入
        if e.mimeData().hasFormat('application/x-tree-widget-internal-move') or \
           e.mimeData().hasFormat('application/x-idea-id'):
            e.accept()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        item = self.itemAt(e.pos())
        if item:
            d = item.data(0, Qt.UserRole)
            # 允许拖放到分类、回收站、收藏和未分类
            if d and d[0] in ['category', 'trash', 'favorite', 'uncategorized']:
                self.setCurrentItem(item)
                e.accept()
                return
            # 如果是内部移动，也允许
            if e.mimeData().hasFormat('application/x-tree-widget-internal-move'):
                e.accept()
                return
        e.ignore()

    def dropEvent(self, e):
        # 优先判断是否是外部拖入的笔记
        if e.mimeData().hasFormat('application/x-idea-id'):
            try:
                iid = int(e.mimeData().data('application/x-idea-id'))
                item = self.itemAt(e.pos())
                if not item: return
                d = item.data(0, Qt.UserRole)
                if not d: return
                key, val = d
                if key == 'category': self.db.move_category(iid, val)
                elif key == 'uncategorized': self.db.move_category(iid, None)
                elif key == 'trash': self.db.set_deleted(iid, True)
                elif key == 'favorite': self.db.set_favorite(iid, True)
                self.data_changed.emit()
                self.refresh()
                e.acceptProposedAction()
            except Exception as err:
                print(f"Drop error: {err}")
        else:
            # 如果不是笔记，则认为是内部排序
            super().dropEvent(e)
            self._save_current_order()


    def _save_current_order(self):
        """遍历TreeWidget，保存所有自定义分类的顺序和父子关系"""
        update_list = []
        
        def iterate_items(parent_item, parent_id):
            for i in range(parent_item.childCount()):
                item = parent_item.child(i)
                data = item.data(0, Qt.UserRole)
                if data and data[0] == 'category':
                    cat_id = data[1]
                    # 记录ID、新顺序和新的父ID
                    update_list.append({'id': cat_id, 'sort_order': i, 'parent_id': parent_id})
                    if item.childCount() > 0:
                        iterate_items(item, cat_id) # 递归，传入当前项的ID作为父ID
                        
        # 从 invisibleRootItem 开始遍历，其父ID为 None
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

        # Case 1: 点击空白处，或 "我的分区" 标题
        if not item or item.text(0) == "🗃️ 我的分区":
            menu.addAction('➕ 组', self._new_group)
            menu.exec_(self.mapToGlobal(pos))
            return

        # Case 2: 点击的是用户创建的分类
        data = item.data(0, Qt.UserRole)
        if data and data[0] == 'category':
            cat_id = data[1]
            raw_text = item.text(0)
            current_name = ' '.join(raw_text.split(' ')[:-1]).strip()[2:]

            menu.addAction('➕ 数据', lambda: self._request_new_data(cat_id))
            menu.addSeparator()
            menu.addAction('➕ 组', self._new_group)
            menu.addAction('➕ 区', lambda: self._new_zone(cat_id))
            menu.addAction('✏️ 重命名', lambda: self._rename_category(cat_id, current_name))
            menu.addAction('🗑️ 删除', lambda: self._del_category(cat_id))
            menu.exec_(self.mapToGlobal(pos))
        
        # Case 3: 点击系统分类，不显示菜单
        # (do nothing)

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
        # 增加判断，看是否有子分类
        c = self.db.conn.cursor()
        c.execute("SELECT COUNT(*) FROM categories WHERE parent_id = ?", (cid,))
        child_count = c.fetchone()[0]

        msg = '确认删除此分类? (其中的内容将移至未分类)'
        if child_count > 0:
            msg = f'此组包含 {child_count} 个区，确认一并删除?\n(所有内容都将移至未分类)'

        if QMessageBox.Yes == QMessageBox.question(self, '确认删除', msg):
            # 删除子分类
            c.execute("SELECT id FROM categories WHERE parent_id = ?", (cid,))
            child_ids = [row[0] for row in c.fetchall()]
            for child_id in child_ids:
                self.db.delete_category(child_id)
            # 删除父分类
            self.db.delete_category(cid)
            self.refresh()
