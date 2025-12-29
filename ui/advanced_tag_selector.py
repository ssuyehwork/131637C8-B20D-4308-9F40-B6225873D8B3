# -*- coding: utf-8 -*-
# ui/advanced_tag_selector.py

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLineEdit, QScrollArea, QLabel, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QCursor, QFont
from core.config import COLORS

class AdvancedTagSelector(QWidget):
    """一个功能更强大的悬浮标签选择面板"""
    tags_confirmed = pyqtSignal(list)

    def __init__(self, db, idea_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.idea_id = idea_id
        
        self.selected_tags = set()
        self.tag_widgets = {}
        self._is_closing = False # 添加一个状态标志，防止重复关闭

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._init_ui()
        self._load_tags()
        
        # 连接全局焦点变化信号
        QApplication.instance().focusChanged.connect(self._on_focus_changed)

    def _init_ui(self):
        """初始化UI界面"""
        container = QWidget()
        container.setObjectName("mainContainer")
        container.setStyleSheet(f"""
            #mainContainer {{
                background-color: #282828;
                border: 1px solid #444;
                border-radius: 8px;
                color: #EEE;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索标签...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #3C3C3C; border: 1px solid #555;
                border-radius: 6px; padding: 7px 10px; font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {COLORS['primary']}; }}
        """)
        self.search_input.textChanged.connect(self._filter_tags)
        layout.addWidget(self.search_input)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                border: none; background: #3C3C3C; width: 8px;
                margin: 0; border-radius: 4px;
            }
            QScrollBar::handle:vertical { background: #555; min-height: 25px; border-radius: 4px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 5, 0, 5)
        self.scroll_layout.setSpacing(12)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        
        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll)
        
        self.setFixedSize(320, 480)

    def _load_tags(self):
        """从数据库加载并显示标签"""
        self.selected_tags = set(self.db.get_tags(self.idea_id))
        c = self.db.conn.cursor()
        c.execute('''
            SELECT t.name, COUNT(it.idea_id) as cnt
            FROM tags t
            LEFT JOIN idea_tags it ON t.id = it.tag_id
            JOIN ideas i ON it.idea_id = i.id AND i.is_deleted = 0
            GROUP BY t.id ORDER BY cnt DESC, t.name ASC
        ''')
        all_tags = c.fetchall()
        
        top_tags = all_tags[:12]
        other_tags = all_tags[12:]
        
        if top_tags:
            self._create_group("最近使用", top_tags)
        if other_tags:
            self._create_group("其它", other_tags)
        
        self._filter_tags()

    def _create_group(self, title, tags):
        """创建标签分组的UI"""
        group_container = QWidget()
        group_layout = QVBoxLayout(group_container)
        group_layout.setContentsMargins(0,0,0,0)
        group_layout.setSpacing(8)

        group_label = QLabel(f"{title} ({len(tags)})")
        group_label.setStyleSheet("color: #AAA; font-size: 12px; margin-top: 5px; margin-bottom: 2px;")
        group_layout.addWidget(group_label)
        
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0,0,0,0)
        grid.setSpacing(8)
        
        row, col = 0, 0
        for name, count in tags:
            btn_text = f"{name} ({count})"
            if name in self.selected_tags:
                btn_text = f"✓ {btn_text}"
            
            btn = QPushButton(btn_text)
            btn.setCheckable(True)
            btn.setChecked(name in self.selected_tags)
            btn.setStyleSheet(self._get_button_style(btn.isChecked()))
            btn.toggled.connect(lambda checked, b=btn, n=name: self._on_tag_toggled(b, n, checked))
            
            grid.addWidget(btn, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1
            
            self.tag_widgets[name] = {"button": btn, "group": group_container, "group_label": group_label}
        
        group_layout.addWidget(grid_widget)
        self.scroll_layout.addWidget(group_container)
        
    def _on_tag_toggled(self, button, name, checked):
        """处理标签按钮的点击事件"""
        button.setStyleSheet(self._get_button_style(checked))
        count_text = f"({button.text().split('(')[-1]}"
        base_text = f"{name} {count_text}"

        if checked:
            self.selected_tags.add(name)
            button.setText(f"✓ {base_text}")
        else:
            self.selected_tags.discard(name)
            button.setText(base_text)

    def _filter_tags(self):
        """根据搜索框内容过滤标签"""
        term = self.search_input.text().lower()
        visible_tags_in_group = {}

        for name, widgets in self.tag_widgets.items():
            button, group_label = widgets["button"], widgets["group_label"]
            if group_label not in visible_tags_in_group:
                visible_tags_in_group[group_label] = 0
            if term in name.lower():
                button.show()
                visible_tags_in_group[group_label] += 1
            else:
                button.hide()
        
        for name, widgets in self.tag_widgets.items():
             group_container, group_label = widgets["group"], widgets["group_label"]
             if visible_tags_in_group.get(group_label, 0) > 0:
                 group_container.show()
             else:
                 group_container.hide()

    def _get_button_style(self, checked):
        base_style = """
            QPushButton {{
                border-radius: 6px; padding: 7px; text-align: left;
                font-size: 13px; border: 1px solid {border_color};
                background-color: {bg_color}; color: {text_color};
            }}
            QPushButton:hover {{
                background-color: #4A4A4A; border-color: #666;
            }}
        """
        if checked:
            return base_style.format(bg_color=COLORS['primary'], border_color=COLORS['primary'], text_color='white')
        else:
            return base_style.format(bg_color="#3C3C3C", border_color="#555", text_color="#DDD")

    def _save_tags(self):
        """将最终选择的标签保存到数据库"""
        c = self.db.conn.cursor()
        c.execute('DELETE FROM idea_tags WHERE idea_id = ?', (self.idea_id,))
        for tag_name in self.selected_tags:
            c.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag_name,))
            c.execute('SELECT id FROM tags WHERE name = ?', (tag_name,))
            result = c.fetchone()
            if result:
                tag_id = result[0]
                c.execute('INSERT INTO idea_tags (idea_id, tag_id) VALUES (?, ?)', (self.idea_id, tag_id))
        self.db.conn.commit()

    def _is_child_widget(self, widget):
        """检查一个控件是否是此面板的子控件"""
        if widget is None:
            return False
        
        current = widget
        while current:
            if current is self:
                return True
            current = current.parent()
        return False

    def _on_focus_changed(self, old_widget, new_widget):
        """全局焦点变化事件处理器"""
        if self._is_closing or not self.isVisible():
            return
        
        # 如果新的焦点不在这个面板内部，则触发关闭
        if not self._is_child_widget(new_widget):
            self._handle_close()

    def _handle_close(self):
        """封装关闭逻辑"""
        if self._is_closing:
            return
        self._is_closing = True
        
        # 先断开信号连接，避免重复触发
        QApplication.instance().focusChanged.disconnect(self._on_focus_changed)
        
        self._save_tags()
        self.tags_confirmed.emit(list(self.selected_tags))
        self.close()

    def show_at_cursor(self):
        cursor_pos = QCursor.pos()
        screen_geo = QApplication.desktop().screenGeometry()
        x, y = cursor_pos.x() + 15, cursor_pos.y() + 15
        if x + self.width() > screen_geo.right(): x = cursor_pos.x() - self.width() - 15
        if y + self.height() > screen_geo.bottom(): y = screen_geo.bottom() - self.height() - 15
        self.move(x, y)
        self.show()
        self.activateWindow()
        self.search_input.setFocus()
