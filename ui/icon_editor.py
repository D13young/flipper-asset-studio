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
    QSplitter,
)

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon

from pathlib import Path

from core.image_processor import FlipperImageProcessor
from ui.drag_drop_widget import DragDropArea
from ui.i18n import tr


class IconEditorWidget(QWidget):
    icon_ready = pyqtSignal(str, list, int, int, int)

    def __init__(self):
        super().__init__()
        self.frames = []
        self._setup_ui()

    def _on_dither_changed(self):
        """При переключении дизеринга пересчитываем bytes/preview для всех загруженных кадров."""
        w = int(self.spin_w.value())
        h = int(self.spin_h.value())
        dither_level = int(self.dither_cb.currentText().split(" ")[0])

        count = self.frame_list.count()
        for i in range(count):
            item = self.frame_list.item(i)
            data = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(data, dict):
                continue
            p = data.get("path")
            if not p:
                continue

            proc = FlipperImageProcessor.process_png(
                p,
                dither_level=dither_level,
                output_w=w,
                output_h=h,
            )

            preview_pm = proc["preview"]
            frame_bytes = proc["bytes"]

            item.setData(
                Qt.ItemDataRole.UserRole,
                {
                    "path": p,
                    "bytes": frame_bytes,
                    "preview": preview_pm,
                },
            )
            item.setIcon(QIcon(preview_pm))

        self._emit_ready()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # ── Левая колонка: настройки + статус ──
        left_panel = QWidget()
        left_panel.setMinimumWidth(240)
        left_panel.setMaximumWidth(330)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Настройки иконки
        self.settings_group = QGroupBox(tr("icon.group_settings"))

        self.settings_layout = QFormLayout(self.settings_group)
        self.settings_layout.setVerticalSpacing(8)

        self.app_name_edit = QLineEdit("passport")
        self.app_name_edit.setEnabled(False)

        self.passport_kind_cb = QComboBox()
        self.passport_kind_cb.addItems(["passport_128x64", "passport_bad_46x49", "passport_happy_46x49", "passport_okay_46x49"])
        self.passport_kind_cb.setCurrentText("passport_128x64")
        self.app_name_edit.setToolTip(tr("icon.tip_app_name"))

        self.spin_w = QSpinBox()
        self.spin_w.setRange(1, 128)
        self.spin_w.setValue(128)
        self.spin_w.setEnabled(True)

        self.spin_h = QSpinBox()
        self.spin_h.setRange(1, 128)
        self.spin_h.setValue(64)
        self.spin_h.setEnabled(True)

        self.dither_cb = QComboBox()
        self.dither_cb.addItems(["0", "1"])
        self.dither_cb.setCurrentIndex(0)

        self.settings_layout.addRow(tr("icon.lbl_app_name"), self.app_name_edit)
        self.settings_layout.addRow(tr("icon.lbl_passport_file"), self.passport_kind_cb)
        self.settings_layout.addRow(tr("icon.lbl_dither_level"), self.dither_cb)
        left_layout.addWidget(self.settings_group)

        left_layout.addStretch(1)

        # Инфо
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setObjectName("tabStatus")
        left_layout.addWidget(self.lbl_status)

        splitter.addWidget(left_panel)

        # ── Правая колонка: кадры иконки ──
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.frames_group = QGroupBox(tr("icon.group_frames"))
        frames_layout = QVBoxLayout(self.frames_group)
        frames_layout.setContentsMargins(8, 8, 8, 8)
        frames_layout.setSpacing(6)

        # Drag-and-Drop область
        self.drag_drop = DragDropArea(tr("icon.drag_title"), [".png"])
        self.drag_drop.files_dropped.connect(self.add_frames)
        frames_layout.addWidget(self.drag_drop)

        # Список кадров
        self.frame_list = QListWidget()
        self.frame_list.setIconSize(QSize(320, 320))

        self.frame_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.frame_list.setFlow(QListWidget.Flow.LeftToRight)
        self.frame_list.setWrapping(True)
        # Поле превью иконок сделано крупнее и растяжимым (T6).
        self.frame_list.setMinimumHeight(300)
        self.frame_list.setMaximumHeight(560)
        frames_layout.addWidget(self.frame_list, 1)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.btn_add = QToolButton()
        self.btn_add.setText(tr("icon.btn_add"))

        self.btn_clear = QToolButton()
        self.btn_clear.setText(tr("icon.btn_clear"))

        # Qt standard icons
        from PyQt6.QtWidgets import QStyle
        style = self.style()
        self.btn_add.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        self.btn_clear.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon))

        btn_layout.addWidget(self.btn_add)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_clear)
        frames_layout.addLayout(btn_layout)

        right_layout.addWidget(self.frames_group, 1)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 760])

        layout.addWidget(splitter, 1)

        # Подключение сигналов
        self.btn_add.clicked.connect(self._add_frames)
        self.btn_clear.clicked.connect(self._clear)

        self.app_name_edit.textChanged.connect(self._apply_passport_preset)
        self.passport_kind_cb.currentTextChanged.connect(self._apply_passport_kind_preset)
        self.dither_cb.currentTextChanged.connect(self._on_dither_changed)

        self._apply_passport_preset()
        self._apply_passport_kind_preset(self.passport_kind_cb.currentText())

    def retranslate(self):
        """Обновляет тексты при смене языка."""
        self.settings_group.setTitle(tr("icon.group_settings"))
        self.app_name_edit.setToolTip(tr("icon.tip_app_name"))
        self.settings_layout.labelForField(self.app_name_edit).setText(tr("icon.lbl_app_name"))
        self.settings_layout.labelForField(self.passport_kind_cb).setText(tr("icon.lbl_passport_file"))
        self.settings_layout.labelForField(self.dither_cb).setText(tr("icon.lbl_dither_level"))
        self.drag_drop.set_text(tr("icon.drag_title"))
        self.btn_add.setText(tr("icon.btn_add"))
        self.btn_clear.setText(tr("icon.btn_clear"))
        self.frames_group.setTitle(tr("icon.group_frames"))

    def add_frames(self, paths):
        dither_level = int(self.dither_cb.currentText().split(" ")[0])
        w = int(self.spin_w.value())
        h = int(self.spin_h.value())

        for p in sorted(paths):
            filename = Path(p).name

            proc = FlipperImageProcessor.process_png(
                p,
                dither_level=dither_level,
                output_w=w,
                output_h=h,
            )

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

    def _add_frames(self):
        paths, _ = QFileDialog.getOpenFileNames(self, tr("icon.select_frames"), "", "PNG (*.png)")
        self.add_frames(paths)

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
            self.app_name_edit.blockSignals(True)
            self.app_name_edit.setText(app_name)
            self.app_name_edit.blockSignals(False)
            if self.spin_w.value() != w:
                self.spin_w.setValue(w)
            if self.spin_h.value() != h:
                self.spin_h.setValue(h)

    def _apply_passport_preset(self):
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
