import os
import re
import struct
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

_FRAME_RE = re.compile(r"^frame_(\d+)(\.bm|\.bmx)$")

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
    
    VALID_ICON_SIZES = {
        (10, 10), (12, 12), (14, 14), (16, 16),
        (32, 32), (46, 49), (64, 64), (97, 61), (128, 64)
    }
    
    REQUIRED_DIRS = {"Anims", "Icons"}
    
    VALID_EXTENSIONS = {".bm", ".bmx", ".txt", ".meta"}

    # Локализованные сообщения (по умолчанию — русский; английские при language="en").
    MSG = {
        "ru": {
            "pack_not_exists": "Папка не существует: {path}",
            "checking_folder": "Проверка папки: {name}",
            "pack_valid": "✅ Asset pack валиден! Готов к использованию.",
            "pack_errors": "❌ Найдено ошибок: {count}. Исправьте перед использованием.",
            "missing_dirs": "Не найдены обязательные папки: {dirs}. Asset pack может быть неполным.",
            "found_dirs": "Найдены папки: {dirs}",
            "manifest_missing": "Отсутствует manifest.txt (в корне папки Anims)",
            "anims_empty": "Папка Anims пуста",
            "meta_missing": "Отсутствует meta.txt",
            "meta_bad_format": "meta.txt имеет неверный формат",
            "meta_ok": "✓ meta.txt валиден",
            "meta_read_error": "Ошибка чтения meta.txt: {err}",
            "no_frames": "Не найдены кадры (.bm/.bmx)",
            "mixed_frame_exts": "Смешаны расширения кадров (.bm и .bmx)",
            "frame_bad_name": "Файл не соответствует шаблону frame_N(.bm/.bmx): {name}",
            "frames_ok": "Найдено кадров: {count} (frame_{first} … frame_{last})",
            "frames_gap": "Нарушена нумерация кадров: есть пропуски или дубликаты индексов",
            "frame_empty": "Кадр пустой (0 байт)",
            "frame_too_big": "Кадр слишком большой: {size} байт",
            "icons_empty": "Папка Icons пуста (это нормально, если иконки не требуются)",
            "meta_size_bad": "Бинарный meta должен быть 6 байт, сейчас: {size}",
            "icon_animated_ok": "✓ Анимированная иконка (meta валиден)",
            "icon_dims": "Размер: {w}x{h}, FPS: {fps}, Кадров: {count}",
            "icon_nonstandard_size": "Нестандартный размер иконки: {w}x{h}",
            "icon_meta_read_error": "Ошибка чтения meta: {err}",
            "icon_no_files": "Не найдены файлы иконки (.bm/.bmx) и нет meta",
            "icon_static_ok": "✓ Статическая иконка: {name}",
        },
        "en": {
            "pack_not_exists": "Folder does not exist: {path}",
            "checking_folder": "Checking folder: {name}",
            "pack_valid": "✅ Asset pack is valid! Ready to use.",
            "pack_errors": "❌ Errors found: {count}. Fix them before use.",
            "missing_dirs": "Required folders not found: {dirs}. The asset pack may be incomplete.",
            "found_dirs": "Found folders: {dirs}",
            "manifest_missing": "manifest.txt is missing (in the root of the Anims folder)",
            "anims_empty": "The Anims folder is empty",
            "meta_missing": "meta.txt is missing",
            "meta_bad_format": "meta.txt has an invalid format",
            "meta_ok": "✓ meta.txt is valid",
            "meta_read_error": "Error reading meta.txt: {err}",
            "no_frames": "No frames found (.bm/.bmx)",
            "mixed_frame_exts": "Mixed frame extensions (.bm and .bmx)",
            "frame_bad_name": "File name does not match frame_N(.bm/.bmx): {name}",
            "frames_ok": "Frames found: {count} (frame_{first} … frame_{last})",
            "frames_gap": "Frame numbering is broken: missing or duplicate frame indexes",
            "frame_empty": "Frame is empty (0 bytes)",
            "frame_too_big": "Frame is too large: {size} bytes",
            "icons_empty": "The Icons folder is empty (OK if no icons are required)",
            "meta_size_bad": "Binary meta must be 6 bytes, got: {size}",
            "icon_animated_ok": "✓ Animated icon (meta is valid)",
            "icon_dims": "Size: {w}x{h}, FPS: {fps}, Frames: {count}",
            "icon_nonstandard_size": "Non-standard icon size: {w}x{h}",
            "icon_meta_read_error": "Error reading meta: {err}",
            "icon_no_files": "No icon files (.bm/.bmx) and no meta found",
            "icon_static_ok": "✓ Static icon: {name}",
        },
    }

    def __init__(self, language: str = "ru"):
        self.results: List[ValidationResult] = []
        self.language = language if language in ("ru", "en") else "ru"

    def _msg(self, key: str, **kwargs) -> str:
        """Возвращает сообщение на выбранном языке (fallback — русский, затем ключ)."""
        lang_dict = self.MSG.get(self.language, self.MSG["ru"])
        text = lang_dict.get(key) or self.MSG["ru"].get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text

    def validate_pack(self, pack_path: Path) -> List[ValidationResult]:
        """Полная проверка asset pack"""
        self.results = []

        if not pack_path.exists():
            self.results.append(ValidationResult(
                ValidationLevel.ERROR,
                self._msg("pack_not_exists", path=str(pack_path)),
                str(pack_path)
            ))
            return self.results

        self.results.append(ValidationResult(
            ValidationLevel.INFO,
            self._msg("checking_folder", name=pack_path.name),
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
                self._msg("pack_valid"),
                ""
            ))
        else:
            self.results.append(ValidationResult(
                ValidationLevel.ERROR,
                self._msg("pack_errors", count=len(errors)),
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
                self._msg("missing_dirs", dirs=", ".join(sorted(self.REQUIRED_DIRS))),
                str(pack_path)
            ))
        else:
            self.results.append(ValidationResult(
                ValidationLevel.INFO,
                self._msg("found_dirs", dirs=", ".join(found_dirs)),
                ""
            ))

    def _validate_animations(self, anims_dir: Path):
        """Валидация папки Anims"""
        # Проверяем manifest.txt в корне папки Anims (а не в каждой подпапке анимации)
        manifest_file = anims_dir / "manifest.txt"
        if not manifest_file.exists():
            self.results.append(ValidationResult(
                ValidationLevel.WARNING,
                self._msg("manifest_missing"),
                str(anims_dir)
            ))

        anim_folders = [d for d in anims_dir.iterdir() if d.is_dir()]

        if not anim_folders:
            self.results.append(ValidationResult(
                ValidationLevel.WARNING,
                self._msg("anims_empty"),
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
                self._msg("meta_missing"),
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
                        self._msg("meta_bad_format"),
                        str(meta_file)
                    ))
                else:
                    self.results.append(ValidationResult(
                        ValidationLevel.SUCCESS,
                        self._msg("meta_ok"),
                        str(anim_path.name)
                    ))
            except Exception as e:
                self.results.append(ValidationResult(
                    ValidationLevel.ERROR,
                    self._msg("meta_read_error", err=str(e)),
                    str(meta_file)
                ))

        # manifest.txt в текущей модели лежит в корне папки Anims (anims_dir/manifest.txt)

        # Проверка кадров
        frame_files = sorted([f for f in files if f.suffix in [".bm", ".bmx"]])
        if not frame_files:
            self.results.append(ValidationResult(
                ValidationLevel.ERROR,
                self._msg("no_frames"),
                str(anim_path)
            ))
            return

        # Расширения кадров должны быть едиными (.bm или .bmx)
        exts = {f.suffix for f in frame_files}
        if len(exts) > 1:
            self.results.append(ValidationResult(
                ValidationLevel.WARNING,
                self._msg("mixed_frame_exts"),
                str(anim_path)
            ))

        # Разбираем числовой индекс из имени: frame_N(.bm|.bmx)
        # Сортируем по числовому индексу (natural sort), а не лексикографически,
        # чтобы frame_2 не «обгонял» frame_10.
        numbered = []
        for f in frame_files:
            m = _FRAME_RE.fullmatch(f.name)
            if m:
                numbered.append((int(m.group(1)), f))
            else:
                self.results.append(ValidationResult(
                    ValidationLevel.WARNING,
                    self._msg("frame_bad_name", name=f.name),
                    str(anim_path)
                ))

        if numbered:
            numbered.sort(key=lambda t: t[0])
            indices = [idx for idx, _ in numbered]

            # Нумерация допустима как с 0, так и с 1 — лишь бы не было пропусков/дубликатов
            consecutive = list(range(indices[0], indices[0] + len(indices)))
            if indices != consecutive:
                self.results.append(ValidationResult(
                    ValidationLevel.WARNING,
                    self._msg("frames_gap"),
                    str(anim_path)
                ))
            else:
                self.results.append(ValidationResult(
                    ValidationLevel.INFO,
                    self._msg("frames_ok", count=len(indices),
                              first=indices[0], last=indices[-1]),
                    str(anim_path.name)
                ))

            # Проверка размера первого (по индексу) кадра
            first_frame = numbered[0][1]
            try:
                frame_size = first_frame.stat().st_size
                if frame_size == 0:
                    self.results.append(ValidationResult(
                        ValidationLevel.ERROR,
                        self._msg("frame_empty"),
                        str(first_frame)
                    ))
                elif frame_size > 10240:  # > 10KB
                    self.results.append(ValidationResult(
                        ValidationLevel.WARNING,
                        self._msg("frame_too_big", size=frame_size),
                        str(first_frame)
                    ))
            except Exception:
                pass

    def _validate_icons(self, icons_dir: Path):
        """Валидация папки Icons"""
        app_folders = [d for d in icons_dir.iterdir() if d.is_dir()]

        if not app_folders:
            self.results.append(ValidationResult(
                ValidationLevel.INFO,
                self._msg("icons_empty"),
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
                        self._msg("meta_size_bad", size=meta_size),
                        str(meta_file)
                    ))
                else:
                    self.results.append(ValidationResult(
                        ValidationLevel.SUCCESS,
                        self._msg("icon_animated_ok"),
                        str(icon_path.name)
                    ))

                    # Чтение meta
                    meta_data = meta_file.read_bytes()
                    width, height, fps, count = struct.unpack("<HHBB", meta_data)

                    self.results.append(ValidationResult(
                        ValidationLevel.INFO,
                        self._msg("icon_dims", w=width, h=height, fps=fps, count=count),
                        str(icon_path.name)
                    ))

                    # Проверка размеров
                    if (width, height) not in self.VALID_ICON_SIZES:
                        self.results.append(ValidationResult(
                            ValidationLevel.WARNING,
                            self._msg("icon_nonstandard_size", w=width, h=height),
                            str(icon_path)
                        ))

            except Exception as e:
                self.results.append(ValidationResult(
                    ValidationLevel.ERROR,
                    self._msg("icon_meta_read_error", err=str(e)),
                    str(meta_file)
                ))
        else:
            # Статическая иконка
            icon_files = [f for f in files if f.suffix in [".bm", ".bmx"]]
            if not icon_files:
                self.results.append(ValidationResult(
                    ValidationLevel.WARNING,
                    self._msg("icon_no_files"),
                    str(icon_path)
                ))
            else:
                self.results.append(ValidationResult(
                    ValidationLevel.INFO,
                    self._msg("icon_static_ok", name=icon_files[0].name),
                    str(icon_path.name)
                ))

    def get_summary(self) -> Dict[str, int]:
        """Получить статистику проверок"""
        summary = {level.value: 0 for level in ValidationLevel}
        for result in self.results:
            summary[result.level.value] += 1
        return summary