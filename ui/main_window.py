# ui/main_window.py
import os
from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QListWidget, QLabel, QTabWidget,
    QToolBar, QToolButton, QMenu, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QFileDialog, QMessageBox, QCheckBox, QTextEdit,
    QSizePolicy,
)
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

from PyQt6.QtCore import Qt, QSize, QTimer, QSettings
from PyQt6.QtGui import QIcon
from pathlib import Path

from ui.styles import load_qss, THEME_NAMES, DEFAULT_THEME
from ui.i18n import tr, trf, set_language, get_language, LANGUAGE_ORDER, LANGUAGES



from core.image_processor import FlipperImageProcessor
from core.animation_manager import FlipperAnimationManager
from core.exporter import FlipperExporter
from ui.animation_timeline import AnimationTimelineWidget
from ui.icon_editor import IconEditorWidget
from core.icon_builder import FlipperIconBuilder
from ui.drag_drop_widget import DragDropArea
from ui.validator_widget import ValidatorWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("app.title"))
        self.resize(1280, 840)

        # Garanty resize on macOS
        self.setMinimumSize(800, 600)
        
        # Данные приложения
        self.current_asset_path = None
        self.anim_manager = FlipperAnimationManager()
        
        # Состояние анимации
        self.anim_timer = QTimer(self)
        self.anim_timer.setSingleShot(False)
        self.anim_timer.timeout.connect(self._next_anim_frame)
        self._anim_frames = []
        self._anim_idx = 0

        # Настройки приложения (сохранение выбранной темы и языка)
        self.settings = QSettings("FlipperAssetStudio", "FlipperAssetStudio")

        # Инициализация UI
        self._setup_ui()
        self._setup_toolbar()
        self._setup_statusbar()

        # Тема оформления (стили + кнопка переключения)
        self._apply_theme(self._load_saved_theme())

        # Язык интерфейса (кнопка переключения + локализация строк)
        self._apply_language(self._load_saved_language())

        self._connect_signals()


    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        
        # --- Левая панель (Навигация) ---
        self.nav_list = QListWidget()
        self.nav_list.addItems([
            tr("nav.create"),
            tr("nav.single_image"),
            tr("nav.jpg_crop"),
            tr("nav.gif_to_png"),
            tr("nav.animation_builder"),
            tr("nav.meta_preview"),
            tr("nav.icons"),
            tr("nav.validator"),
            tr("nav.bm_bmx_preview"),
        ])



        self.nav_list.setMinimumWidth(220)
        # Сигнал подключения будет в _connect_signals(), после создания tabs
        splitter.addWidget(self.nav_list)

        # --- Правая панель (Контент) ---
        right = QWidget()
        right.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 1. Вкладка: Single Image с Drag-and-Drop
        tab_single = QWidget()

        sl = QVBoxLayout(tab_single)
        
        # Drag-and-Drop область
        self.drag_drop = DragDropArea("Перетащите PNG или нажмите Import", [".png"])

        self.drag_drop.files_dropped.connect(self._on_files_dropped)
        sl.addWidget(self.drag_drop)
        
        # Или обычный превью
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(384, 192)
        self.preview_label.setText(tr("single.preview_hint"))

        self.preview_label.setScaledContents(True)
        self.preview_label.setVisible(False)  # Скрыт по умолчанию

        shadow = QGraphicsDropShadowEffect(self.preview_label)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(Qt.GlobalColor.black)
        self.preview_label.setGraphicsEffect(shadow)

        sl.addWidget(self.preview_label)

        
        self.dither_cb = QCheckBox(tr("single.dither"))
        self.dither_cb.setChecked(True)
        sl.addWidget(self.dither_cb)

        # 2. Вкладка: Animation
        self.anim_preview = QLabel()
        self.anim_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.anim_preview.setMinimumHeight(192)
        self.anim_preview.setText(tr("anim.preview_hint"))

        shadow = QGraphicsDropShadowEffect(self.anim_preview)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(Qt.GlobalColor.black)
        self.anim_preview.setGraphicsEffect(shadow)

        
        self.anim_timeline = AnimationTimelineWidget(self.anim_manager)
        tab_anim = QWidget()
        al = QVBoxLayout(tab_anim)
        al.addWidget(self.anim_preview)
        al.addWidget(self.anim_timeline)

        # 3. Вкладка: Meta
        tab_meta = QWidget()
        ml = QVBoxLayout(tab_meta)
        self.meta_text = QTextEdit()
        self.meta_text.setReadOnly(True)
        ml.addWidget(self.meta_text)
        tab_meta.setLayout(ml)

        # 4. Вкладка: Icons
        self.icon_editor = IconEditorWidget()
        tab_icons = QWidget()
        il = QVBoxLayout(tab_icons)
        il.addWidget(self.icon_editor)
        tab_icons.setLayout(il)

        # 5. Вкладка: Validator
        self.validator_widget = ValidatorWidget()
        tab_validator = QWidget()
        vl = QVBoxLayout(tab_validator)
        vl.addWidget(self.validator_widget)
        tab_validator.setLayout(vl)

        # 6. Вкладка: BM/BMX Preview
        self.bm_bmx_preview_drop = DragDropArea(tr("bm.drop_title"), [".bm", ".bmx"])

        self.bm_bmx_preview_label = QLabel()
        self.bm_bmx_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bm_bmx_preview_label.setMinimumSize(328, 264)
        self.bm_bmx_preview_label.setText(tr("bm.preview_hint"))

        self.bm_bmx_preview_label.setScaledContents(True)

        shadow = QGraphicsDropShadowEffect(self.bm_bmx_preview_label)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(Qt.GlobalColor.black)
        self.bm_bmx_preview_label.setGraphicsEffect(shadow)

        tab_bm_bmx = QWidget()
        bml = QVBoxLayout(tab_bm_bmx)
        bml.addWidget(self.bm_bmx_preview_drop)
        bml.addWidget(self.bm_bmx_preview_label)
        tab_bm_bmx.setLayout(bml)

        self.bm_bmx_preview_drop.files_dropped.connect(self._on_bm_bmx_files_dropped)

        # 7. Вкладка: Create (ручная отрисовка)

        from ui.create_editor import CreateEditorWidget
        from ui.jpg_crop_editor import JpegCropEditorWidget
        from ui.gif_crop_editor import GifCropEditorWidget
        self.jpg_crop_editor = JpegCropEditorWidget()
        
        tab_jpg_crop = QWidget()
        jl = QVBoxLayout(tab_jpg_crop)
        jl.addWidget(self.jpg_crop_editor)
        tab_jpg_crop.setLayout(jl)

        self.gif_crop_editor = GifCropEditorWidget()

        tab_gif_crop = QWidget()
        gl = QVBoxLayout(tab_gif_crop)
        gl.addWidget(self.gif_crop_editor)
        tab_gif_crop.setLayout(gl)

        self.create_editor = CreateEditorWidget()

        tab_create = QWidget()
        cl = QVBoxLayout(tab_create)
        cl.addWidget(self.create_editor)
        tab_create.setLayout(cl)

        # Сборка табов
        self.tabs = QTabWidget()

        icons_dir = Path(__file__).resolve().parent.parent / "assets" / "icons"

        tab_defs = [
            (tab_create, tr("tab.create"), icons_dir / "create.svg"),
            (tab_single, tr("tab.single"), icons_dir / "single.svg"),
            (tab_jpg_crop, tr("tab.jpg_crop"), icons_dir / "jpg_crop.svg"),
            (tab_gif_crop, tr("tab.gif_to_png"), icons_dir / "animation.svg"),
            (tab_anim, tr("tab.animation"), icons_dir / "animation.svg"),
            (tab_meta, tr("tab.meta"), icons_dir / "meta.svg"),
            (tab_icons, tr("tab.icons"), icons_dir / "icons.svg"),
            (tab_validator, tr("tab.validator"), icons_dir / "validator.svg"),
            (tab_bm_bmx, tr("tab.bm_bmx"), icons_dir / "bm_bmx.svg"),
        ]

        for widget, text, icon_path in tab_defs:
            tab_index = self.tabs.addTab(widget, text)
            if icon_path.exists():
                self.tabs.setTabIcon(tab_index, QIcon(str(icon_path)))



        self.tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.tabs)
        right_layout.setStretch(0, 1)


        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        layout.addWidget(splitter)
        layout.setStretch(0, 1)

    def _setup_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        tb.setFixedHeight(36)
        self.addToolBar(tb)

        icons_dir = Path(__file__).resolve().parent.parent / "assets" / "icons"

        def _icon(name: str) -> QIcon | None:
            p = icons_dir / name
            if p.exists():
                return QIcon(str(p))
            return None

        # Кнопки (иконки + короткий текст)
        self.btn_import = QPushButton(" " + tr("tb.import"))
        icon = _icon("create.svg") or _icon("single.svg") or _icon("icons.svg")
        if icon:
            self.btn_import.setIcon(icon)
            self.btn_import.setIconSize(QSize(18, 18))

        self.btn_import.setFixedWidth(110)

        self.btn_export = QPushButton(" " + tr("tb.export"))
        icon = _icon("animation.svg") or _icon("meta.svg") or _icon("validator.svg")
        if icon:
            self.btn_export.setIcon(icon)
            self.btn_export.setIconSize(QSize(18, 18))

        self.btn_export.setFixedWidth(110)

        self.btn_exit = QPushButton(" " + tr("tb.exit"))
        icon = _icon("validator.svg") or _icon("meta.svg") or _icon("icons.svg")
        if icon:
            self.btn_exit.setIcon(icon)
            self.btn_exit.setIconSize(QSize(18, 18))

        self.btn_exit.setFixedWidth(90)

        tb.addWidget(self.btn_import)
        tb.addSeparator()
        tb.addWidget(self.btn_export)
        tb.addSeparator()
        tb.addWidget(self.btn_exit)

        # --- Справа: кнопка смены темы ---
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)

        self.theme_btn = QToolButton()
        self.theme_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.theme_btn.setStatusTip(tr("tb.theme_tip"))

        self.theme_menu = QMenu(self)
        self.theme_actions = {}
        for tname in THEME_NAMES:
            action = self.theme_menu.addAction(tname)
            action.setCheckable(True)
            action.triggered.connect(lambda _, n=tname: self._apply_theme(n))
            self.theme_actions[tname] = action

        self.theme_btn.setMenu(self.theme_menu)
        tb.addWidget(self.theme_btn)

        # --- Справа: кнопка смены языка (рядом с кнопкой Theme) ---
        self.lang_btn = QToolButton()
        self.lang_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.lang_btn.setObjectName("langBtn")
        self.lang_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.lang_btn.setStatusTip(tr("tb.language_tip"))

        self.lang_menu = QMenu(self)
        self.lang_actions = {}
        for lid in LANGUAGE_ORDER:
            action = self.lang_menu.addAction(LANGUAGES[lid])
            action.setCheckable(True)
            action.setData(lid)
            action.triggered.connect(lambda _, lid=lid: self._apply_language(lid))
            self.lang_actions[lid] = action

        self.lang_btn.setMenu(self.lang_menu)
        self.lang_btn.setText(tr("tb.language"))
        tb.addWidget(self.lang_btn)

    def _load_saved_theme(self) -> str:
        saved = self.settings.value("ui/theme", DEFAULT_THEME)
        return saved if saved in THEME_NAMES else DEFAULT_THEME

    def _save_theme(self, name: str) -> None:
        self.settings.setValue("ui/theme", name)

    def _load_saved_language(self) -> str:
        saved = self.settings.value("ui/language", "ru")
        return saved if saved in LANGUAGES else "ru"

    def _save_language(self, lang: str) -> None:
        self.settings.setValue("ui/language", lang)

    def _apply_theme(self, name: str) -> None:
        if name not in THEME_NAMES:
            name = DEFAULT_THEME
        self.current_theme = name
        self.setStyleSheet(load_qss(name))
        self.theme_btn.setText(tr("tb.theme"))
        for tname, action in self.theme_actions.items():
            action.setChecked(tname == name)
        self._save_theme(name)

    def _apply_language(self, lang: str) -> None:
        """Переключает язык интерфейса и переводит все тексты."""
        lang = lang if lang in LANGUAGES else "ru"
        set_language(lang)
        for lid, action in self.lang_actions.items():
            action.setChecked(lid == lang)
        # Кнопка показывает название текущего языка
        self.lang_btn.setText(LANGUAGES[lang])
        self.retranslate()
        # Переводим дочерние виджеты
        for w in (self.create_editor, self.jpg_crop_editor, self.gif_crop_editor,
                  self.icon_editor, self.anim_timeline, self.validator_widget):
            retranslate = getattr(w, "retranslate", None)
            if callable(retranslate):
                retranslate()
        self._save_language(lang)

    def retranslate(self):
        """Переводит строки главного окна."""
        nav_items = [
            tr("nav.create"),
            tr("nav.single_image"),
            tr("nav.jpg_crop"),
            tr("nav.gif_to_png"),
            tr("nav.animation_builder"),
            tr("nav.meta_preview"),
            tr("nav.icons"),
            tr("nav.validator"),
            tr("nav.bm_bmx_preview"),
        ]
        for i, text in enumerate(nav_items):
            if i < self.nav_list.count():
                self.nav_list.item(i).setText(text)

        tab_keys = [
            "tab.create", "tab.single", "tab.jpg_crop", "tab.gif_to_png",
            "tab.animation", "tab.meta", "tab.icons", "tab.validator", "tab.bm_bmx",
        ]
        for i, key in enumerate(tab_keys):
            if i < self.tabs.count():
                self.tabs.setTabText(i, tr(key))

        self.btn_import.setText(" " + tr("tb.import"))
        self.btn_export.setText(" " + tr("tb.export"))
        self.btn_exit.setText(" " + tr("tb.exit"))
        self.theme_btn.setText(tr("tb.theme"))
        self.theme_btn.setStatusTip(tr("tb.theme_tip"))
        # Кнопка языка показывает название активного языка
        self.lang_btn.setText(LANGUAGES[get_language()])
        self.lang_btn.setStatusTip(tr("tb.language_tip"))

        self.statusBar().showMessage(tr("status.ready"))

        self.drag_drop.set_text(tr("single.drag_title"))
        self.preview_label.setText(tr("single.preview_hint"))
        self.anim_preview.setText(tr("anim.preview_hint"))
        self.bm_bmx_preview_drop.set_text(tr("bm.drop_title"))
        self.bm_bmx_preview_label.setText(tr("bm.preview_hint"))

    def _load_saved_theme(self) -> str:
        saved = self.settings.value("ui/theme", DEFAULT_THEME)
        return saved if saved in THEME_NAMES else DEFAULT_THEME

    def _save_theme(self, name: str) -> None:
        self.settings.setValue("ui/theme", name)

    def _apply_theme(self, name: str) -> None:
        if name not in THEME_NAMES:
            name = DEFAULT_THEME
        self.current_theme = name
        self.setStyleSheet(load_qss(name))
        self.theme_btn.setText(tr("tb.theme"))
        for tname, action in self.theme_actions.items():
            action.setChecked(tname == name)
        self._save_theme(name)

    def _setup_statusbar(self):
        self.statusBar().showMessage(tr("status.ready"))

    def _connect_signals(self):
        # Кнопки
        self.btn_import.clicked.connect(self._import_png)
        self.btn_export.clicked.connect(self._export_pack)
        self.btn_exit.clicked.connect(self.close)
        
        # Чекбокс
        self.dither_cb.stateChanged.connect(self._process_single)

        
        # Навигация (теперь self.tabs точно существует)
        self.nav_list.currentRowChanged.connect(self.tabs.setCurrentIndex)
        
        # Таймлайн -> Превью и Мета
        self.anim_timeline.frames_updated.connect(self._on_anim_frames_updated)
        self.anim_timeline.meta_updated.connect(self.meta_text.setPlainText)
        
        # Изменение FPS -> Перезапуск таймера
        self.anim_timeline.spin_fps.valueChanged.connect(self._restart_animation)

        # Сигнал от редактора иконок
        self.icon_editor.icon_ready.connect(self._on_icon_data_ready)
        self.create_editor.icon_ready.connect(self._on_create_icon_data_ready)


    def _on_bm_bmx_files_dropped(self, files: list):
        if not files:
            return

        from core.bm_bmx_decoder import FlipperBmBmxDecoder
        from PyQt6.QtGui import QPixmap

        p = files[0]
        try:
            pm, w, h = FlipperBmBmxDecoder.load_frame_as_pixmap(p, scale=3)
            self.bm_bmx_preview_label.setPixmap(pm)
            self.bm_bmx_preview_label.setText("")
            self.statusBar().showMessage(trf("status.bm_ok", name=Path(p).name, w=w, h=h), 3000)

        except Exception as e:
            self.bm_bmx_preview_label.setPixmap(QPixmap())
            self.bm_bmx_preview_label.setText(trf("bm.error_label", err=e))
            self.statusBar().showMessage(trf("status.bm_err", name=Path(p).name, err=e), 5000)


    def _import_png(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("dlg.select_png"), "", "PNG Images (*.png)")
        if path:
            self.current_asset_path = path
            self.statusBar().showMessage(trf("status.loaded", name=os.path.basename(path)), 3000)
            self._process_single()



    def _process_single(self):
        if not self.current_asset_path:
            self.preview_label.setVisible(False)
            return

        try:
            # single-image: dither_cb переключает “включить/выключить” дизеринг
            dither_level = 1 if self.dither_cb.isChecked() else 0
            d = FlipperImageProcessor.process_png(self.current_asset_path, dither_level=dither_level)

            self.preview_label.setPixmap(d["preview"])
            self.preview_label.setVisible(True)
            self.statusBar().showMessage(trf("status.ok_128x64", size=d['byte_length']), 3000)
        except Exception as e:
            self.preview_label.setVisible(False)
            self.statusBar().showMessage(trf("status.error", err=e), 5000)


    def _on_icon_data_ready(self, app_name, paths, w, h, dither_level):
        """Вызывается, когда во вкладке Icons изменены данные"""
        pass


    def _on_create_icon_data_ready(self, app_name, frames_pixels_list, w, h, fps):
        """Вызывается, когда во вкладке Create изменены данные"""
        pass




    # --- Логика Анимации ---

    def _on_anim_frames_updated(self, frames_bytes):
        """Вызывается, когда в таймлайне изменились кадры"""
        self._anim_frames = frames_bytes
        self._anim_idx = 0
        if frames_bytes:
            self._restart_animation()
        else:
            self.anim_timer.stop()
            self.anim_preview.setText(tr("anim.preview_hint_short"))

    def _restart_animation(self):
        """Сброс и запуск таймера"""
        if not self._anim_frames: return
        
        self.anim_timer.stop()
        fps = max(1, self.anim_manager.meta_params["frame_rate"])
        self.anim_timer.setInterval(1000 // fps)
        self.anim_timer.start()
        
        self._next_anim_frame() # Показать первый кадр сразу

    def _next_anim_frame(self):
        """Тик таймера"""
        if not self._anim_frames: return
        
        # Циклический индекс
        idx = self._anim_idx % len(self._anim_frames)
        
        # Конвертация байтов в QPixmap
        pm = FlipperImageProcessor.bytes_to_preview(self._anim_frames[idx])
        self.anim_preview.setPixmap(pm)
        
        self._anim_idx += 1
        
    def _on_files_dropped(self, files: list):
        """Обработка сброшенных файлов"""
        if files:
            # Берем первый файл
            self.current_asset_path = files[0]
            self.statusBar().showMessage(f"📄 Drag&Drop: {len(files)} файл(ов)", 3000)
            self._process_single()
            
            active_tab = self.tabs.currentWidget()

            if active_tab == self.icon_editor.parent():
                for p in files:
                    item = self.icon_editor.frame_list.findItems(Path(p).name, Qt.MatchFlag.MatchExactly)
                    if item:
                        continue
                    # Вставляем именно dict с байтами, иначе export получит строку/путь и упадёт/не экспортирует корректно.
                    dither_level = int(self.icon_editor.dither_cb.currentText().split(" ")[0])
                    proc = FlipperImageProcessor.process_png(
                        p,
                        dither_level=dither_level,
                        output_w=self.icon_editor.spin_w.value(),
                        output_h=self.icon_editor.spin_h.value(),
                    )


                    preview_pm = proc["preview"]
                    frame_bytes = proc["bytes"]
                    from PyQt6.QtWidgets import QListWidgetItem
                    new_item = QListWidgetItem(Path(p).name)
                    new_item.setData(
                        Qt.ItemDataRole.UserRole,
                        {
                            "path": p,
                            "bytes": frame_bytes,
                            "preview": preview_pm,
                        },
                    )
                    new_item.setIcon(QIcon(preview_pm))
                    self.icon_editor.frame_list.addItem(new_item)
                self.icon_editor._emit_ready()

            elif active_tab == self.anim_timeline.parent():
                for f in files:
                    self.anim_manager.add_frame(f, dither_level=int(self.anim_timeline.spin_dither_level.value()))
                self.anim_timeline._refresh_list()
                self.anim_timeline._emit_updates()


            else:
                if len(files) > 1:
                    reply = QMessageBox.question(
                        self,
                        tr("dlg.add_to_animation"),
                        trf("dlg.multi_files", count=len(files)),
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:
                        self.tabs.setCurrentIndex(1)
                        for f in files:
                            self.anim_manager.add_frame(f)

                        self.anim_timeline._refresh_list()
                        self.anim_timeline._emit_updates()



    def _import_png(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("dlg.select_png"), "", "PNG Images (*.png)")
        if path:
            self.current_asset_path = path
            self.statusBar().showMessage(trf("status.loaded", name=os.path.basename(path)), 3000)
            self._process_single()    

    # --- Логика Экспорта ---

    def _export_pack(self):
        # Определяем, какая вкладка активна
        active_tab = self.tabs.currentWidget()
        out_dir = QFileDialog.getExistingDirectory(self, tr("dlg.export_folder"))
        if not out_dir: return

        try:
            if active_tab == self.anim_timeline.parent(): 
                # ЭКСПОРТ АНИМАЦИИ (Дельфин)
                if not self.anim_manager.frames:
                    raise ValueError(tr("msg.no_anim_frames"))
                
                meta = self.anim_manager.generate_meta_txt()
                manifest = self.anim_manager.generate_manifest_txt(
                    self.anim_timeline.line_name.text(),
                    self.anim_timeline.spin_bh_min.value(),
                    self.anim_timeline.spin_bh_max.value(),
                    self.anim_timeline.spin_lv_min.value(),
                    self.anim_timeline.spin_lv_max.value(),
                    self.anim_timeline.spin_weight.value(),
                )
                
                anim_name = self.anim_timeline.line_name.text()
                anims_out_dir = Path(out_dir) / "Anims"

                meta_txt = meta
                manifest_txt = manifest

                # ВАЖНО: экспорт анимации в формате Asset Pack Momentum:
                # manifest.txt должен быть ТОЛЬКО в папке Anims/ (не в папке конкретной анимации)
                # Поэтому генерим файл манифеста вручную и после вызова exporter удаляем его из anim_dir.

                FlipperExporter.export_animation(
                    self.anim_manager.get_frame_bytes_list(),
                    meta_txt,
                    manifest_txt,
                    anim_name,
                    anims_out_dir,
                    compressed=False,

                    create_zip=False
                )

                anim_dir = anims_out_dir / anim_name
                (anim_dir / "manifest.txt").unlink(missing_ok=True)

                # Momentum ожидает manifest.txt в корне папки Anims/.
                (anims_out_dir / "manifest.txt").write_text(manifest_txt, encoding="utf-8")


                msg = tr("msg.anim_exported")

            elif active_tab == self.create_editor.parent():

                frames_pixels_list = self.create_editor.get_frames_pixels_list()
                w, h, fps = self.create_editor.get_params()
                name_png = self.create_editor.name_png_edit.text().strip() or "icon"

                if not frames_pixels_list:
                    raise ValueError(tr("msg.no_create_frames"))

                # Экспортируем каждый кадр как отдельный PNG прямо в выбранную папку.
                from PIL import Image

                target_folder = Path(out_dir)

                def pixels_to_png(pixels_2d: list[list[int]], out_path: Path):
                    # 0 = black, 1 = white (по текущей логике canvas)
                    img = Image.new("L", (w, h), 0)
                    # создаём байтовый буфер 0/255 построчно
                    row_bytes = []
                    for yy in range(h):
                        row = [255 if int(pixels_2d[yy][xx]) else 0 for xx in range(w)]
                        row_bytes.extend(row)
                    img.putdata(row_bytes)
                    img.save(out_path, format="PNG")

                if len(frames_pixels_list) == 1:
                    out_path = target_folder / f"{name_png}.png"
                    pixels_to_png(frames_pixels_list[0], out_path)
                else:
                    for i, frame_pixels in enumerate(frames_pixels_list):
                        out_path = target_folder / f"{name_png}_{i:03d}.png"
                        pixels_to_png(frame_pixels, out_path)

                msg = trf("msg.create_exported", count=len(frames_pixels_list), folder=target_folder)



            elif active_tab == self.icon_editor.parent():


                # ЭКСПОРТ ИКОНКИ
                count = self.icon_editor.frame_list.count()
                if count == 0:
                    raise ValueError(tr("msg.no_icon_frames"))
                
                # UserRole хранит dict {path, bytes, preview}
                items = [self.icon_editor.frame_list.item(i) for i in range(count)]
                paths = []
                for it in items:
                    data = it.data(Qt.ItemDataRole.UserRole)
                    if isinstance(data, dict) and data.get("path"):
                        paths.append(data["path"])
                    else:
                        raise TypeError("Icons export: expected dict with 'path' in UserRole")

                w = self.icon_editor.spin_w.value()
                h = self.icon_editor.spin_h.value()
                # В Icons FPS не используется

                # app_name здесь используется как passport-kind (passport / passport_bad / ...)
                base_app = (self.icon_editor.app_name_edit.text() or "").strip().lower()
                dither_level = int(self.icon_editor.dither_cb.currentText().split(" ")[0])

                # Конвертируем PNG в байты Flipper с выбранным dither
                frame_bytes_list = []
                for p in paths:
                    proc = FlipperImageProcessor.process_png(
                        p,
                        dither_level=dither_level,
                        output_w=w,
                        output_h=h,
                    )
                    frame_bytes_list.append(proc["bytes"])


                # basename для passport (строго из ТЗ, без App Name в имени файла)
                file_basename = None
                if base_app == "passport":
                    file_basename = "passport_128x64"
                elif base_app in {"passport_bad", "passport_happy", "passport_okay"}:
                    file_basename = f"{base_app}_46x49"
                else:
                    # На случай если UI будет в другом состоянии
                    file_basename = "icon"

                # По ТЗ: создаём ровно: out_dir/Icons/Passport/<file>
                # self.icon_editor.app_name_edit — паспорт-категория, но она участвует только в имени файла.
                target_folder = Path(out_dir) / "Passport"

                # У passport-иконок нет анимации, поэтому FPS/кадровая логика не нужна
                
                FlipperIconBuilder.export_icon(
                    frame_bytes_list,
                    w,
                    h,
                    1,
                    output_folder=target_folder,
                    compress=True,
                    file_basename=file_basename,
                    frames_paths=paths,
                    dither_level=dither_level,
                )


                msg = trf("msg.icon_exported", name=file_basename)


            
            else:
                msg = "Выберите вкладку с контентом для экспорта"
            
            self.statusBar().showMessage(f"✅ {msg}", 5000)
            QMessageBox.information(self, tr("dlg.done"), msg)

        except Exception as e:
            QMessageBox.critical(self, tr("dlg.error"), str(e))


