from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from pathlib import Path

class DragDropArea(QWidget):
    """Область для Drag-and-Drop импорта файлов"""
    
    files_dropped = pyqtSignal(list)  # Сигнал с списком путей файлов
    
    def __init__(self, title: str = "Перетащите PNG файлы сюда", accepted_extensions=None):
        super().__init__()
        self.accepted_extensions = accepted_extensions or [".png"]
        self.setAcceptDrops(True)
        self._setup_ui(title)

    def _setup_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.label = QLabel(title)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            QLabel {
                background-color: #1a1a2e;
                border: 3px dashed #4a4a6a;
                border-radius: 10px;
                padding: 40px;
                color: #888;
                font-size: 16px;
                font-weight: bold;
            }
            QLabel:hover {
                background-color: #252545;
                border-color: #6a6a9a;
                color: #aaa;
            }
        """)
        self.label.setMinimumSize(200, 100)
        
        layout.addWidget(self.label)
        self.setLayout(layout)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Событие при перетаскивании файла над областью"""
        if event.mimeData().hasUrls():
            # Проверяем, есть ли подходящие файлы
            urls = event.mimeData().urls()
            valid_files = [
                url.toLocalFile() for url in urls 
                if Path(url.toLocalFile()).suffix.lower() in self.accepted_extensions
            ]
            
            if valid_files:
                event.acceptProposedAction()
                self.label.setStyleSheet("""
                    QLabel {
                        background-color: #2a2a4e;
                        border: 3px dashed #00ff00;
                        border-radius: 10px;
                        padding: 40px;
                        color: #00ff00;
                        font-size: 18px;
                        font-weight: bold;
                    }
                """)
            else:
                event.ignore()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Событие при уходе файла с области"""
        self._reset_style()

    def dropEvent(self, event: QDropEvent):
        """Событие при отпускании файлов"""
        self._reset_style()
        
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            dropped_files = []
            
            for url in urls:
                file_path = url.toLocalFile()
                if Path(file_path).suffix.lower() in self.accepted_extensions:
                    dropped_files.append(file_path)
            
            if dropped_files:
                self.files_dropped.emit(dropped_files)
                self.label.setText(f"✅ Загружено файлов: {len(dropped_files)}")
            else:
                QMessageBox.warning(
                    self, 
                    "Неверный формат", 
                    f"Принимаются только файлы: {', '.join(self.accepted_extensions)}"
                )
        else:
            event.ignore()

    def _reset_style(self):
        """Сброс стиля к исходному"""
        self.label.setStyleSheet("""
            QLabel {
                background-color: #1a1a2e;
                border: 3px dashed #4a4a6a;
                border-radius: 10px;
                padding: 40px;
                color: #888;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        self.label.setText("Перетащите PNG файлы сюда")

    def set_active(self, active: bool):
        """Визуальная индикация активности"""
        if active:
            self.label.setStyleSheet("""
                QLabel {
                    background-color: #1a3a1a;
                    border: 3px solid #00ff00;
                    border-radius: 10px;
                    padding: 40px;
                    color: #00ff00;
                }
            """)
        else:
            self._reset_style()