# K Main_V3.py
import sys
import time
import logging
import traceback
import keyboard
from PyQt5.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QDialog
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

# 导入 Container 和 Views
from core.container import AppContainer
from ui.quick_window import QuickWindow
from ui.main_window import MainWindow
from ui.ball import FloatingBall
from ui.action_popup import ActionPopup
from ui.common_tags_manager import CommonTagsManager
from core.settings import load_setting

SERVER_NAME = "K_KUAIJIBIJI_SINGLE_INSTANCE_SERVER"

# --- Setup Logging ---
log_format = '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
logging.basicConfig(filename='app_log.txt', level=logging.DEBUG, format=log_format, filemode='w')
def excepthook(exc_type, exc_value, exc_tb):
    logging.error("Unhandled exception:", exc_info=(exc_type, exc_value, exc_tb))
    traceback.print_exception(exc_type, exc_value, exc_tb)
sys.excepthook = excepthook
# --- End Logging Setup ---

# 用于在主线程中接收全局热键信号
class HotkeySignal(QObject):
    activated = pyqtSignal()

class AppManager(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        
        # 1. 初始化容器并获取 Service
        self.container = AppContainer()
        self.service = self.container.service
        
        self.main_window = None
        self.quick_window = None
        self.ball = None
        self.popup = None 
        self.tray_icon = None
        self.tags_manager_dialog = None
        
        # 全局热键信号
        self.hotkey_signal = HotkeySignal()
        self.hotkey_signal.activated.connect(self.toggle_quick_window)

    def start(self):
        # 2. 注入 Service 到 UI 组件
        self.main_window = MainWindow(self.service) 
        self.main_window.closing.connect(self.on_main_window_closing)

        self.ball = FloatingBall(self.main_window)
        
        # 悬浮球菜单逻辑
        # 导入 create_svg_icon
        from ui.utils import create_svg_icon

        original_context_menu = self.ball.contextMenuEvent
        def enhanced_context_menu(e):
            m = QMenu(self.ball)
            m.setStyleSheet("""
                QMenu {
                    background-color: #2b2b2b; color: #f0f0f0; border: 1px solid #444;
                    border-radius: 5px; padding: 4px;
                }
                QMenu::item { padding: 6px 10px 6px 28px; border-radius: 4px; }
                QMenu::item:selected { background-color: #4a90e2; }
                QMenu::separator { background-color: #444; height: 1px; margin: 4px 0; }
                QMenu::icon { position: absolute; left: 8px; }
            """)

            # 使用SVG图标
            skin_menu = m.addMenu(create_svg_icon('action_eye.svg', '#1abc9c'), "切换外观")
            a1 = skin_menu.addAction("摩卡·勃艮第"); a1.triggered.connect(lambda: self.ball.switch_skin(self.ball.SKIN_MOCHA))
            a2 = skin_menu.addAction("经典黑金"); a2.triggered.connect(lambda: self.ball.switch_skin(self.ball.SKIN_CLASSIC))
            a3 = skin_menu.addAction("皇家蓝"); a3.triggered.connect(lambda: self.ball.switch_skin(self.ball.SKIN_ROYAL))
            a4 = skin_menu.addAction("抹茶绿"); a4.triggered.connect(lambda: self.ball.switch_skin(self.ball.SKIN_MATCHA))
            a5 = skin_menu.addAction("摊开手稿"); a5.triggered.connect(lambda: self.ball.switch_skin(self.ball.SKIN_OPEN))

            m.addSeparator()
            m.addAction(create_svg_icon('pencil.svg', '#4a90e2'), '打开快速笔记', self.ball.request_show_quick_window.emit)
            m.addAction(create_svg_icon('win_sidebar.svg', '#4a90e2'), '打开主界面', self.ball.request_show_main_window.emit)
            m.addAction(create_svg_icon('action_add.svg', '#2ecc71'), '新建灵感', self.main_window.new_idea)
            m.addSeparator()
            m.addAction(create_svg_icon('tag.svg', '#f39c12'), '管理常用标签', self._open_common_tags_manager)
            m.addSeparator()
            m.addAction(create_svg_icon('win_close.svg', '#e74c3c'), '退出', self.ball.request_quit_app.emit)
            m.exec_(e.globalPos())

        self.ball.contextMenuEvent = enhanced_context_menu
        self.ball.request_show_quick_window.connect(self.show_quick_window)
        self.ball.double_clicked.connect(self.show_quick_window)
        self.ball.request_show_main_window.connect(self.show_main_window)
        self.ball.request_quit_app.connect(self.quit_application)
        
        ball_pos = load_setting('floating_ball_pos')
        if ball_pos and isinstance(ball_pos, dict) and 'x' in ball_pos and 'y' in ball_pos:
            self.ball.move(ball_pos['x'], ball_pos['y'])
        else:
            g = QApplication.desktop().screenGeometry()
            self.ball.move(g.width()-80, g.height()//2)
        self.ball.show()

        self.quick_window = QuickWindow(self.service) 
        self.quick_window.toggle_main_window_requested.connect(self.toggle_main_window)
        
        self.popup = ActionPopup(self.service) 
        self.popup.request_favorite.connect(self._handle_popup_favorite)
        self.popup.request_tag_toggle.connect(self._handle_popup_tag_toggle)
        self.popup.request_manager.connect(self._open_common_tags_manager)
        
        self.quick_window.cm.data_captured.connect(self._on_clipboard_data_captured)
        
        self._init_tray_icon()
        
        # 注册全局热键 Alt+Space
        try:
            keyboard.add_hotkey('alt+space', self._on_hotkey_triggered, suppress=False)
        except Exception as e:
            logging.error(f"Failed to register hotkey: {e}")

        self.show_quick_window()

    def _on_hotkey_triggered(self):
        self.hotkey_signal.activated.emit()

    def _init_tray_icon(self):
        temp_ball = FloatingBall(None)
        temp_ball.timer.stop()
        temp_ball.is_writing = False
        temp_ball.pen_angle = -45
        temp_ball.pen_x = 0; temp_ball.pen_y = 0; temp_ball.book_y = 0
        pixmap = QPixmap(temp_ball.size()); pixmap.fill(Qt.transparent); temp_ball.render(pixmap)
        dynamic_icon = QIcon(pixmap)
        
        self.app.setWindowIcon(dynamic_icon)
        self.tray_icon = QSystemTrayIcon(self.app)
        self.tray_icon.setIcon(dynamic_icon)
        self.tray_icon.setToolTip("快速笔记")
        
        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #2D2D2D; color: #EEE; border: 1px solid #444; } QMenu::item { padding: 6px 24px; } QMenu::item:selected { background-color: #4a90e2; color: white; }")
        
        action_show = menu.addAction("显示主界面"); action_show.triggered.connect(self.show_main_window)
        action_quick = menu.addAction("显示快速笔记"); action_quick.triggered.connect(self.show_quick_window)
        menu.addSeparator()
        action_quit = menu.addAction("退出程序"); action_quit.triggered.connect(self.quit_application)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_icon_activated)
        self.tray_icon.show()

    def _on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger: self.show_quick_window()

    def _open_common_tags_manager(self):
        if self.tags_manager_dialog and self.tags_manager_dialog.isVisible():
            self._force_activate(self.tags_manager_dialog); return
        self.tags_manager_dialog = CommonTagsManager()
        self.tags_manager_dialog.finished.connect(self._on_tags_manager_closed)
        self.tags_manager_dialog.show(); self._force_activate(self.tags_manager_dialog)

    def _on_tags_manager_closed(self, result):
        if result == QDialog.Accepted and self.popup: self.popup.common_tags_bar.reload_tags()
        self.tags_manager_dialog = None

    def _on_clipboard_data_captured(self, idea_id):
        self.ball.trigger_clipboard_feedback()
        if self.popup: self.popup.show_at_mouse(idea_id)

    def _handle_popup_favorite(self, idea_id):
        idea_data = self.service.get_idea(idea_id)
        if not idea_data: return
        is_favorite = idea_data['is_favorite'] == 1
        self.service.set_favorite(idea_id, not is_favorite)
        if self.main_window.isVisible():
            self.main_window._load_data(); self.main_window.sidebar.refresh()

    def _handle_popup_tag_toggle(self, idea_id, tag_name):
        current_tags = self.service.get_tags(idea_id)
        if tag_name in current_tags: self.service.remove_tag_from_multiple_ideas([idea_id], tag_name)
        else: self.service.add_tags_to_multiple_ideas([idea_id], [tag_name])
        if self.main_window.isVisible():
            self.main_window._load_data(); self.main_window._refresh_metadata_panel()

    def _force_activate(self, window):
        if not window: return
        window.show()
        if window.isMinimized(): window.setWindowState(window.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        window.showNormal(); window.raise_(); window.activateWindow()

    def show_quick_window(self): self._force_activate(self.quick_window)
    def toggle_quick_window(self):
        if self.quick_window and self.quick_window.isVisible(): self.quick_window.hide()
        else: self.show_quick_window()
    def show_main_window(self): self._force_activate(self.main_window)
    def toggle_main_window(self):
        if self.main_window.isVisible() and not self.main_window.isMinimized(): self.main_window.hide()
        else: self.show_main_window()
    def on_main_window_closing(self):
        if self.main_window: self.main_window.hide()
    def quit_application(self):
        try:
            keyboard.unhook_all()
        except: pass
        if self.quick_window:
            try: self.quick_window.save_state()
            except: pass
        if self.main_window:
            try: self.main_window.save_state()
            except: pass
        self.app.quit()

def main():
    app = QApplication(sys.argv)
    socket = QLocalSocket(); socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(500):
        socket.write(b'EXIT'); socket.flush(); socket.waitForBytesWritten(1000)
        socket.disconnectFromServer(); time.sleep(0.5)
    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer(); server.listen(SERVER_NAME)
    
    manager = AppManager(app)
    
    def handle_new_connection():
        conn = server.nextPendingConnection()
        if conn and conn.waitForReadyRead(500):
            msg = conn.readAll().data().decode()
            if msg == 'SHOW': manager.show_quick_window()
            elif msg == 'EXIT': manager.quit_application()
    server.newConnection.connect(handle_new_connection)
    
    manager.start()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()