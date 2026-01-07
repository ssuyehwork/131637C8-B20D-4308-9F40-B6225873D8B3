# -*- coding: utf-8 -*-
# ui/main_window.py
import sys
import math
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QSplitter, QLineEdit,
                               QPushButton, QLabel, QScrollArea, QShortcut, QMessageBox,
                               QApplication, QToolTip, QMenu, QFrame, QTextEdit, QDialog,
                               QGraphicsDropShadowEffect, QLayout, QSizePolicy, QInputDialog)
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QRect, QSize, QByteArray
from PyQt5.QtGui import QKeySequence, QCursor, QColor, QIntValidator
from core.config import STYLES, COLORS
from core.settings import load_setting, save_setting
from data.db_manager import DatabaseManager
from services.backup_service import BackupService
from ui.sidebar import Sidebar
from ui.cards import IdeaCard
from ui.dialogs import EditDialog
from ui.ball import FloatingBall
from ui.advanced_tag_selector import AdvancedTagSelector
from ui.components.search_line_edit import SearchLineEdit
from services.preview_service import PreviewService
from ui.utils import create_svg_icon

# --- 辅助类：流式布局 ---
class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super(FlowLayout, self).__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super(FlowLayout, self).setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        margin = self.contentsMargins()
        size += QSize(margin.left() + margin.right(), margin.top() + margin.bottom())
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        spacing = self.spacing()

        for item in self.itemList:
            wid = item.widget()
            spaceX = spacing + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
            spaceY = spacing + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)
            
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y()

class ContentContainer(QWidget):
    cleared = pyqtSignal()

    def mousePressEvent(self, e):
        # 点击空白处（没有子控件的地方）触发清除选择
        if self.childAt(e.pos()) is None:
            self.cleared.emit()
            e.accept() # 阻止事件冒泡，防止被父窗口再次处理
        else:
            super().mousePressEvent(e)

# 可双击的输入框
class ClickableLineEdit(QLineEdit):
    doubleClicked = pyqtSignal()
    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)

# --- 辅助类：带删除按钮的标签 ---
class TagChipWidget(QWidget):
    deleted = pyqtSignal(str)

    def __init__(self, tag_name, parent=None):
        super().__init__(parent)
        self.tag_name = tag_name
        self.setObjectName("TagChip")
        self.setAttribute(Qt.WA_StyledBackground, True)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 5, 5)
        layout.setSpacing(6)

        self.label = QLabel(tag_name)
        self.label.setStyleSheet("border: none; background: transparent; color: #DDD; font-size: 12px; font-family: 'Segoe UI', 'Microsoft YaHei';")
        
        self.delete_btn = QPushButton("×")
        self.delete_btn.setFixedSize(18, 18)
        self.delete_btn.setCursor(Qt.PointingHandCursor)
        self.delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: #AAA;
                border: none;
                border-radius: 9px;
                font-size: 14px;
                padding-bottom: 1px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger']};
                color: white;
            }}
        """)
        
        layout.addWidget(self.label)
        layout.addWidget(self.delete_btn)

        self.setStyleSheet("""
            #TagChip {
                background-color: #383838;
                border: 1px solid #4D4D4D;
                border-radius: 14px;
            }
        """)
        
        self.delete_btn.clicked.connect(self._emit_delete)

    def _emit_delete(self):
        self.deleted.emit(self.tag_name)


# --- 辅助类：用于右侧栏的通用占位符 ---
class InfoWidget(QWidget):
    def __init__(self, icon_name, title, subtitle, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 40, 20, 20)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel()
        icon_label.setPixmap(create_svg_icon(icon_name).pixmap(64, 64))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e0e0e0; border: none;")
        layout.addWidget(title_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 12px; color: #888; border: none;")
        layout.addWidget(subtitle_label)

        layout.addStretch(1)

# --- 辅助类：带圆角的胶囊(徽章) ---
class CapsuleWidget(QLabel):
    def __init__(self, text, bg_color, text_color="white", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            background-color: {bg_color};
            color: {text_color};
            padding: 3px 8px;
            border-radius: 9px;
            font-size: 11px;
            font-weight: bold;
        """)

