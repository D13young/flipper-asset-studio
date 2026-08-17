# ui/i18n.py
# ─────────────────────────────────────────────────────────────
#  Русский / English
# ─────────────────────────────────────────────────────────────
from __future__ import annotations

LANG_RU = "ru"
LANG_EN = "en"

LANGUAGES = {
    LANG_RU: "Русский",
    LANG_EN: "English",
}

# Порядок языков для меню переключения
LANGUAGE_ORDER = [LANG_RU, LANG_EN]

# Каталог переводов. Ключи — имена строк, значения — слова по языкам.
STRINGS: dict[str, dict[str, str]] = {
    LANG_RU: {
        # ── Главное окно ──
        "nav.create": "Создание",
        "nav.single_image": "Одиночное изображение",
        "nav.jpg_crop": "JPG Crop → PNG",
        "nav.gif_to_png": "GIF → PNG",
        "nav.animation_builder": "Конструктор анимаций",
        "nav.meta_preview": "Предпросмотр Meta",
        "nav.icons": "Иконки",
        "nav.validator": "Валидатор",
        "nav.bm_bmx_preview": "Превью BM/BMX",

        "tab.create": "Создание",
        "tab.single": "Одиночное",
        "tab.jpg_crop": "JPG Crop",
        "tab.gif_to_png": "GIF → PNG",
        "tab.animation": "Анимация",
        "tab.meta": "Meta",
        "tab.icons": "Иконки",
        "tab.validator": "Валидатор",
        "tab.bm_bmx": "BM/BMX",

        "tb.import": "Импорт",
        "tb.export": "Экспорт",
        "tb.exit": "Выход",
        "tb.theme": "Тема",
        "tb.language": "Язык",
        "tb.theme_tip": "Сменить тему оформления",
        "tb.language_tip": "Сменить язык интерфейса",

        "app.title": "Flipper Asset Studio",

        "single.drag_title": "Перетащите PNG или нажмите «Импорт»",
        "single.preview_hint": "Импортируйте PNG",
        "single.dither": "Дизеринг Флойда-Стейнберга",

        "anim.preview_hint": "Добавьте кадры для предпросмотра",
        "anim.preview_hint_short": "Добавьте кадры",

        "bm.drop_title": "Перетащите .bm / .bmx для превью",
        "bm.preview_hint": "Загружайте .bm / .bmx",

        "status.ready": "Готово. Выберите PNG или добавьте кадры анимации.",
        "status.dnd_files": "📄 Перетащено файлов: {count}",
        "status.ok_128x64": "✅ 128x64 | {size} Б",
        "status.error": "❌ Ошибка: {err}",
        "status.loaded": "📄 {name}",
        "status.bm_ok": "OK {name} | {w}x{h}",
        "status.bm_err": "Ошибка {name}: {err}",
        "bm.error_label": "Ошибка: {err}",

        "dlg.add_to_animation": "Добавить в анимацию?",
        "dlg.multi_files": "Обнаружено {count} файлов. Добавить их в анимацию?",
        "dlg.export_folder": "Выберите папку экспорта",
        "dlg.select_png": "Выбрать PNG",
        "dlg.done": "Готово",
        "dlg.error": "Ошибка",

        "msg.anim_exported": "Анимация экспортирована!",
        "msg.create_exported": "Создание: экспортировано {count} PNG кадр(ов) в: {folder}",
        "msg.no_icon_frames": "Нет кадров иконки",
        "msg.icon_exported": "Иконка экспортирована: {name}.bmx",
        "msg.select_tab": "Выберите вкладку с контентом для экспорта",
        "msg.no_anim_frames": "Нет кадров анимации",
        "msg.no_create_frames": "Нет кадров для экспорта",
        "msg.ok": "Готово",

        # ── Validator ──
        "val.btn_select": "📁 Выбрать Asset Pack",
        "val.btn_validate": "✅ Проверить",
        "val.path_default": "Папка не выбрана",
        "val.group_results": "📋 Результаты проверки",
        "val.stats_default": "Статистика: -",
        "val.stats": "📊 Всего: {total} | ✅ Успешно: {success} | ℹ️ Инфо: {info} | ⚠️ Предупреждения: {warning} | ❌ Ошибки: {error}",
        "val.select_folder": "Выберите папку Asset Pack",

        # ── Animation Timeline ──
        "anim.drag_title": "📥 Перетащите PNG кадры сюда",
        "anim.btn_add": "➕ Добавить кадры",
        "anim.btn_up": "⬆️ Вверх",
        "anim.btn_down": "⬇️ Вниз",
        "anim.btn_remove": "❌ Удалить",
        "anim.btn_clear": "🧼 Очистить",
        "anim.group_params": "⚙️ Параметры анимации",
        "anim.lbl_dither": "Уровень дизеринга:",
        "anim.lbl_fps": "Частота кадров (FPS):",
        "anim.lbl_duration": "Длительность (мс):",
        "anim.lbl_name": "Имя анимации:",
        "anim.lbl_bh_min": "Мин. butthurt:",
        "anim.lbl_bh_max": "Макс. butthurt:",
        "anim.lbl_lv_min": "Мин. уровень:",
        "anim.lbl_lv_max": "Макс. уровень:",
        "anim.lbl_weight": "Вес:",
        "anim.frame_item": "Кадр {index}",
        "anim.select_frames": "Выбрать кадры анимации",

        # ── Icon Editor ──
        "icon.group_settings": "Настройки",
        "icon.tip_app_name": "Название папки приложения (например: RFID, NFC, SubGhz)",
        "icon.lbl_app_name": "Имя приложения:",
        "icon.lbl_passport_file": "Файл паспорта:",
        "icon.lbl_dither_level": "Уровень дизеринга:",
        "icon.drag_title": "Перетащите PNG файлы сюда",
        "icon.btn_add": "Добавить кадры",
        "icon.btn_clear": "Очистить",
        "icon.select_frames": "Выбрать кадры иконки",

        # ── Create Editor ──
        "create.group_settings": "⚙️ Настройки",
        "create.lbl_name_png": "Имя PNG:",
        "create.lbl_width": "Ширина (px):",
        "create.lbl_height": "Высота (px):",
        "create.group_canvas": "🖼️ Холст",
        "create.group_frames": "Кадры",
        "create.btn_add_frame": "➕ Добавить кадр",
        "create.btn_remove_frame": "❌ Удалить",
        "create.btn_prev": "⬅️ Назад",
        "create.btn_next": "Вперёд ➡️",
        "create.btn_clear": "🧼 Очистить",
        "create.status": "Кадры: {count} | Активный: {active}",
        "create.frame_item": "Кадр {index}",

        # ── JPG Crop Editor ──
        "jpg.drag_title": "Перетащите JPG/PNG файл сюда или нажмите «Выбрать JPG»",
        "jpg.group_controls": "📷 JPG → PNG crop",
        "jpg.btn_load": "Загрузить JPG",
        "jpg.loaded_default": "Файл не выбран",
        "jpg.loaded_error": "Файл не выбран / не удалось прочитать",
        "jpg.btn_export": "Экспортировать PNG",
        "jpg.lbl_input": "Входной файл:",
        "jpg.lbl_loaded": "Загружено:",
        "jpg.lbl_output_size": "Выходной размер:",
        "jpg.group_preview": "Превью (двигайте рамку)",
        "jpg.lbl_hint": "Рамка соответствует выбранному соотношению сторон выхода. Можно двигать/тянуть за углы.",
        "jpg.preview_hint": "Загрузите JPG для превью",
        "jpg.select_jpg": "Выбрать JPG",
        "jpg.export_dir": "Выберите папку для PNG",

        # ── GIF Crop Editor ──
        "gif.drag_title": "Перетащите GIF файл сюда или нажмите «Загрузить GIF»",
        "gif.group_controls": "🎞 GIF → PNG crop",
        "gif.btn_load": "Загрузить GIF",
        "gif.loaded_default": "Файл не выбран",
        "gif.btn_export": "Экспортировать PNG кадры",
        "gif.lbl_frames": "Кадров: —",
        "gif.lbl_frames_count": "Кадров: {count}",
        "gif.lbl_frames_label": "Кадры:",
        "gif.group_preview": "Превью (двигайте рамку — применяется ко всем кадрам)",
        "gif.lbl_frame": "Кадр:",
        "gif.lbl_hint": "Рамка соответствует выбранному соотношению сторон выхода. Можно двигать/тянуть за углы — она применяется ко всем кадрам анимации.",
        "gif.preview_hint": "Загрузите GIF для превью",
        "gif.select_gif": "Выбрать GIF",
        "gif.export_dir": "Выберите папку для PNG кадров",
        "gif.exported": "Экспортировано кадров: {count} → {dir}",
        "gif.exporting": "⏳ Экспорт GIF…",

        # ── Drag & Drop ──
        "drag.loaded": "✅ Загружено файлов: {count}",
        "drag.wrong_format_title": "Неверный формат",
        "drag.wrong_format_msg": "Принимаются только файлы: {exts}",
    },

    LANG_EN: {
        # ── Main Window ──
        "nav.create": "Create",
        "nav.single_image": "Single Image",
        "nav.jpg_crop": "JPG Crop → PNG",
        "nav.gif_to_png": "GIF to PNG",
        "nav.animation_builder": "Animation Builder",
        "nav.meta_preview": "Meta Preview",
        "nav.icons": "Icons",
        "nav.validator": "Validator",
        "nav.bm_bmx_preview": "BM/BMX Preview",

        "tab.create": "Create",
        "tab.single": "Single",
        "tab.jpg_crop": "JPG Crop",
        "tab.gif_to_png": "GIF to PNG",
        "tab.animation": "Animation",
        "tab.meta": "Meta",
        "tab.icons": "Icons",
        "tab.validator": "Validator",
        "tab.bm_bmx": "BM/BMX",

        "tb.import": "Import",
        "tb.export": "Export",
        "tb.exit": "Exit",
        "tb.theme": "Theme",
        "tb.language": "Language",
        "tb.theme_tip": "Change the color theme",
        "tb.language_tip": "Change the interface language",

        "app.title": "Flipper Asset Studio",

        "single.drag_title": "Drag a PNG or click Import",
        "single.preview_hint": "Import a PNG",
        "single.dither": "Floyd-Steinberg Dithering",

        "anim.preview_hint": "Add frames for preview",
        "anim.preview_hint_short": "Add frames",

        "bm.drop_title": "Drop .bm / .bmx to preview",
        "bm.preview_hint": "Load .bm / .bmx",

        "status.ready": "Ready. Select a PNG or add animation frames.",
        "status.dnd_files": "📄 Drag&Drop: {count} file(s)",
        "status.ok_128x64": "✅ 128x64 | {size}B",
        "status.error": "❌ Error: {err}",
        "status.loaded": "📄 {name}",
        "status.bm_ok": "OK {name} | {w}x{h}",
        "status.bm_err": "Error {name}: {err}",
        "bm.error_label": "Error: {err}",

        "dlg.add_to_animation": "Add to animation?",
        "dlg.multi_files": "Found {count} files. Add them to the animation?",
        "dlg.export_folder": "Choose export folder",
        "dlg.select_png": "Select PNG",
        "dlg.done": "Done",
        "dlg.error": "Error",

        "msg.anim_exported": "Animation exported!",
        "msg.create_exported": "Create: exported {count} PNG frame(s) to: {folder}",
        "msg.no_icon_frames": "No icon frames",
        "msg.icon_exported": "Icon exported: {name}.bmx",
        "msg.select_tab": "Select a tab with content to export",
        "msg.no_anim_frames": "No animation frames",
        "msg.no_create_frames": "No frames to export",
        "msg.ok": "Done",

        # ── Validator ──
        "val.btn_select": "📁 Select Asset Pack",
        "val.btn_validate": "✅ Validate",
        "val.path_default": "No folder selected",
        "val.group_results": "📋 Validation results",
        "val.stats_default": "Statistics: -",
        "val.stats": "📊 Total: {total} | ✅ Success: {success} | ℹ️ Info: {info} | ⚠️ Warnings: {warning} | ❌ Errors: {error}",
        "val.select_folder": "Choose Asset Pack folder",

        # ── Animation Timeline ──
        "anim.drag_title": "📥 Drag PNG frames here",
        "anim.btn_add": "➕ Add Frames",
        "anim.btn_up": "⬆️ Move Up",
        "anim.btn_down": "⬇️ Move Down",
        "anim.btn_remove": "❌ Remove",
        "anim.btn_clear": "🧼 Clear",
        "anim.group_params": "⚙️ Animation Parameters",
        "anim.lbl_dither": "Dither Level:",
        "anim.lbl_fps": "Frame Rate (FPS):",
        "anim.lbl_duration": "Duration (ms):",
        "anim.lbl_name": "Animation Name:",
        "anim.lbl_bh_min": "Min Butthurt:",
        "anim.lbl_bh_max": "Max Butthurt:",
        "anim.lbl_lv_min": "Min Level:",
        "anim.lbl_lv_max": "Max Level:",
        "anim.lbl_weight": "Weight:",
        "anim.frame_item": "Frame {index}",
        "anim.select_frames": "Select Animation Frames",

        # ── Icon Editor ──
        "icon.group_settings": "Settings",
        "icon.tip_app_name": "Application folder name (e.g. RFID, NFC, SubGhz)",
        "icon.lbl_app_name": "App Name:",
        "icon.lbl_passport_file": "Passport file:",
        "icon.lbl_dither_level": "Dither level:",
        "icon.drag_title": "Drag PNG files here",
        "icon.btn_add": "Add Frames",
        "icon.btn_clear": "Clear",
        "icon.select_frames": "Add Icon Frames",

        # ── Create Editor ──
        "create.group_settings": "⚙️ Settings",
        "create.lbl_name_png": "Name PNG:",
        "create.lbl_width": "Width (px):",
        "create.lbl_height": "Height (px):",
        "create.group_canvas": "🖼️ Canvas",
        "create.group_frames": "Frames",
        "create.btn_add_frame": "➕ Add Frame",
        "create.btn_remove_frame": "❌ Remove",
        "create.btn_prev": "⬅️ Prev",
        "create.btn_next": "Next ➡️",
        "create.btn_clear": "🧼 Clear",
        "create.status": "Frames: {count} | Active: {active}",
        "create.frame_item": "Frame {index}",

        # ── JPG Crop Editor ──
        "jpg.drag_title": "Drag a JPG/PNG file here or click Select JPG",
        "jpg.group_controls": "📷 JPG → PNG crop",
        "jpg.btn_load": "Load JPG",
        "jpg.loaded_default": "No file selected",
        "jpg.loaded_error": "No file selected / could not be read",
        "jpg.btn_export": "Export PNG",
        "jpg.lbl_input": "Input:",
        "jpg.lbl_loaded": "Loaded:",
        "jpg.lbl_output_size": "Output size:",
        "jpg.group_preview": "Preview (drag frame)",
        "jpg.lbl_hint": "The frame matches the selected output aspect ratio. You can move/drag it by the corners.",
        "jpg.preview_hint": "Load a JPG for preview",
        "jpg.select_jpg": "Select JPG",
        "jpg.export_dir": "Choose folder for PNG",

        # ── GIF Crop Editor ──
        "gif.drag_title": "Drag a GIF file here or click Load GIF",
        "gif.group_controls": "🎞 GIF → PNG crop",
        "gif.btn_load": "Load GIF",
        "gif.loaded_default": "No file selected",
        "gif.btn_export": "Export PNG frames",
        "gif.lbl_frames": "Frames: —",
        "gif.lbl_frames_count": "Frames: {count}",
        "gif.lbl_frames_label": "Frames:",
        "gif.group_preview": "Preview (drag frame — applies to all frames)",
        "gif.lbl_frame": "Frame:",
        "gif.lbl_hint": "The frame matches the selected output aspect ratio. You can move/drag it by the corners — it applies to all animation frames.",
        "gif.preview_hint": "Load a GIF for preview",
        "gif.select_gif": "Select GIF",
        "gif.export_dir": "Choose folder for PNG frames",
        "gif.exported": "Exported frames: {count} → {dir}",
        "gif.exporting": "⏳ Exporting GIF…",

        # ── Drag & Drop ──
        "drag.loaded": "✅ Loaded files: {count}",
        "drag.wrong_format_title": "Invalid format",
        "drag.wrong_format_msg": "Only these files are accepted: {exts}",
    },
}


_current_lang = LANG_RU


def set_language(lang: str) -> None:
    """Устанавливает текущий язык интерфейса."""
    global _current_lang
    _current_lang = lang if lang in LANGUAGES else LANG_RU


def get_language() -> str:
    return _current_lang


def tr(key: str) -> str:
    """Возвращает строку на текущем языке (fallback — русский, затем ключ)."""
    lang_dict = STRINGS.get(_current_lang, STRINGS[LANG_RU])
    if key in lang_dict:
        return lang_dict[key]
    return STRINGS[LANG_RU].get(key, key)


def trf(key: str, **kwargs) -> str:
    """Возвращает строку с подстановкой параметров (.format)."""
    text = tr(key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text

