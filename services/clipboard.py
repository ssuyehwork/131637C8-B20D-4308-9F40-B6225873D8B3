# -*- coding: utf-8 -*-
# services/clipboard.py
import datetime
import os
import uuid
import hashlib
from PyQt5.QtCore import QObject, pyqtSignal, QBuffer
from PyQt5.QtGui import QImage

class ClipboardManager(QObject):
    """
    管理剪贴板数据，处理数据并将其存入数据库。
    """
    # 【核心修改】信号携带参数：新增数据的 ID
    data_captured = pyqtSignal(int)

    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self._last_hash = None

    def _hash_data(self, data):
        """为数据创建一个简单的哈希值以检查重复。"""
        if isinstance(data, QImage):
            # 对图片，哈希其原始字节数据
            return hash(data.bits().tobytes())
        # 对于字符串，先编码
        return hashlib.md5(str(data).encode('utf-8')).hexdigest()

    def process_clipboard(self, mime_data, category_id=None):
        """
        处理来自剪贴板的 MIME 数据。
        """
        try:
            # 优先处理 URL (文件路径)
            if mime_data.hasUrls():
                urls = mime_data.urls()
                filepaths = [url.toLocalFile() for url in urls if url.isLocalFile()]
                
                if filepaths:
                    content = ";".join(filepaths)
                    current_hash = self._hash_data(content)
                    
                    # 即使哈希相同，如果是文件操作可能也需要记录，这里保持去重逻辑
                    if current_hash != self._last_hash:
                        print(f"[Clipboard] 捕获到文件: {content}")
                        # 获取返回的 idea_id
                        idea_id = self.db.add_clipboard_item(item_type='file', content=content, category_id=category_id)
                        self._last_hash = current_hash
                        # 【核心修改】发射带有 ID 的信号
                        if idea_id:
                            self.data_captured.emit(idea_id)
                        return

            # 处理图片
            if mime_data.hasImage():
                image = mime_data.imageData()
                # 注意：QImage 直接哈希可能不稳定，这里简化处理，实际项目建议转换后哈希
                buffer = QBuffer()
                buffer.open(QBuffer.ReadWrite)
                image.save(buffer, "PNG")
                image_bytes = buffer.data()
                
                current_hash = hashlib.md5(image_bytes).hexdigest()
                
                if current_hash != self._last_hash:
                    print("[Clipboard] 捕获到图片。")
                    idea_id = self.db.add_clipboard_item(item_type='image', content='[Image Data]', data_blob=image_bytes, category_id=category_id)
                    self._last_hash = current_hash
                    if idea_id:
                        self.data_captured.emit(idea_id)
                    return

            # 处理文本
            if mime_data.hasText():
                text = mime_data.text()
                if not text.strip(): return
                
                current_hash = self._hash_data(text)
                if current_hash != self._last_hash:
                    print(f"[Clipboard] 捕获到文本: {text[:30]}...")
                    idea_id = self.db.add_clipboard_item(item_type='text', content=text, category_id=category_id)
                    self._last_hash = current_hash
                    if idea_id:
                        self.data_captured.emit(idea_id)
                    return

        except Exception as e:
            print(f"处理剪贴板数据时出错: {e}")