# --- 辅助类：元数据展示 ---
class MetadataDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 10, 0, 5)
        self.layout.setSpacing(0) # Zebra stripes need 0 spacing
        self.layout.setAlignment(Qt.AlignTop)

    def _add_row(self, icon_name, widget_or_text, is_odd=False):
        row_widget = QWidget()
        row_widget.setAutoFillBackground(True)

        palette = row_widget.palette()
        color = QColor("#282828") if is_odd else QColor("#2C2C2C")
        palette.setColor(QPalette.Window, color)
        row_widget.setPalette(palette)

        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(8, 8, 8, 8)
        row_layout.setSpacing(10)

        icon = QLabel()
        icon.setPixmap(create_svg_icon(icon_name).pixmap(16, 16))
        icon.setFixedSize(16, 16)
        row_layout.addWidget(icon)

        if isinstance(widget_or_text, QWidget):
            row_layout.addWidget(widget_or_text)
        else:
            value_label = QLabel(str(widget_or_text))
            value_label.setStyleSheet("font-size: 12px; color: #ddd; border: none;")
            row_layout.addWidget(value_label)

        self.layout.addWidget(row_widget)

    def _create_stars_widget(self, rating):
        stars_widget = QWidget()
        stars_layout = QHBoxLayout(stars_widget)
        stars_layout.setContentsMargins(0,0,0,0)
        stars_layout.setSpacing(2)

        star_icon_filled = create_svg_icon('star.svg')
        star_icon_empty = create_svg_icon('star.svg')

        for i in range(5):
            star = QLabel()
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)

            if i < rating:
                painter.setCompositionMode(QPainter.CompositionMode_Source)
                painter.fillRect(pixmap.rect(), QColor("#f39c12"))
                painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
                star_icon_filled.paint(painter, pixmap.rect())
            else:
                star_icon_empty.paint(painter, pixmap.rect())

            painter.end()
            star.setPixmap(pixmap)
            stars_layout.addWidget(star)

        stars_layout.addStretch()
        return stars_widget

    def _create_capsules_widget(self, items, color_map):
        capsules_widget = QWidget()
        capsules_layout = FlowLayout(capsules_widget, margin=0, spacing=6)
        for item in items:
            color = color_map.get(item, "#333")
            capsules_layout.addWidget(CapsuleWidget(item, color))
        return capsules_widget

    def update_data(self, data, tags, category_name):
        # Clear old data
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not data: return

        rows_to_add = []

        # Collect all data rows
        rows_to_add.append(("calendar.svg", data['created_at'][:16]))
        rows_to_add.append(("calendar.svg", data['updated_at'][:16]))
        rows_to_add.append(("folder.svg", category_name if category_name else "未分类"))

        stars_widget = self._create_stars_widget(data['rating'])
        rows_to_add.append(("star.svg", stars_widget))

        states = []
        state_colors = { "置顶": "#3498db", "锁定": "#e74c3c", "书签": "#ff6b81" }
        if data['is_pinned']: states.append("置顶")
        if data['is_locked']: states.append("锁定")
        if data['is_favorite']: states.append("书签")
        if states:
            states_widget = self._create_capsules_widget(states, state_colors)
            rows_to_add.append(("pin.svg", states_widget))

        if tags:
            tag_colors = {}
            for tag in tags:
                hash_val = sum(ord(c) for c in tag)
                colors = ["#1abc9c", "#2ecc71", "#9b59b6", "#e67e22", "#34495e"]
                tag_colors[tag] = colors[hash_val % len(colors)]
            tags_widget = self._create_capsules_widget(tags, tag_colors)
            rows_to_add.append(("tag.svg", tags_widget))

        # Add all rows with zebra striping
        for i, (icon, content) in enumerate(rows_to_add):
            self._add_row(icon, content, is_odd=(i % 2 != 0))


