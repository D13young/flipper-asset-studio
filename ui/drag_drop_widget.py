from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from pathlib import Path

from ui.i18n import trf, tr

class DragDropArea(QWidget):
    """Область для Drag-and-Drop импорта файлов"""

    files_dropped = pyqtSignal(list)  # Сигнал с списком путей файлов

    # Имя объекта используется селектором в глобальной теме
    # (ui/styles.py -> QLabel#dragDropLabel), чтобы цвета следовали теме (A4).
    LABEL_OBJECT_NAME = "dragDropLabel"

    def __init__(self, title: str = "", accepted_extensions=None):
        super().__init__()
        self.accepted_extensions = accepted_extensions or [".png"]
        self._default_text = title
        self.setAcceptDrops(True)
        self._setup_ui(title)

    def set_text(self, text: str):
        """Обновить основной текст области и перерисовать его."""
        self._default_text = text
        self.label.setText(text)

    def _setup_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.label = QLabel(title)
        self.label.setObjectName(self.LABEL_OBJECT_NAME)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setMinimumSize(200, 100)

        layout.addWidget(self.label)
        self.setLayout(layout)

    def _set_state(self, state: str):
        """Переключает динамическое свойство 'state' для перекраски из темы.

        Явного setStyleSheet здесь нет (A4): фон/граница/цвет берутся из
        активной темы селектором QLabel#dragDropLabel[state=...]. Чтобы Qt
        перерисовал виджет при смене свойства, нужен unpolish/polish.
        """
        current = self.label.property("state") or ""
        if current == state:
            return
        self.label.setProperty("state", state or None)
        style = self.label.style()
        style.unpolish(self.label)
        style.polish(self.label)

    def _reset_state(self):
        """Возврат к обычному виду (снятие drag/active) и тексту по умолчанию."""
        self._set_state("")
        self.label.setText(self._default_text)

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
                self._set_state("drag")
            else:
                event.ignore()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """Событие при уходе файла с области"""
        self._reset_state()

    def dropEvent(self, event: QDropEvent):
        """Событие при отпускании файлов"""
        self._reset_state()

        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            dropped_files = []

            for url in urls:
                file_path = url.toLocalFile()
                if Path(file_path).suffix.lower() in self.accepted_extensions:
                    dropped_files.append(file_path)

            if dropped_files:
                self.files_dropped.emit(dropped_files)
                self.label.setText(trf("drag.loaded", count=len(dropped_files)))
            else:
                QMessageBox.warning(
                    self,
                    tr("drag.wrong_format_title"),
                    trf("drag.wrong_format_msg", exts=", ".join(self.accepted_extensions))
                )
        else:
            event.ignore()

    def set_active(self, active: bool):
        """Визуальная индикация активности"""
        if active:
            self._set_state("active")
        else:
            self._reset_state()