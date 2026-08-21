from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QListWidget, QListWidgetItem, QFileDialog,
                             QProgressBar, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from collections import Counter
from pathlib import Path
from core.validator import FlipperAssetPackValidator, ValidationLevel
from ui.background import BackgroundRunner
from ui.i18n import tr, trf, get_language

class ValidatorWidget(QWidget):
    """Виджет для валидации Asset Pack"""
    
    pack_validated = pyqtSignal(bool)
    
    def __init__(self):
        super().__init__()
        self.validator = FlipperAssetPackValidator()
        self._pack_path_selected = False
        self._validating = False
        self._bg = BackgroundRunner(self)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Карточка «Asset Pack»
        self.pack_group = QGroupBox(tr("val.group_pack"))
        pack_layout = QVBoxLayout(self.pack_group)
        pack_layout.setSpacing(8)
        pack_layout.setContentsMargins(8, 8, 8, 8)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.btn_select = QPushButton(tr("val.btn_select"))
        self.btn_validate = QPushButton(tr("val.btn_validate"))
        self.btn_validate.setEnabled(False)
        btn_layout.addWidget(self.btn_select)
        btn_layout.addWidget(self.btn_validate)
        btn_layout.addStretch(1)
        pack_layout.addLayout(btn_layout)

        # Путь к папке
        self.lbl_path = QLabel(tr("val.path_default"))
        self.lbl_path.setObjectName("mutedLabel")
        self.lbl_path.setWordWrap(True)
        pack_layout.addWidget(self.lbl_path)

        # Прогресс
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        pack_layout.addWidget(self.progress)

        layout.addWidget(self.pack_group)

        # Результаты
        self.results_group = QGroupBox(tr("val.group_results"))
        results_layout = QVBoxLayout(self.results_group)
        results_layout.setContentsMargins(8, 8, 8, 8)

        self.results_list = QListWidget()
        self.results_list.setObjectName("validatorResults")
        self.results_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        results_layout.addWidget(self.results_list)
        layout.addWidget(self.results_group, 1)

        # Статистика
        self.lbl_stats = QLabel(tr("val.stats_default"))
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_stats.setObjectName("tabStatus")
        layout.addWidget(self.lbl_stats)

        # Подключение сигналов
        self.btn_select.clicked.connect(self._select_pack)
        self.btn_validate.clicked.connect(self._validate_pack)

    def retranslate(self):
        """Обновляет тексты при смене языка."""
        self.btn_select.setText(tr("val.btn_select"))
        self.btn_validate.setText(tr("val.btn_validate"))
        self.pack_group.setTitle(tr("val.group_pack"))
        self.results_group.setTitle(tr("val.group_results"))
        if not hasattr(self, "current_pack_path"):
            self.lbl_path.setText(tr("val.path_default"))
            self.lbl_stats.setText(tr("val.stats_default"))
        else:
            if not self.current_pack_path:
                self.lbl_path.setText(tr("val.path_default"))
        if self.results_list.count() == 0:
            self.lbl_stats.setText(tr("val.stats_default"))

        if getattr(self, "_has_validated", False) and not self._validating:
            if hasattr(self, "current_pack_path") and self.current_pack_path:
                self._validate_pack()

    def _select_pack(self):
        """Выбор папки Asset Pack"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            tr("val.select_folder"),
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.current_pack_path = Path(folder)
            self.lbl_path.setText(f"📂 {folder}")
            self.btn_validate.setEnabled(True)
            self.results_list.clear()
            self.lbl_stats.setText(tr("val.stats_default"))

    def _validate_pack(self):
        """Запуск валидации в фоновом потоке (UI не блокируется)."""
        if self._validating or not hasattr(self, 'current_pack_path'):
            return

        self.validator.language = get_language()

        self._validating = True
        self.btn_validate.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.results_list.clear()
        self.lbl_stats.setText(tr("val.stats_default"))

        self._bg.run(
            self.validator.validate_pack,
            on_done=self._on_validation_done,
            on_error=self._on_validation_error,
            args=(self.current_pack_path,),
        )

    def _on_validation_done(self, results: list):
        """Обработка результата валидации (вызывается в UI-потоке)."""
        self._validating = False
        self._has_validated = True
        self.btn_validate.setEnabled(True)
        self.progress.setRange(0, 100)
        self.progress.setValue(100)

        total = len(results)
        for i, result in enumerate(results):
            item = QListWidgetItem(self._format_result(result))
            item.setData(Qt.ItemDataRole.UserRole, result)

            if result.level == ValidationLevel.ERROR:
                item.setForeground(QColor("#ff6b6b"))
            elif result.level == ValidationLevel.WARNING:
                item.setForeground(QColor("#ffc94d"))
            elif result.level == ValidationLevel.SUCCESS:
                item.setForeground(QColor("#69db7c"))
            else:
                item.setForeground(QColor("#adb5bd"))

            self.results_list.addItem(item)
            if total:
                self.progress.setValue(int((i + 1) / total * 100))

        summary = Counter(r.level.value for r in results)
        stats_text = trf(
            "val.stats",
            total=sum(summary.values()),
            success=summary['success'],
            info=summary['info'],
            warning=summary['warning'],
            error=summary['error'],
        )
        self.lbl_stats.setText(stats_text)

        has_errors = summary['error'] > 0
        self.pack_validated.emit(not has_errors)
        self.progress.setVisible(False)

    def _on_validation_error(self, message: str):
        """Ошибка выполнения валидации (вызывается в UI-потоке)."""
        self._validating = False
        self.btn_validate.setEnabled(True)
        self.progress.setVisible(False)
        item = QListWidgetItem(f"❌ {message}")
        item.setForeground(QColor("#ff6b6b"))
        self.results_list.addItem(item)
        self.lbl_stats.setText(tr("val.stats_default"))

    def _format_result(self, result) -> str:
        """Форматирование строки результата"""
        icon = {
            ValidationLevel.ERROR: "❌",
            ValidationLevel.WARNING: "⚠️",
            ValidationLevel.SUCCESS: "✅",
            ValidationLevel.INFO: "ℹ️"
        }.get(result.level, "•")
        
        path_info = f" [{result.path}]" if result.path else ""
        return f"{icon} {result.message}{path_info}"

    def clear_results(self):
        """Очистка результатов"""
        self.results_list.clear()
        self.lbl_stats.setText(tr("val.stats_default"))
        self.btn_validate.setEnabled(False)