class MainWindow(QWidget):
    closing = pyqtSignal()
    RESIZE_MARGIN = 8

    def __init__(self):
        super().__init__()
        QApplication.setQuitOnLastWindowClosed(False)
        self.db = DatabaseManager()
        self.preview_service = PreviewService(self.db, self)
        
        self.curr_filter = ('all', None)
        self.selected_ids = set()
        self._drag_pos = None
        self.current_tag_filter = None
        self.last_clicked_id = None 
        self.card_ordered_ids = []  
        self._resize_area = None
        self._resize_start_pos = None
        self._resize_start_geometry = None
        
        # 分页状态
        self.current_page = 1
        self.page_size = 100
        self.total_pages = 1
        
        self.open_dialogs = [] # 存储打开的窗口
        
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.Window | 
            Qt.WindowSystemMenuHint | 
            Qt.WindowMinimizeButtonHint | 
            Qt.WindowMaximizeButtonHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        self._setup_ui()
        self._load_data()
    def _setup_ui(self):
        self.setWindowTitle('数据管理')
        # self.resize(1300, 700) # Replaced by restore
        self._restore_window_state()
        
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        
        self.container = QWidget()
        self.container.setObjectName("MainContainer")
        self.container.setStyleSheet(STYLES['main_window'])
        root_layout.addWidget(self.container)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.container.setGraphicsEffect(shadow)
        
        outer_layout = QVBoxLayout(self.container)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        titlebar = self._create_titlebar()
        outer_layout.addWidget(titlebar)
        
        main_content = QWidget()
        main_layout = QHBoxLayout(main_content)
        main_layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Horizontal)
        
        self.sidebar = Sidebar(self.db)
        self.sidebar.filter_changed.connect(self._set_filter)
        self.sidebar.data_changed.connect(self._load_data)
        self.sidebar.new_data_requested.connect(self._on_new_data_in_category_requested)
        splitter.addWidget(self.sidebar)
        
        middle_panel = self._create_middle_panel()
        splitter.addWidget(middle_panel)
        
        self.metadata_panel = self._create_metadata_panel()
        splitter.addWidget(self.metadata_panel)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 1)
        
        main_layout.addWidget(splitter)
        outer_layout.addWidget(main_content)
        
        QShortcut(QKeySequence("Ctrl+T"), self, self._handle_extract_key)
        QShortcut(QKeySequence("Ctrl+N"), self, self.new_idea)
        QShortcut(QKeySequence("Ctrl+W"), self, self.close)
        QShortcut(QKeySequence("Ctrl+A"), self, self._select_all)
        QShortcut(QKeySequence("Ctrl+F"), self, self.search.setFocus)
        QShortcut(QKeySequence("Ctrl+E"), self, self._do_fav)
        QShortcut(QKeySequence("Ctrl+B"), self, self._do_edit)
        QShortcut(QKeySequence("Ctrl+P"), self, self._do_pin)
        QShortcut(QKeySequence("Delete"), self, self._handle_del_key)
        
        # 【新增】Ctrl+S 锁定/解锁快捷键
        QShortcut(QKeySequence("Ctrl+S"), self, self._do_lock)

        # 【新增】星级评分快捷键 Ctrl+0 到 Ctrl+5
        for i in range(6):
            QShortcut(QKeySequence(f"Ctrl+{i}"), self, lambda r=i: self._do_set_rating(r))
        
        self.space_shortcut = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.space_shortcut.setContext(Qt.WindowShortcut)
        self.space_shortcut.activated.connect(lambda: self.preview_service.toggle_preview(self.selected_ids))

    def _select_all(self):
        if not self.cards: return
        if len(self.selected_ids) == len(self.cards):
            self.selected_ids.clear()
        else:
            self.selected_ids = set(self.cards.keys())
        self._update_all_card_selections()
        self._update_ui_state()

    def _clear_all_selections(self):
        if not self.selected_ids: return
        self.selected_ids.clear()
        self.last_clicked_id = None
        self._update_all_card_selections()
        self._update_ui_state()

    def _create_titlebar(self):
        titlebar = QWidget()
        titlebar.setFixedHeight(40)
        titlebar.setStyleSheet(f"QWidget {{ background-color: {COLORS['bg_mid']}; border-bottom: 1px solid {COLORS['bg_light']}; border-top-left-radius: 8px; border-top-right-radius: 8px; }}")
        
        layout = QHBoxLayout(titlebar)
        layout.setContentsMargins(15, 0, 10, 0)
        layout.setSpacing(6)
        
        title = QLabel('💡 快速笔记')
        title.setStyleSheet("font-size: 13px; font-weight: bold; color: #4a90e2;")
        layout.addWidget(title)
        
        self.search = SearchLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.setPlaceholderText('🔍 搜索灵感 (双击查看历史)')
        self.search.setFixedWidth(280)
        self.search.setFixedHeight(28)
        self.search.setStyleSheet(STYLES['input'] + """
            QLineEdit { border-radius: 14px; padding-right: 25px; }
            QLineEdit::clear-button { image: url(assets/clear.png); subcontrol-position: right; margin-right: 5px; }
        """)
        self.search.textChanged.connect(lambda: self._set_page(1))
        self.search.returnPressed.connect(self._add_search_to_history)
        layout.addWidget(self.search)
        
        layout.addSpacing(10)
        
        # --- 分页控件区域 ---
        page_btn_style = """
            QPushButton { background-color: transparent; border: 1px solid #444; color: #aaa; border-radius: 4px; font-size: 11px; padding: 2px 8px; min-width: 20px; }
            QPushButton:hover { background-color: #333; color: white; border-color: #666; }
            QPushButton:disabled { color: #444; border-color: #333; }
        """
        
        self.btn_first = QPushButton("<<")
        self.btn_first.setStyleSheet(page_btn_style)
        self.btn_first.setToolTip("首页")
        self.btn_first.clicked.connect(lambda: self._set_page(1))
        
        self.btn_prev = QPushButton("<")
        self.btn_prev.setStyleSheet(page_btn_style)
        self.btn_prev.setToolTip("上一页")
        self.btn_prev.clicked.connect(lambda: self._set_page(self.current_page - 1))
        
        self.page_input = QLineEdit()
        self.page_input.setFixedWidth(40)
        self.page_input.setAlignment(Qt.AlignCenter)
        self.page_input.setValidator(QIntValidator(1, 9999))
        self.page_input.setStyleSheet("background-color: #2D2D2D; border: 1px solid #444; color: #DDD; border-radius: 4px; padding: 2px;")
        self.page_input.returnPressed.connect(self._jump_to_page)
        
        self.total_page_label = QLabel("/ 1")
        self.total_page_label.setStyleSheet("color: #888; font-size: 12px; margin-left: 2px; margin-right: 5px;")
        
        self.btn_next = QPushButton(">")
        self.btn_next.setStyleSheet(page_btn_style)
        self.btn_next.setToolTip("下一页")
        self.btn_next.clicked.connect(lambda: self._set_page(self.current_page + 1))
        
        self.btn_last = QPushButton(">>")
        self.btn_last.setStyleSheet(page_btn_style)
        self.btn_last.setToolTip("末页")
        self.btn_last.clicked.connect(lambda: self._set_page(self.total_pages))
        
        layout.addWidget(self.btn_first)
        layout.addWidget(self.btn_prev)
        layout.addWidget(self.page_input)
        layout.addWidget(self.total_page_label)
        layout.addWidget(self.btn_next)
        layout.addWidget(self.btn_last)
        
        layout.addStretch()
        
        ctrl_btn_style = f"QPushButton {{ background-color: transparent; border: none; color: #aaa; border-radius: 6px; font-size: 16px; min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; }} QPushButton:hover {{ background-color: rgba(255,255,255,0.1); color: white; }}"
        
        extract_btn = QPushButton('📤')
        extract_btn.setToolTip('批量提取全部')
        extract_btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['primary']}; border: none; color: white; border-radius: 6px; font-size: 18px; min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; }} QPushButton:hover {{ background-color: #357abd; }}")
        # 确保这里调用了 self._extract_all
        extract_btn.clicked.connect(self._extract_all)
        layout.addWidget(extract_btn)
        
        new_btn = QPushButton('➕')
        new_btn.setToolTip('新建灵感 (Ctrl+N)')
        new_btn.setStyleSheet(f"QPushButton {{ background-color: {COLORS['primary']}; border: none; color: white; border-radius: 6px; font-size: 18px; min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; }} QPushButton:hover {{ background-color: #357abd; }}")
        new_btn.clicked.connect(self.new_idea)
        layout.addWidget(new_btn)
        layout.addSpacing(4)
        
        min_btn = QPushButton('─')
        min_btn.setStyleSheet(ctrl_btn_style)
        min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(min_btn)
        
        self.max_btn = QPushButton('□')
        self.max_btn.setStyleSheet(ctrl_btn_style)
        self.max_btn.clicked.connect(self._toggle_maximize)
        layout.addWidget(self.max_btn)
        
        close_btn = QPushButton('✕')
        close_btn.setStyleSheet(ctrl_btn_style + "QPushButton:hover { background-color: #e74c3c; color: white; }")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        return titlebar

    # --- 分页逻辑 ---
    def _set_page(self, page_num):
        if page_num < 1: page_num = 1
        self.current_page = page_num
        self._load_data()

    def _jump_to_page(self):
        text = self.page_input.text().strip()
        if text.isdigit():
            page = int(text)
            self._set_page(page)
        else:
            self.page_input.setText(str(self.current_page))

    def _update_pagination_ui(self):
        self.page_input.setText(str(self.current_page))
        self.total_page_label.setText(f"/ {self.total_pages}")
        
        is_first = (self.current_page <= 1)
        is_last = (self.current_page >= self.total_pages)
        
        self.btn_first.setDisabled(is_first)
        self.btn_prev.setDisabled(is_first)
        self.btn_next.setDisabled(is_last)
        self.btn_last.setDisabled(is_last)

    def _create_middle_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        act_bar = QHBoxLayout()
        act_bar.setSpacing(4)
        act_bar.setContentsMargins(20, 10, 20, 10)
        
        self.header_label = QLabel('全部数据')
        self.header_label.setStyleSheet("font-size:18px;font-weight:bold;")
        act_bar.addWidget(self.header_label)
        
        self.tag_filter_label = QLabel()
        self.tag_filter_label.setStyleSheet(f"background-color: {COLORS['primary']}; color: white; border-radius: 10px; padding: 4px 10px; font-size: 11px; font-weight: bold;")
        self.tag_filter_label.hide()
        act_bar.addWidget(self.tag_filter_label)
        act_bar.addStretch()
        
        self.btns = {}
        for k, i, f in [('pin','📌',self._do_pin), ('fav','🔖',self._do_fav), ('edit','✏️',self._do_edit),
                        ('del','🗑️',self._do_del), ('rest','♻️',self._do_restore), ('dest','🗑️',self._do_destroy)]:
            b = QPushButton(i)
            b.setStyleSheet(STYLES['btn_icon'])
            b.clicked.connect(f)
            b.setEnabled(False)
            act_bar.addWidget(b)
            self.btns[k] = b
        layout.addLayout(act_bar)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none")
        self.list_container = ContentContainer()
        self.list_container.cleared.connect(self._clear_all_selections)
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignTop)
        self.list_layout.setSpacing(10)
        self.list_layout.setContentsMargins(20, 5, 20, 15)
        scroll.setWidget(self.list_container)
        layout.addWidget(scroll)
        
        return panel

    def _create_metadata_panel(self):
        panel = QWidget()
        panel.setObjectName("RightPanel")
        panel.setStyleSheet(f"#RightPanel {{ background-color: {COLORS['bg_mid']}; }}")
        panel.setFixedWidth(240)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # 1. 标题区
        self.metadata_panel_title = QLabel('📄 元数据')
        self.metadata_panel_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #4a90e2;")
        layout.addWidget(self.metadata_panel_title)

        # 2. 信息展示区
        self.info_stack = QWidget()
        self.info_stack_layout = QVBoxLayout(self.info_stack)
        self.info_stack_layout.setContentsMargins(0,10,0,0) # Add some top margin

        self.no_selection_widget = InfoWidget('select.svg', "未选择项目", "请选择一个项目以查看其元数据")
        self.multi_selection_widget = InfoWidget('all_data.svg', "已选择多个项目", "请仅选择一项以查看其元数据")
        self.metadata_display = MetadataDisplay()

        self.info_stack_layout.addWidget(self.no_selection_widget)
        self.info_stack_layout.addWidget(self.multi_selection_widget)
        self.info_stack_layout.addWidget(self.metadata_display)

        layout.addWidget(self.info_stack)
        layout.addStretch(1) # Pushes everything below to the bottom

        # 3. 标题编辑器
        self.title_editor = QLineEdit()
        self.title_editor.setPlaceholderText("笔记标题")
        self.title_editor.setStyleSheet(f"""
            QLineEdit {{
                background-color: #2D2D2D; border: 1px solid #444; border-radius: 4px;
                padding: 6px 8px; font-size: 13px; color: #EEE; font-weight: bold;
            }}
            QLineEdit:focus {{ border-color: {COLORS['primary']}; background-color: #38383C; }}
            QLineEdit:disabled {{ background-color: #252525; color: #666; }}
        """)
        self.title_editor.setEnabled(False)
        self.title_editor.returnPressed.connect(self._save_title)
        self.title_editor.editingFinished.connect(self._save_title)
        layout.addWidget(self.title_editor)

        # 4. 底部标签输入框
        self.tag_input = ClickableLineEdit()
        self.tag_input.setPlaceholderText("添加标签...")
        self.tag_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: #2D2D2D; border: 1px solid #444; border-radius: 16px;
                padding: 6px 12px; font-size: 12px; color: #EEE;
            }}
            QLineEdit:focus {{ border-color: {COLORS['primary']}; background-color: #38383C; }}
            QLineEdit:disabled {{ background-color: #252525; color: #666; }}
        """)
        self.tag_input.returnPressed.connect(self._handle_tag_input_return)
        self.tag_input.doubleClicked.connect(self._open_tag_selector_for_selection)
        layout.addWidget(self.tag_input)
        
        QTimer.singleShot(0, self._refresh_metadata_panel)
        return panel

    def _handle_tag_input_return(self):
        text = self.tag_input.text().strip()
        if not text: return
        
        if self.selected_ids:
            self._add_tag_to_selection([text])
            self.tag_input.clear()

    def _open_tag_selector_for_selection(self):
        if self.selected_ids:
            selector = AdvancedTagSelector(self.db, idea_id=None, initial_tags=[])
            selector.tags_confirmed.connect(self._add_tag_to_selection)
            selector.show_at_cursor()

    def _add_tag_to_selection(self, tags):
        if not self.selected_ids or not tags: return
        self.db.add_tags_to_multiple_ideas(list(self.selected_ids), tags)
        self._refresh_all()

    def _remove_tag_from_selection(self, tag_name):
        if not self.selected_ids: return
        self.db.remove_tag_from_multiple_ideas(list(self.selected_ids), tag_name)
        self._refresh_all()

    def _save_title(self):
        if len(self.selected_ids) != 1:
            return

        idea_id = list(self.selected_ids)[0]
        new_title = self.title_editor.text()

        # To prevent saving an unchanged title and triggering unnecessary refreshes
        current_data = self.db.get_idea(idea_id)
        if current_data and current_data['title'] != new_title:
            self.db.update_idea_title(idea_id, new_title)
            self._refresh_all() # Refresh to show updated title in main list and metadata

    def _refresh_metadata_panel(self):
        num_selected = len(self.selected_ids)

        if num_selected == 0:
            self.no_selection_widget.show()
            self.multi_selection_widget.hide()
            self.metadata_display.hide()
            self.tag_input.setEnabled(False)
            self.tag_input.setPlaceholderText("请先选择一个项目")
            self.title_editor.setEnabled(False)
            self.title_editor.clear()

        elif num_selected == 1:
            self.no_selection_widget.hide()
            self.multi_selection_widget.hide()
            self.metadata_display.show()
            self.tag_input.setEnabled(True)
            self.tag_input.setPlaceholderText("添加标签...")
            self.title_editor.setEnabled(True)

            idea_id = list(self.selected_ids)[0]
            data = self.db.get_idea(idea_id)
            if data:
                tags = self.db.get_tags(idea_id)
                category_name = ""
                if data['category_id']:
                    # Inefficient to query every time, but acceptable for this context.
                    # A better implementation would cache categories on startup.
                    all_categories = self.db.get_categories()
                    cat = next((c for c in all_categories if c['id'] == data['category_id']), None)
                    if cat:
                        category_name = cat['name']
                self.metadata_display.update_data(data, tags, category_name)
                self.title_editor.setText(data['title'])
            else:
                # Handle case where data might not be found (e.g., just deleted)
                self.metadata_display.update_data(None, [], "")
                self.title_editor.clear()
                self.title_editor.setEnabled(False)
                self.tag_input.setEnabled(False)

        else: # num_selected > 1
            self.no_selection_widget.hide()
            self.multi_selection_widget.show()
            self.metadata_display.hide()
            self.tag_input.setEnabled(False)
            self.tag_input.setPlaceholderText("请仅选择一项以查看元数据")
            self.title_editor.setEnabled(False)
            self.title_editor.clear()

    # ==================== 调整大小逻辑 ====================
    def _get_resize_area(self, pos):
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = self.RESIZE_MARGIN
        
        areas = []
        if x < m: areas.append('left')
        elif x > w - m: areas.append('right')
        if y < m: areas.append('top')
        elif y > h - m: areas.append('bottom')
        return areas
    
    def _set_cursor_for_resize(self, areas):
        if not areas:
            self.setCursor(Qt.ArrowCursor)
            return
        if 'left' in areas and 'top' in areas: self.setCursor(Qt.SizeFDiagCursor)
        elif 'right' in areas and 'bottom' in areas: self.setCursor(Qt.SizeFDiagCursor)
        elif 'left' in areas and 'bottom' in areas: self.setCursor(Qt.SizeBDiagCursor)
        elif 'right' in areas and 'top' in areas: self.setCursor(Qt.SizeBDiagCursor)
        elif 'left' in areas or 'right' in areas: self.setCursor(Qt.SizeHorCursor)
        elif 'top' in areas or 'bottom' in areas: self.setCursor(Qt.SizeVerCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            areas = self._get_resize_area(e.pos())
            if areas:
                self._resize_area = areas
                self._resize_start_pos = e.globalPos()
                self._resize_start_geometry = self.geometry()
                self._drag_pos = None
            elif e.y() < 40:
                self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()
                self._resize_area = None
            else:
                self._drag_pos = None
                self._resize_area = None
            e.accept()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.NoButton:
            areas = self._get_resize_area(e.pos())
            self._set_cursor_for_resize(areas)
            e.accept()
            return
        
        if e.buttons() == Qt.LeftButton:
            if self._resize_area:
                delta = e.globalPos() - self._resize_start_pos
                rect = self._resize_start_geometry
                new_rect = rect.adjusted(0, 0, 0, 0)
                if 'left' in self._resize_area:
                    new_left = rect.left() + delta.x()
                    if rect.right() - new_left >= 600:
                        new_rect.setLeft(new_left)
                if 'right' in self._resize_area:
                    new_width = rect.width() + delta.x()
                    if new_width >= 600:
                        new_rect.setWidth(new_width)
                if 'top' in self._resize_area:
                    new_top = rect.top() + delta.y()
                    if rect.bottom() - new_top >= 400:
                        new_rect.setTop(new_top)
                if 'bottom' in self._resize_area:
                    new_height = rect.height() + delta.y()
                    if new_height >= 400:
                        new_rect.setHeight(new_height)
                
                self.setGeometry(new_rect)
                e.accept()
            elif self._drag_pos:
                self.move(e.globalPos() - self._drag_pos)
                e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        self._resize_area = None
        self.setCursor(Qt.ArrowCursor)

    def mouseDoubleClickEvent(self, e):
        if e.y() < 40: self._toggle_maximize()

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setText('□')
        else:
            self.showMaximized()
            self.max_btn.setText('❐')

    def _add_search_to_history(self):
        search_text = self.search.text().strip()
        if search_text:
            self.search.add_history_entry(search_text)

    def quick_add_idea(self, text):
        raw = text.strip()
        if not raw: return
        lines = raw.split('\n')
        title = lines[0][:25].strip() if lines else "快速记录"
        if len(lines) > 1 or len(lines[0]) > 25: title += "..."
        idea_id = self.db.add_idea(title, raw, COLORS['default_note'], [], None)
        self._show_tag_selector(idea_id)
        self._refresh_all()

    def _show_tag_selector(self, idea_id):
        tag_selector = AdvancedTagSelector(self.db, idea_id, None, self)
        tag_selector.tags_confirmed.connect(lambda tags: self._on_tags_confirmed(idea_id, tags))
        tag_selector.show_at_cursor()

    def _on_tags_confirmed(self, idea_id, tags):
        self._refresh_all()

    def _set_filter(self, f_type, val):
        self.curr_filter = (f_type, val)
        self.selected_ids.clear()
        self.last_clicked_id = None
        self.current_tag_filter = None
        self.tag_filter_label.hide()
        titles = {'all':'全部数据','today':'今日数据','trash':'回收站','favorite':'我的收藏'}
        if f_type == 'category':
            cat = next((c for c in self.db.get_categories() if c['id'] == val), None)
            self.header_label.setText(f"📂 {cat['name']}" if cat else '文件夹')
        else:
            self.header_label.setText(titles.get(f_type, '灵感列表'))
        
        # 延迟执行，防止在点击事件处理中销毁对象
        QTimer.singleShot(10, self._load_data)
        QTimer.singleShot(10, self._update_ui_state)
        QTimer.singleShot(10, self._refresh_metadata_panel)

    def _load_data(self):
        while self.list_layout.count():
            w = self.list_layout.takeAt(0).widget()
            if w: w.deleteLater()
        self.cards = {}
        self.card_ordered_ids = []
        
        # 【核心补充】此处必须先计算总数，否则分页控件全是 1/1
        total_items = self.db.get_ideas_count(self.search.text(), *self.curr_filter, tag_filter=self.current_tag_filter)
        self.total_pages = math.ceil(total_items / self.page_size) if total_items > 0 else 1
        
        # 修正页码范围
        if self.current_page > self.total_pages: self.current_page = self.total_pages
        if self.current_page < 1: self.current_page = 1

        data_list = self.db.get_ideas(self.search.text(), *self.curr_filter, page=self.current_page, page_size=self.page_size, tag_filter=self.current_tag_filter)
        
        if not data_list:
            self.list_layout.addWidget(QLabel("🔭 空空如也", alignment=Qt.AlignCenter, styleSheet="color:#666;font-size:16px;margin-top:50px"))
        for d in data_list:
            c = IdeaCard(d, self.db)
            c.get_selected_ids_func = lambda: list(self.selected_ids)
            c.selection_requested.connect(self._handle_selection_request)
            c.double_clicked.connect(self._extract_single)
            c.setContextMenuPolicy(Qt.CustomContextMenu)
            c.customContextMenuRequested.connect(lambda pos, iid=d['id']: self._show_card_menu(iid, pos))
            self.list_layout.addWidget(c)
            self.cards[d['id']] = c
            self.card_ordered_ids.append(d['id'])
            
        self._update_pagination_ui() # 刷新页码显示
        self._update_ui_state()

    def _show_card_menu(self, idea_id, pos):
        if idea_id not in self.selected_ids:
            self.selected_ids = {idea_id}
            self.last_clicked_id = idea_id
            self._update_all_card_selections()
            self._update_ui_state()
        data = self.db.get_idea(idea_id)
        if not data: return
        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ background-color: {COLORS['bg_mid']}; color: white; border: 1px solid {COLORS['bg_light']}; border-radius: 6px; padding: 4px; }} QMenu::item {{ padding: 8px 20px; border-radius: 4px; }} QMenu::item:selected {{ background-color: {COLORS['primary']}; }} QMenu::separator {{ height: 1px; background: {COLORS['bg_light']}; margin: 4px 0px; }}")
        
        in_trash = (self.curr_filter[0] == 'trash')
        
        is_locked = data['is_locked']
        rating = data['rating']
        
        if not in_trash:
            if not is_locked:
                menu.addAction('✏️ 编辑', self._do_edit)
            else:
                edit_action = menu.addAction('✏️ 编辑 (已锁定)')
                edit_action.setEnabled(False)
                
            menu.addAction('📋 提取(Ctrl+T)', lambda: self._extract_single(idea_id))
            menu.addSeparator()
            
            # --- 星级评价 ---
            rating_menu = menu.addMenu("⭐ 设置星级")
            from PyQt5.QtWidgets import QAction, QActionGroup # 临时导入
            star_group = QActionGroup(self)
            star_group.setExclusive(True)
            for i in range(1, 6):
                action = QAction(f"{'★'*i}", self, checkable=True)
                action.triggered.connect(lambda _, r=i: self._do_set_rating(r))
                if rating == i:
                    action.setChecked(True)
                rating_menu.addAction(action)
                star_group.addAction(action)
            rating_menu.addSeparator()
            action_clear_rating = rating_menu.addAction("清除评级")
            action_clear_rating.triggered.connect(lambda: self._do_set_rating(0))

            if is_locked:
                menu.addAction('🔓 解锁', self._do_lock)
            else:
                menu.addAction('🔒 锁定 (Ctrl+S)', self._do_lock)
                
            menu.addSeparator()
            menu.addAction('📌 取消置顶' if data['is_pinned'] else '📌 置顶', self._do_pin)
            menu.addAction('🔖 取消书签' if data['is_favorite'] else '🔖 添加书签', self._do_fav)
            menu.addSeparator()
            
            if not is_locked:
                cat_menu = menu.addMenu('📂 移动到分类')
                cat_menu.addAction('⚠️ 未分类', lambda: self._move_to_category(None))
                for cat in self.db.get_categories():
                    cat_menu.addAction(f'📂 {cat["name"]}', lambda cid=cat["id"]: self._move_to_category(cid))
                menu.addSeparator()
                menu.addAction('🗑️ 移至回收站', self._do_del)
            else:
                del_action = menu.addAction('🗑️ 移至回收站 (已锁定)')
                del_action.setEnabled(False)
                
        else:
            menu.addAction('♻️ 恢复', self._do_restore)
            menu.addAction('🗑️ 永久删除', self._do_destroy)
            
        card = self.cards.get(idea_id)
        if card: menu.exec_(card.mapToGlobal(pos))

    def _do_set_rating(self, rating):
        if not self.selected_ids: return
        
        for idea_id in self.selected_ids:
            self.db.set_rating(idea_id, rating)
        
        # --- 关键修复：只刷新受影响的卡片 ---
        for idea_id in self.selected_ids:
            card_widget = self.cards.get(idea_id)
            if card_widget:
                new_data = self.db.get_idea(idea_id, include_blob=True)
                if new_data:
                    card_widget.update_data(new_data)
                    
    def _do_lock(self):
        if not self.selected_ids: return
        
        # 1. 获取所有选中ID的当前锁定状态
        status_map = self.db.get_lock_status(list(self.selected_ids))
        
        # 2. 判断逻辑：如果选中的数据中有任意一个是“未锁定(0)”，则执行“全部锁定(1)”
        #    只有当所有数据都是“已锁定(1)”时，才执行“全部解锁(0)”
        any_unlocked = False
        for iid, is_locked in status_map.items():
            if not is_locked:
                any_unlocked = True
                break
        
        target_state = 1 if any_unlocked else 0
        
        # 3. 执行批量更新
        self.db.set_locked(list(self.selected_ids), target_state)
        
        # In-place update
        for iid in self.selected_ids:
            card = self.cards.get(iid)
            if card:
                new_data = self.db.get_idea(iid, include_blob=True)
                if new_data:
                    card.update_data(new_data)

        action_name = "锁定" if target_state else "解锁"
        self._update_ui_state()

    def _move_to_category(self, cat_id):
        if self.selected_ids:
            # 过滤掉锁定的项目
            valid_ids = []
            status_map = self.db.get_lock_status(list(self.selected_ids))
            for iid in self.selected_ids:
                if not status_map.get(iid, 0):
                    valid_ids.append(iid)
            
            if not valid_ids: return

            for iid in valid_ids:
                self.db.move_category(iid, cat_id)
                # --- 从UI中移除卡片 ---
                card = self.cards.pop(iid, None)
                if card:
                    card.hide()
                    card.deleteLater()
            
            self.selected_ids.clear()
            self._update_ui_state()
            self.sidebar.refresh() # 刷新分类计数
            self.sidebar._update_partition_tree() # 刷新分区计数

    def _handle_selection_request(self, iid, is_ctrl, is_shift):
        if is_shift and self.last_clicked_id is not None:
            try:
                start_index = self.card_ordered_ids.index(self.last_clicked_id)
                end_index = self.card_ordered_ids.index(iid)
                min_idx = min(start_index, end_index)
                max_idx = max(start_index, end_index)
                if not is_ctrl: self.selected_ids.clear()
                for idx in range(min_idx, max_idx + 1):
                    self.selected_ids.add(self.card_ordered_ids[idx])
            except ValueError:
                self.selected_ids.clear()
                self.selected_ids.add(iid)
                self.last_clicked_id = iid
        elif is_ctrl:
            if iid in self.selected_ids: self.selected_ids.remove(iid)
            else: self.selected_ids.add(iid)
            self.last_clicked_id = iid
        else:
            self.selected_ids.clear()
            self.selected_ids.add(iid)
            self.last_clicked_id = iid
        self._update_all_card_selections()
        # 【关键修复】异步更新UI状态，防止点击卡片时重绘右侧面板导致崩溃
        QTimer.singleShot(0, self._update_ui_state)

    def _update_all_card_selections(self):
        for iid, card in self.cards.items():
            card.update_selection(iid in self.selected_ids)

    def _update_ui_state(self):
        in_trash = (self.curr_filter[0] == 'trash')
        selection_count = len(self.selected_ids)
        has_selection = selection_count > 0
        is_single_selection = selection_count == 1
        for k in ['pin', 'fav', 'del']: self.btns[k].setVisible(not in_trash)
        for k in ['rest', 'dest']: self.btns[k].setVisible(in_trash)
        self.btns['edit'].setVisible(not in_trash)
        self.btns['edit'].setEnabled(is_single_selection)
        for k in ['pin', 'fav', 'del', 'rest', 'dest']: self.btns[k].setEnabled(has_selection)
        if is_single_selection and not in_trash:
            idea_id = list(self.selected_ids)[0]
            d = self.db.get_idea(idea_id)
            if d:
                self.btns['pin'].setText('📍' if not d['is_pinned'] else '📌')
                self.btns['fav'].setText('🔖' if d['is_favorite'] else '🔖') # 保持图标一致
        else:
            self.btns['pin'].setText('📌')
            self.btns['fav'].setText('🔖')
        # 【关键修复】异步刷新标签面板
        QTimer.singleShot(0, self._refresh_metadata_panel)

    def _on_new_data_in_category_requested(self, cat_id):
        self._open_edit_dialog(category_id_for_new=cat_id)

    def _open_edit_dialog(self, idea_id=None, category_id_for_new=None):
        # 检查是否已存在此ID的窗口
        for dialog in self.open_dialogs:
            if hasattr(dialog, 'idea_id') and dialog.idea_id == idea_id and idea_id is not None:
                dialog.activateWindow()
                return

        dialog = EditDialog(self.db, idea_id=idea_id, category_id_for_new=category_id_for_new, parent=None)
        dialog.setAttribute(Qt.WA_DeleteOnClose) # 确保关闭时删除
        
        # 使用 data_saved 刷新，确保实时性
        dialog.data_saved.connect(self._refresh_all)
        dialog.finished.connect(lambda: self.open_dialogs.remove(dialog) if dialog in self.open_dialogs else None)

        self.open_dialogs.append(dialog)
        dialog.show()
        dialog.activateWindow()

    def _show_tooltip(self, msg, dur=2000):
        QToolTip.showText(QCursor.pos(), msg, self)
        QTimer.singleShot(dur, QToolTip.hideText)

    def new_idea(self):
        self._open_edit_dialog()

    def _do_edit(self):
        if len(self.selected_ids) == 1:
            idea_id = list(self.selected_ids)[0]
            # 检查锁定
            status = self.db.get_lock_status([idea_id])
            if status.get(idea_id, 0):
                return
            self._open_edit_dialog(idea_id=idea_id)

    def _do_pin(self):
        if self.selected_ids:
            for iid in self.selected_ids: self.db.toggle_field(iid, 'is_pinned')
            self._load_data()

    def _do_fav(self):
        if self.selected_ids:
            # 智能批量切换：如果其中任何一个没有加书签，则全部设为书签
            # 只有当全部都已加书签时，才全部取消书签
            any_not_favorited = False
            all_data = []
            for iid in self.selected_ids:
                data = self.db.get_idea(iid)
                if data and not data['is_favorite']:
                    any_not_favorited = True
                all_data.append(data)

            target_state = True if any_not_favorited else False

            for iid in self.selected_ids:
                self.db.set_favorite(iid, target_state)
            
            # In-place update
            for iid in self.selected_ids:
                card = self.cards.get(iid)
                if card:
                    new_data = self.db.get_idea(iid, include_blob=True)
                    if new_data:
                        card.update_data(new_data)

            self._update_ui_state()
            self.sidebar.refresh() # --- 关键修复：刷新侧边栏计数 ---

    def _do_del(self):
        if self.selected_ids:
            # 过滤掉锁定的项目
            valid_ids = []
            status_map = self.db.get_lock_status(list(self.selected_ids))
            for iid in self.selected_ids:
                if not status_map.get(iid, 0):
                    valid_ids.append(iid)
            
            if not valid_ids: return

            for iid in valid_ids:
                self.db.set_deleted(iid, True)
                # --- 从UI中移除卡片 ---
                card = self.cards.pop(iid, None)
                if card:
                    card.hide()
                    card.deleteLater()
            
            self.selected_ids.clear()
            self._update_ui_state()
            self.sidebar.refresh() # --- 关键修复：刷新侧边栏计数 ---

    def _do_restore(self):
        if self.selected_ids:
            count = len(self.selected_ids)
            for iid in self.selected_ids:
                self.db.set_deleted(iid, False)
                card = self.cards.pop(iid, None)
                if card:
                    card.hide()
                    card.deleteLater()
            self.selected_ids.clear()
            self._update_ui_state()
            self.sidebar.refresh()

    def _do_destroy(self):
        if self.selected_ids:
            msg = f'确定永久删除选中的 {len(self.selected_ids)} 项?\n此操作不可恢复!'
            if self._show_custom_confirm_dialog("永久删除", msg):
                count = len(self.selected_ids)
                for iid in self.selected_ids:
                    self.db.delete_permanent(iid)
                    card = self.cards.pop(iid, None)
                    if card:
                        card.hide()
                        card.deleteLater()
                self.selected_ids.clear()
                self._update_ui_state()
                self.sidebar.refresh()

    def _refresh_all(self):
        # 【关键保护】如果正在清理旧控件，不要重入
        if not self.isVisible(): return
        
        # 延迟执行所有刷新
        QTimer.singleShot(10, self._load_data)
        QTimer.singleShot(10, self.sidebar.refresh)
        QTimer.singleShot(10, self._update_ui_state)
        QTimer.singleShot(10, self._refresh_tag_panel)

    def _extract_single(self, idea_id):
        data = self.db.get_idea(idea_id)
        if not data:
            self._show_tooltip('⚠️ 数据不存在', 1500)
            return
        content_to_copy = data['content'] or ""
        QApplication.clipboard().setText(content_to_copy)
        preview = content_to_copy.replace('\n', ' ')[:40] + ('...' if len(content_to_copy) > 40 else '')
        self._show_tooltip(f'✅ 内容已提取到剪贴板\n\n📋 {preview}', 2500)

    # 【补充方法】_extract_all
    def _extract_all(self):
        data = self.db.get_ideas('', 'all', None)
        if not data:
            self._show_tooltip('🔭 暂无数据', 1500)
            return
        lines = ['='*60, '💡 灵感闪记 - 内容导出', '='*60, '']
        for d in data:
            lines.append(f"【{d['title']}】")
            if d['is_pinned']: lines.append('📌 已置顶')
            if d['is_favorite']: lines.append('⭐ 已收藏')
            tags = self.db.get_tags(d['id'])
            if tags: lines.append(f"标签: {', '.join(tags)}")
            lines.append(f"时间: {d['created_at']}")
            if d['content']: lines.append(f"\n{d['content']}")
            lines.append('\n'+'-'*60+'\n')
        text = '\n'.join(lines)
        QApplication.clipboard().setText(text)
        self._show_tooltip(f'✅ 已提取 {len(data)} 条到剪贴板!', 2000)

    def _handle_del_key(self):
        self._do_destroy() if self.curr_filter[0] == 'trash' else self._do_del()

    def _handle_extract_key(self):
        if len(self.selected_ids) == 1:
            self._extract_single(list(self.selected_ids)[0])
        elif len(self.selected_ids) > 1:
            self._show_tooltip('⚠️ 请选择一条笔记进行提取', 1500)
        else:
            self._show_tooltip('⚠️ 请先选择一条笔记', 1500)

    def show_main_window(self):
        self.show()
        self.activateWindow()

    def quit_app(self):
        BackupService.run_backup()
        QApplication.quit()

    def _save_window_state(self):
        save_setting("main_window_geometry_hex", self.saveGeometry().toHex().data().decode())
        save_setting("main_window_maximized", self.isMaximized())

    def save_state(self):
        self._save_window_state()

    def _restore_window_state(self):
        geo_hex = load_setting("main_window_geometry_hex")
        if geo_hex:
            try:
                self.restoreGeometry(QByteArray.fromHex(geo_hex.encode()))
            except Exception:
                self.resize(1300, 700)
        else:
            self.resize(1300, 700)
            
        if load_setting("main_window_maximized", False):
            self.showMaximized()
            self.max_btn.setText('❐')

    def closeEvent(self, event):
        self._save_window_state()
        self.closing.emit()
        self.hide()
        event.ignore()
