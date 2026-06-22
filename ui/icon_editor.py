from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QSpinBox,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QFileDialog,
    QComboBox,
    QToolButton,
)

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon

from pathlib import Path

from core.image_processor import FlipperImageProcessor


class IconEditorWidget(QWidget):
    # Сигнал для передачи готовых данных в главный экспорт
    # app_name, frames_bytes, w, h, dither_level
    icon_ready = pyqtSignal(str, list, int, int, int)


    def __init__(self):
        super().__init__()
        self.frames = []
        self._setup_ui()


    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Настройки иконки
        settings_group = QGroupBox("Settings")

        settings_layout = QFormLayout()
        
        self.app_name_edit = QLineEdit("passport")
        self.app_name_edit.setEnabled(False)

        self.passport_kind_cb = QComboBox()
        self.passport_kind_cb.addItems(["passport_128x64", "passport_bad_46x49", "passport_happy_46x49", "passport_okay_46x49"])
        self.passport_kind_cb.setCurrentText("passport_128x64")
        self.app_name_edit.setToolTip("Название папки приложения (например: RFID, NFC, SubGhz)")
        
        self.spin_w = QSpinBox()
        self.spin_w.setRange(1, 128)
        self.spin_w.setValue(128)
        self.spin_w.setEnabled(False)

        self.spin_h = QSpinBox()
        self.spin_h.setRange(1, 128)
        self.spin_h.setValue(64)
        self.spin_h.setEnabled(False)

        self.dither_cb = QComboBox()
        self.dither_cb.addItems(["0 (без дизеринга)", "1 (Floyd-Steinberg)"])
        self.dither_cb.setCurrentIndex(1)

        settings_layout.addRow("App Name:", self.app_name_edit)
        settings_layout.addRow("Passport file:", self.passport_kind_cb)
        settings_layout.addRow("Width:", self.spin_w)
        settings_layout.addRow("Height:", self.spin_h)
        settings_layout.addRow("Dither level:", self.dither_cb)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)



        # Список кадров
        self.frame_list = QListWidget()
        self.frame_list.setIconSize(QSize(96, 96))

        self.frame_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.frame_list.setFlow(QListWidget.Flow.LeftToRight)
        self.frame_list.setWrapping(True)
        self.frame_list.setFixedHeight(150)
        layout.addWidget(self.frame_list)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.btn_add = QToolButton()
        self.btn_add.setText("Add Frames")
        
        self.btn_clear = QToolButton()
        self.btn_clear.setText("Clear")

        # Qt standard icons
        from PyQt6.QtWidgets import QStyle
        style = self.style()
        self.btn_add.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        self.btn_clear.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon))

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_clear)
        layout.addLayout(btn_layout)

        # Инфо
        self.lbl_status = QLabel("")

        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

        # Подключение сигналов
        self.btn_add.clicked.connect(self._add_frames)
        self.btn_clear.clicked.connect(self._clear)

        self.app_name_edit.textChanged.connect(self._apply_passport_preset)
        self.passport_kind_cb.currentTextChanged.connect(self._apply_passport_kind_preset)
        self.dither_cb.currentTextChanged.connect(self._emit_ready)


        self._apply_passport_preset()
        self._apply_passport_kind_preset(self.passport_kind_cb.currentText())


    def _add_frames(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add Icon Frames", "", "PNG (*.png)")
        dither_level = int(self.dither_cb.currentText().split(" ")[0])

        for p in sorted(paths):
            filename = Path(p).name

            # Конвертируем PNG → байты Flipper → превью, чтобы превью отображалось в списке
            # process_png ждёт параметр dither_level
            proc = FlipperImageProcessor.process_png(p, dither_level=dither_level)




            preview_pm = proc["preview"]
            frame_bytes = proc["bytes"]

            item = QListWidgetItem(filename)
            item.setData(Qt.ItemDataRole.UserRole, {
                "path": p,
                "bytes": frame_bytes,
                "preview": preview_pm,
            })

            item.setIcon(QIcon(preview_pm))
            self.frame_list.addItem(item)

        self._emit_ready()


    def _clear(self):
        self.frame_list.clear()
        self.frames = []
        self._emit_ready()

    def _apply_passport_kind_preset(self, file_name: str | None = None):

        """Устанавливает App Name и размеры строго под 4 варианта passport-файлов."""
        if file_name is None:
            file_name = self.passport_kind_cb.currentText()

        file_name = (file_name or "").strip()
        mapping = {
            "passport_128x64": ("passport", 128, 64),
            "passport_bad_46x49": ("passport_bad", 46, 49),
            "passport_happy_46x49": ("passport_happy", 46, 49),
            "passport_okay_46x49": ("passport_okay", 46, 49),
        }

        if file_name in mapping:
            app_name, w, h = mapping[file_name]
            # Блокируем сигнал, чтобы не было лишних рекурсий
            self.app_name_edit.blockSignals(True)
            self.app_name_edit.setText(app_name)
            self.app_name_edit.blockSignals(False)
            if self.spin_w.value() != w:
                self.spin_w.setValue(w)
            if self.spin_h.value() != h:
                self.spin_h.setValue(h)

    def _apply_passport_preset(self):
        # legacy fallback: если пользователь меняет App Name вручную
        base = (self.app_name_edit.text() or "").strip().lower()
        if base == "passport":
            if self.spin_w.value() != 128:
                self.spin_w.setValue(128)
            if self.spin_h.value() != 64:
                self.spin_h.setValue(64)
            return

        if base in {"passport_bad", "passport_happy", "passport_okay"}:
            if self.spin_w.value() != 46:
                self.spin_w.setValue(46)
            if self.spin_h.value() != 49:
                self.spin_h.setValue(49)
            return


    def _emit_ready(self):

        count = self.frame_list.count()
        # В Icons fps/анимация не используются, поэтому надпись убираем
        _ = count
        
        # Собираем данные для экспорта.
        payload = []
        for i in range(count):
            data = self.frame_list.item(i).data(Qt.ItemDataRole.UserRole)
            if isinstance(data, dict):
                payload.append(data.get("bytes"))
            else:
                payload.append(data)

        dither_level = int(self.dither_cb.currentText().split(" ")[0])

        self.icon_ready.emit(
            self.passport_kind_cb.currentText().split("_")[0],
            payload,

            self.spin_w.value(),
            self.spin_h.value(),
            dither_level,
        )


