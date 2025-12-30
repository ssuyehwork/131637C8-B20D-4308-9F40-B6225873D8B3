from PyQt5.QtCore import pyqtSignal, QSettings, Qt, QPoint
from PyQt5.QtWidgets import QLineEdit, QListWidget, QListWidgetItem, QPushButton, QHBoxLayout, QWidget


class SearchLineEdit(QLineEdit):
    """
    一个带有搜索历史记录功能的自定义QLineEdit。
    """
    search_triggered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 使用与应用匹配的设置名称
        self.settings = QSettings("KMain_V3", "SearchHistory")
        self.history = self.load_history()

        self.history_popup = QListWidget(self)
        self.history_popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.history_popup.setFocusPolicy(Qt.NoFocus)
        self.history_popup.setMouseTracking(True)
        # itemClicked 信号在有自定义小部件时可能不会按预期工作，我们将依赖按钮的点击
        # self.history_popup.itemClicked.connect(self._on_history_item_clicked)
        self.history_popup.hide()

    def focusOutEvent(self, event):
        """当焦点离开时隐藏弹出窗口"""
        self.history_popup.hide()
        super().focusOutEvent(event)
        
    def mouseDoubleClickEvent(self, event):
        """
        Show search history on double click.
        """
        self.show_history_popup()
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        """
        Trigger search on Enter/Return key press and add to history.
        """
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            text = self.text()
            if text:
                self.add_to_history(text)
                self.search_triggered.emit(text)
        super().keyPressEvent(event)

    def add_to_history(self, text):
        """
        Add a new search term to the history.
        """
        if text in self.history:
            self.history.remove(text)
        self.history.insert(0, text)
        if len(self.history) > 20:
            self.history.pop()
        self.save_history()

    def load_history(self):
        """
        Load search history from QSettings.
        """
        return self.settings.value("history", [], type=list)

    def save_history(self):
        """
        Save search history to QSettings.
        """
        self.settings.setValue("history", self.history)

    def show_history_popup(self):
        """
        Populate and show the history list popup.
        """
        self.history_popup.clear()
        if not self.history:
            return

        for item_text in self.history:
            list_item = QListWidgetItem(self.history_popup)
            
            item_widget = QWidget()
            layout = QHBoxLayout(item_widget)
            layout.setContentsMargins(5, 2, 5, 2)
            layout.setSpacing(10)
            
            # Use a button for the text to make it clickable
            text_button = QPushButton(item_text)
            text_button.setStyleSheet("QPushButton { border: none; text-align: left; }")
            text_button.setFlat(True)
            text_button.clicked.connect(lambda _, t=item_text: self._select_history_item(t))

            delete_button = QPushButton("X")
            delete_button.setFixedSize(20, 20)
            delete_button.setStyleSheet("QPushButton { border: none; color: red; font-weight: bold; }")
            delete_button.clicked.connect(lambda _, t=item_text: self.remove_history_item(t))
            
            layout.addWidget(text_button)
            layout.addStretch()
            layout.addWidget(delete_button)
            
            item_widget.setLayout(layout)
            list_item.setSizeHint(item_widget.sizeHint())
            
            self.history_popup.addItem(list_item)
            self.history_popup.setItemWidget(list_item, item_widget)

        # 定位弹出窗口
        point = self.mapToGlobal(QPoint(0, self.height()))
        self.history_popup.move(point)
        self.history_popup.setFixedWidth(self.width())
        self.history_popup.show()

    def _select_history_item(self, text):
        """
        处理历史记录项的选择。
        """
        if not text:
            return
        self.setText(text)
        self.add_to_history(text)  # 更新历史记录，将其移到最前面
        self.search_triggered.emit(text)
        self.history_popup.hide()

    def remove_history_item(self, text):
        """
        Remove a specific item from the history.
        """
        if text in self.history:
            self.history.remove(text)
            self.save_history()
            self.show_history_popup() # Refresh the list

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication, QVBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    main_widget = QWidget()
    layout = QVBoxLayout(main_widget)
    
    search_box = SearchLineEdit()
    search_box.setPlaceholderText("双击此处查看历史记录")
    
    def handle_search(query):
        print(f"执行搜索: {query}")
        
    search_box.search_triggered.connect(handle_search)
    
    layout.addWidget(search_box)
    main_widget.setWindowTitle("自定义搜索框测试")
    main_widget.show()
    
    sys.exit(app.exec_())
