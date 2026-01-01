# K Main_V3.py
import sys
import time
from PyQt5.QtWidgets import QApplication, QMenu
from PyQt5.QtCore import QObject, Qt
from PyQt5.QtNetwork import QLocalServer, QLocalSocket

from ui.quick_window import QuickWindow
from ui.main_window import MainWindow
from ui.ball import FloatingBall
from ui.action_popup import ActionPopup
from ui.common_tags_manager import CommonTagsManager
from ui.advanced_tag_selector import AdvancedTagSelector
from data.db_manager import DatabaseManager
from core.settings import load_setting

SERVER_NAME = "K_KUAIJIBIJI_SINGLE_INSTANCE_SERVER"

class AppManager(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.db_manager = None
        self.main_window = None
        self.quick_window = None
        self.ball = None
        self.popup = None 

    def start(self):
        try:
            self.db_manager = DatabaseManager()
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            sys.exit(1)

        self.main_window = MainWindow()
        self.main_window.closing.connect(self.on_main_window_closing)

        self.ball = FloatingBall(self.main_window)
        
        # 动态绑定悬浮球右键菜单
        original_context_menu = self.ball.contextMenuEvent
        def new_context_menu(e):
            m = QMenu(self.ball)
            m.setStyleSheet("""
                QMenu { background-color: #1a1a1a; color: #00f3ff; border: 1px solid #333; padding: 5px; }
                QMenu::item { padding: 5px 20px; }
                QMenu::item:selected { background-color: #00f3ff; color: #000; border-radius: 2px;}
                QMenu::separator { background-color: #333; height: 1px; margin: 5px 0; }
            """)
            m.addAction('⚡ 打开快速笔记', self.ball.request_show_quick_window.emit)
            m.addAction('💻 打开主界面', self.ball.request_show_main_window.emit)
            m.addAction('➕ 新建灵感', self.main_window.new_idea)
            m.addSeparator()
            m.addAction('🏷️ 管理常用标签', self._open_common_tags_manager)
            m.addSeparator()
            m.addAction('❌ 退出', self.ball.request_quit_app.emit)
            m.exec_(e.globalPos())
        
        self.ball.contextMenuEvent = new_context_menu

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

        self.quick_window = QuickWindow(self.db_manager)
        self.quick_window.open_main_window_requested.connect(self.show_main_window)
        
        # 初始化 Popup (无参数)
        self.popup = ActionPopup() 
        self.popup.request_favorite.connect(self._handle_popup_favorite)
        self.popup.request_tag_add.connect(self._handle_popup_tag_add)
        self.popup.request_manager.connect(self._open_common_tags_manager)
        
        self.quick_window.cm.data_captured.connect(self._on_clipboard_data_captured)

    def _open_common_tags_manager(self):
        """打开常用标签管理界面"""
        dlg = CommonTagsManager()
        if dlg.exec_():
            # 刷新 Popup 里的标签栏 (如果它还活着)
            if self.popup:
                self.popup.common_tags_bar.reload_tags()

    def _on_clipboard_data_captured(self, idea_id):
        self.ball.trigger_clipboard_feedback()
        if self.popup:
            self.popup.show_at_mouse(idea_id)

    def _handle_popup_favorite(self, idea_id):
        self.db_manager.set_favorite(idea_id, True)
        if self.main_window.isVisible():
            self.main_window._load_data()
            self.main_window.sidebar.refresh()

    def _handle_popup_tag_add(self, idea_id, tag_name):
        """快速添加单个标签"""
        self.db_manager.add_tags_to_multiple_ideas([idea_id], [tag_name])
        if self.main_window.isVisible():
            self.main_window._load_data()
            self.main_window._refresh_tag_panel()

    def show_quick_window(self):
        if self.quick_window:
            if self.quick_window.isMinimized():
                self.quick_window.showNormal()
            self.quick_window.show()
            self.quick_window.activateWindow()

    def toggle_quick_window(self):
        if self.quick_window:
            if self.quick_window.isVisible():
                self.quick_window.hide()
            else:
                self.show_quick_window()

    def show_main_window(self):
        if self.main_window:
            if self.main_window.isMinimized():
                self.main_window.showNormal()
            self.main_window.show()
            self.main_window.activateWindow()

    def on_main_window_closing(self):
        if self.main_window:
            self.main_window.hide()
            
    def quit_application(self):
        print("ℹ️  应用程序正在退出...")
        self.app.quit()

def main():
    app = QApplication(sys.argv)
    
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)

    if socket.waitForConnected(500):
        print("ℹ️  检测到旧实例，发送退出指令...")
        socket.write(b'EXIT')
        socket.flush()
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        time.sleep(0.5)
        QLocalServer.removeServer(SERVER_NAME)
        print("✅ 旧实例已清理")
    else:
        QLocalServer.removeServer(SERVER_NAME)

    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        print(f"❌ 无法创建单例服务器: {server.errorString()}")
    
    manager = AppManager(app)

    def handle_new_connection():
        conn = server.nextPendingConnection()
        if conn and conn.waitForReadyRead(500):
            msg = conn.readAll().data().decode()
            if msg == 'SHOW':
                manager.show_quick_window()
            elif msg == 'EXIT':
                manager.quit_application()

    server.newConnection.connect(handle_new_connection)
    
    manager.start()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()