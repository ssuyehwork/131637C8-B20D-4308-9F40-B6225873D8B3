# K Main_V3.py (Refactored with Micro-invasive approach)

import sys
import time
import os
import logging
import traceback
import sqlite3

# --- Setup Logging ---
log_format = '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
logging.basicConfig(filename='app_log.txt', level=logging.DEBUG, format=log_format, filemode='w')

def excepthook(exc_type, exc_value, exc_tb):
    logging.error("Unhandled exception:", exc_info=(exc_type, exc_value, exc_tb))
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook
# --- End Logging Setup ---

from PyQt5.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QDialog
from PyQt5.QtCore import QObject, Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

# --- UI Imports ---
from ui.quick_window import QuickWindow
from ui.main_window import MainWindow
from ui.ball import FloatingBall
from ui.action_popup import ActionPopup
from ui.common_tags_manager import CommonTagsManager
from ui.advanced_tag_selector import AdvancedTagSelector

# --- New Architecture Imports ---
from core.config import DB_NAME
from infrastructure.database_setup import setup_database
from infrastructure.repositories.idea_repository import IdeaRepository
from infrastructure.repositories.category_repository import CategoryRepository
from infrastructure.repositories.tag_repository import TagRepository
from application.services.idea_service import IdeaService
from application.services.category_service import CategoryService
from application.services.statistics_service import StatisticsService

# --- Legacy Import (for components not yet refactored) ---
from data.db_manager import DatabaseManager
from core.settings import load_setting

SERVER_NAME = "K_KUAIJIBIJI_SINGLE_INSTANCE_SERVER"

class AppManager(QObject):

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.db_manager = None # Legacy
        self.db_connection = None # New
        self.main_window = None
        self.quick_window = None
        self.ball = None
        self.popup = None 
        self.tray_icon = None
        self.tags_manager_dialog = None
        # Services
        self.idea_service = None
        self.category_service = None
        self.statistics_service = None

    def start(self):
        # --- Composition Root ---
        try:
            # 1. DB Connection and Setup
            self.db_connection = sqlite3.connect(DB_NAME)
            self.db_connection.row_factory = sqlite3.Row
            setup_database(self.db_connection)

            # 2. Instantiate Repositories
            idea_repo = IdeaRepository(self.db_connection)
            category_repo = CategoryRepository(self.db_connection)
            tag_repo = TagRepository(self.db_connection)

            # 3. Instantiate Services
            self.idea_service = IdeaService(idea_repo, tag_repo)
            self.category_service = CategoryService(category_repo, idea_repo)
            self.statistics_service = StatisticsService(self.db_connection)

            # 4. Legacy DB Manager for non-refactored parts
            self.db_manager = DatabaseManager()

        except Exception as e:
            logging.critical(f"Initialization failed: {e}")
            sys.exit(1)
        # --- End Composition Root ---

        app_icon = QIcon()
        self.app.setWindowIcon(app_icon)
        self._init_tray_icon(app_icon)

        # Inject services into MainWindow
        self.main_window = MainWindow(self.idea_service, self.category_service, self.statistics_service)
        self.main_window.closing.connect(self.on_main_window_closing)

        self.ball = FloatingBall(self.main_window)
        
        # --- Ball Menu Setup (unchanged) ---
        def enhanced_context_menu(e):
            m = QMenu(self.ball)
            m.addAction('⚡ 打开快速笔记', self.ball.request_show_quick_window.emit)
            m.addAction('💻 打开主界面', self.ball.request_show_main_window.emit)
            m.addAction('➕ 新建灵感', self.main_window.new_idea)
            m.addSeparator()
            m.addAction('❌ 退出', self.ball.request_quit_app.emit)
            m.exec_(e.globalPos())
        self.ball.contextMenuEvent = enhanced_context_menu
        self.ball.request_show_quick_window.connect(self.show_quick_window)
        self.ball.double_clicked.connect(self.show_quick_window)
        self.ball.request_show_main_window.connect(self.show_main_window)
        self.ball.request_quit_app.connect(self.quit_application)
        self.ball.show()

        # QuickWindow still uses legacy db_manager for now
        self.quick_window = QuickWindow(self.db_manager)
        self.quick_window.toggle_main_window_requested.connect(self.toggle_main_window)
        
        # ActionPopup also uses legacy db_manager for now
        self.popup = ActionPopup(self.db_manager)
        # BUT, the handlers for its signals will use the new service layer
        self.popup.request_favorite.connect(self._handle_popup_favorite)
        self.popup.request_tag_toggle.connect(self._handle_popup_tag_toggle)
        
        self.quick_window.cm.data_captured.connect(self._on_clipboard_data_captured)
        self.show_quick_window()

    def _init_tray_icon(self, icon):
        temp_ball = FloatingBall(None)
        pixmap = QPixmap(temp_ball.size())
        pixmap.fill(Qt.transparent)
        temp_ball.render(pixmap)
        dynamic_icon = QIcon(pixmap)
        
        self.app.setWindowIcon(dynamic_icon)
        self.tray_icon = QSystemTrayIcon(self.app)
        self.tray_icon.setIcon(dynamic_icon)
        self.tray_icon.setToolTip("快速笔记")
        
        menu = QMenu()
        menu.addAction("显示主界面", self.show_main_window)
        menu.addAction("显示快速笔记", self.show_quick_window)
        menu.addSeparator()
        menu.addAction("退出程序", self.quit_application)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        self.tray_icon.show()

    def _on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show_quick_window()

    def _on_clipboard_data_captured(self, idea_id):
        self.ball.trigger_clipboard_feedback()
        if self.popup:
            self.popup.show_at_mouse(idea_id)

    def _handle_popup_favorite(self, idea_id):
        # Refactored to use IdeaService
        self.idea_service.batch_toggle_favorite([idea_id])
        if self.main_window.isVisible():
            self.main_window._load_data()
            self.main_window.sidebar.refresh()

    def _handle_popup_tag_toggle(self, idea_id, tag_name):
        # Refactored to use IdeaService
        idea = self.idea_service.get_idea(idea_id)
        if idea:
            tag_names = [tag.name for tag in idea.tags]
            if tag_name in tag_names:
                self.idea_service.remove_tag_from_ideas([idea_id], tag_name)
            else:
                self.idea_service.add_tags_to_ideas([idea_id], [tag_name])

        if self.main_window.isVisible():
            self.main_window._load_data()

    def _force_activate(self, window):
        if not window: return
        window.show(); window.raise_(); window.activateWindow()

    def show_quick_window(self): self._force_activate(self.quick_window)
    def show_main_window(self): self._force_activate(self.main_window)
    def toggle_main_window(self):
        if self.main_window.isVisible() and not self.main_window.isMinimized(): self.main_window.hide()
        else: self.show_main_window()
    def on_main_window_closing(self):
        if self.main_window: self.main_window.hide()
            
    def quit_application(self):
        if self.quick_window: self.quick_window.save_state()
        if self.main_window: self.main_window.save_state()
        if self.db_connection: self.db_connection.close()
        self.app.quit()

def main():
    app = QApplication(sys.argv)
    
    # Single instance logic
    socket = QLocalSocket(); socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(500):
        socket.write(b'SHOW'); socket.flush(); socket.waitForBytesWritten(1000)
        return
    
    server = QLocalServer(); server.listen(SERVER_NAME)
    manager = AppManager(app)
    server.newConnection.connect(lambda: manager.show_main_window())
    
    manager.start()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
