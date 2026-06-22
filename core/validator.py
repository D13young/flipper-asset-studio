import os
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

class ValidationLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

@dataclass
class ValidationResult:
    level: ValidationLevel
    message: str
    path: str = ""

class FlipperAssetPackValidator:
    """Валидатор структуры Asset Pack для Flipper Zero (Momentum)"""
    
    # Допустимые размеры для иконок
    VALID_ICON_SIZES = {
        (10, 10), (12, 12), (14, 14), (16, 16),
        (32, 32), (46, 49), (64, 64), (97, 61), (128, 64)
    }
    
    # Обязательные папки в asset pack
    REQUIRED_DIRS = {"Anims", "Icons"}
    
    # Расширения файлов
    VALID_EXTENSIONS = {".bm", ".bmx", ".txt", ".meta"}

    def __init__(self):
        self.results: List[ValidationResult] = []

    def validate_pack(self, pack_path: Path) -> List[ValidationResult]:
        """Полная проверка asset pack"""
        self.results = []
        
        if not pack_path.exists():
            self.results.append(ValidationResult(
                ValidationLevel.ERROR, 
                f"Папка не существует: {pack_path}",
                str(pack_path)
            ))
            return self.results

        self.results.append(ValidationResult(
            ValidationLevel.INFO, 
            f"Проверка папки: {pack_path.name}",
            str(pack_path)
        ))

        # Проверка структуры
        self._check_directory_structure(pack_path)
        
        # Проверка анимаций
        anims_dir = pack_path / "Anims"
        if anims_dir.exists():
            self._validate_animations(anims_dir)
        
        # Проверка иконок
        icons_dir = pack_path / "Icons"
        if icons_dir.exists():
            self._validate_icons(icons_dir)

        # Итоговая проверка
        errors = [r for r in self.results if r.level == ValidationLevel.ERROR]
        if not errors:
            self.results.append(ValidationResult(
                ValidationLevel.SUCCESS,
                "✅ Asset pack валиден! Готов к использованию.",
                ""
            ))
        else:
            self.results.append(ValidationResult(
                ValidationLevel.ERROR,
                f"❌ Найдено ошибок: {len(errors)}. Исправьте перед использованием.",
                ""
            ))

        return self.results

    def _check_directory_structure(self, pack_path: Path):
        """Проверка базовой структуры папок"""
        # Проверяем, есть ли хотя бы одна из требуемых папок
        found_dirs = [d for d in self.REQUIRED_DIRS if (pack_path / d).exists()]
        
        if not found_dirs:
            self.results.append(ValidationResult(
                ValidationLevel.WARNING,
                f"Не найдены обязательные папки: {self.REQUIRED_DIRS}. "
                f"Asset pack может быть неполным.",
                str(pack_path)
            ))
        else:
            self.results.append(ValidationResult(
                ValidationLevel.INFO,
                f"Найдены папки: {', '.join(found_dirs)}",
                ""
            ))

    def _validate_animations(self, anims_dir: Path):
        """Валидация папки Anims"""
        # Проверяем manifest.txt в корне папки Anims (а не в каждой подпапке анимации)
        manifest_file = anims_dir / "manifest.txt"
        if not manifest_file.exists():
            self.results.append(ValidationResult(
                ValidationLevel.WARNING,
                "Отсутствует manifest.txt (в корне папки Anims)",
                str(anims_dir)
            ))

        anim_folders = [d for d in anims_dir.iterdir() if d.is_dir()]

        if not anim_folders:
            self.results.append(ValidationResult(
                ValidationLevel.WARNING,
                "Папка Anims пуста",
                str(anims_dir)
            ))
            return

        for anim_folder in anim_folders:
            self._validate_single_animation(anim_folder)


    def _validate_single_animation(self, anim_path: Path):
        """Проверка одной анимации"""
        files = list(anim_path.iterdir())
        
        # Проверка meta.txt
        meta_file = anim_path / "meta.txt"
        if not meta_file.exists():
            self.results.append(ValidationResult(
                ValidationLevel.ERROR,
                f"Отсутствует meta.txt",
                str(anim_path)
            ))
            return
        else:
            # Проверка содержимого meta.txt
            try:
                content = meta_file.read_text(encoding="utf-8")
                if "Filetype: Flipper Animation" not in content:
                    self.results.append(ValidationResult(
                        ValidationLevel.ERROR,
                        f"meta.txt имеет неверный формат",
                        str(meta_file)
                    ))
                else:
                    self.results.append(ValidationResult(
                        ValidationLevel.SUCCESS,
                        f"✓ meta.txt валиден",
                        str(anim_path.name)
                    ))
            except Exception as e:
                self.results.append(ValidationResult(
                    ValidationLevel.ERROR,
                    f"Ошибка чтения meta.txt: {e}",
                    str(meta_file)
                ))

        # manifest.txt в текущей модели лежит в корне папки Anims (anims_dir/manifest.txt)

        # Проверка кадров
        frames = sorted([f for f in files if f.suffix in [".bm", ".bmx"]])
        if not frames:
            self.results.append(ValidationResult(
                ValidationLevel.ERROR,
                f"Не найдены кадры (.bm/.bmx)",
                str(anim_path)
            ))
        else:
            # Проверка последовательности имен
            expected_names = [f"frame_{i}{frames[0].suffix}" for i in range(len(frames))]
            actual_names = [f.name for f in frames]
            
            if actual_names != expected_names:
                self.results.append(ValidationResult(
                    ValidationLevel.WARNING,
                    f"Нарушена нумерация кадров. Ожидается: {expected_names}, найдено: {actual_names}",
                    str(anim_path)
                ))
            else:
                self.results.append(ValidationResult(
                    ValidationLevel.INFO,
                    f"Найдено кадров: {len(frames)}",
                    str(anim_path.name)
                ))

            # Проверка размера первого кадра
            try:
                frame_size = frames[0].stat().st_size
                if frame_size == 0:
                    self.results.append(ValidationResult(
                        ValidationLevel.ERROR,
                        f"Кадр пустой (0 байт)",
                        str(frames[0])
                    ))
                elif frame_size > 10240:  # > 10KB
                    self.results.append(ValidationResult(
                        ValidationLevel.WARNING,
                        f"Кадр слишком большой: {frame_size} байт",
                        str(frames[0])
                    ))
            except Exception:
                pass

    def _validate_icons(self, icons_dir: Path):
        """Валидация папки Icons"""
        app_folders = [d for d in icons_dir.iterdir() if d.is_dir()]
        
        if not app_folders:
            self.results.append(ValidationResult(
                ValidationLevel.INFO,
                "Папка Icons пуста (это нормально, если иконки не требуются)",
                str(icons_dir)
            ))
            return

        for app_folder in app_folders:
            self._validate_icon_folder(app_folder)

    def _validate_icon_folder(self, icon_path: Path):
        """Проверка папки с иконкой приложения"""
        files = list(icon_path.iterdir())
        
        # Проверяем, это анимированная иконка (есть meta) или статическая
        meta_file = icon_path / "meta"
        is_animated = meta_file.exists()
        
        if is_animated:
            # Проверка бинарного meta
            try:
                meta_size = meta_file.stat().st_size
                if meta_size != 6:  # HHBB = 2+2+1+1 = 6 байт
                    self.results.append(ValidationResult(
                        ValidationLevel.ERROR,
                        f"Бинарный meta должен быть 6 байт, сейчас: {meta_size}",
                        str(meta_file)
                    ))
                else:
                    self.results.append(ValidationResult(
                        ValidationLevel.SUCCESS,
                        f"✓ Анимированная иконка (meta валиден)",
                        str(icon_path.name)
                    ))
                    
                    # Чтение meta
                    import struct
                    meta_data = meta_file.read_bytes()
                    width, height, fps, count = struct.unpack("<HHBB", meta_data)
                    
                    self.results.append(ValidationResult(
                        ValidationLevel.INFO,
                        f"Размер: {width}x{height}, FPS: {fps}, Кадров: {count}",
                        str(icon_path.name)
                    ))
                    
                    # Проверка размеров
                    if (width, height) not in self.VALID_ICON_SIZES:
                        self.results.append(ValidationResult(
                            ValidationLevel.WARNING,
                            f"Нестандартный размер иконки: {width}x{height}",
                            str(icon_path)
                        ))
                        
            except Exception as e:
                self.results.append(ValidationResult(
                    ValidationLevel.ERROR,
                    f"Ошибка чтения meta: {e}",
                    str(meta_file)
                ))
        else:
            # Статическая иконка
            icon_files = [f for f in files if f.suffix in [".bm", ".bmx"]]
            if not icon_files:
                self.results.append(ValidationResult(
                    ValidationLevel.WARNING,
                    f"Не найдены файлы иконки (.bm/.bmx) и нет meta",
                    str(icon_path)
                ))
            else:
                self.results.append(ValidationResult(
                    ValidationLevel.INFO,
                    f"✓ Статическая иконка: {icon_files[0].name}",
                    str(icon_path.name)
                ))

    def get_summary(self) -> Dict[str, int]:
        """Получить статистику проверок"""
        summary = {level.value: 0 for level in ValidationLevel}
        for result in self.results:
            summary[result.level.value] += 1
        return summary