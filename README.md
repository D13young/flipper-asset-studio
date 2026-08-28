# 🎨 Flipper Asset Studio

**Flipper Asset Studio** — это мощное кроссплатформенное приложение для создания, редактирования и валидации asset pack'ов (наборов графики) для **Flipper Zero** с прошивкой **Momentum Firmware**.

---

## ⬇️ Скачать готовые сборки

> Готовые исполняемые файлы публикуются в разделе **[Releases](https://github.com/D13young/flipper-asset-studio/releases)** репозитория:

| Платформа | Исполняемый файл |
|-----------|------------------|
| 🪟 Windows | [`FlipperAssetStudio_Windows_x86_64.exe`](https://github.com/D13young/flipper-asset-studio/releases) |
| 🍎 macOS   | [`FlipperAssetStudio_macOS_x86_64.app.zip`](https://github.com/D13young/flipper-asset-studio/releases) |
| 🐧 Linux   | [`FlipperAssetStudio_Linux_x86_64`](https://github.com/D13young/flipper-asset-studio/releases) |

> Исполняемый файл собирается как **one-file**: иконка и все ресурсы упакованы внутри.
> Сборки создаются автоматически через **GitHub Actions** при каждом теге `v*` —
> см. [release.yml](.github/workflows/release.yml).
> macOS-сборка из CI — Intel (x86_64), на Apple Silicon работает через Rosetta 2;
> нативный arm64 можно собрать локально по инструкции
> [Сборка исполняемого файла](#-сборка-исполняемого-файла).

---

## 🌟 Возможности

### 🎬 Редактор анимаций
- Создание кастомных анимаций для дельфина
- Поддержка до 30 уровней и всех диапазонов butthurt
- Живой предпросмотр с настраиваемым FPS
- Автоматическая генерация `meta.txt` и `manifest.txt`

### 📱 Редактор иконок Passport
- Создание статических иконок
- Поддержка всех стандартных размеров (46×49 и 128×64)

### 🖼️ Обработка изображений
- Конвертация PNG → 1-битный формат Flipper
- Алгоритм дизеринга Floyd-Steinberg для сохранения детализации
- Автоматический ресайз и центрирование
- Пакетная обработка кадров

### 📦 Экспорт и сжатие
- Экспорт в форматы `.bm` (raw) и `.bmx` (сжатый Heatshrink)
- Автоматическая структура папок для Momentum

### 🔍 Валидатор
- Проверка структуры asset pack
- Валидация meta-файлов
- Проверка размеров и последовательности кадров
- Цветовая индикация ошибок и предупреждений

### 🖱️ Drag-and-Drop
- Перетаскивание PNG файлов прямо в окно программы
- Мульти-импорт для быстрого создания анимаций

---

## 📋 Требования

- **Python 3.10** или выше
- **ОС**: Windows 10/11, macOS 10.15+, Linux (Ubuntu 20.04+)
- **RAM**: минимум 512 MB
- **Место на диске**: 50 MB

---

## 🛠️ Стек технологий

- **Язык**: Python 3.10+
- **GUI-фреймворк**: PyQt6 (Qt6)
- **Обработка изображений**: Pillow (PIL), NumPy
- **Сжатие**: heatshrink2 (формат `.bmx`, Heatshrink)
- **Сборка**: PyInstaller (`FlipperAssetStudio.spec`)
- **Тестирование**: unittest (stdlib) + pytest
- **Интернационализация**: собственная i18n-система (RU / EN)

---

## 🚀 Установка

### 1. Клонируйте репозиторий
```bash
git clone https://github.com/D13young/flipper-asset-studio.git
cd flipper-asset-studio
```

### 2. Создайте виртуальное окружение (рекомендуется)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Установите зависимости
```bash
pip install -r requirements.txt
```

### 4. Запустите приложение
```bash
python main.py
```

---

## 📖 Быстрый старт

### Создание анимации дельфина

1. **Запустите приложение:**
   ```bash
   python main.py
   ```

2. **Перейдите на вкладку "🎞️ Animation"**

3. **Добавьте кадры:**
   - Нажмите **"➕ Add Frames"**
   - Выберите PNG файлы (рекомендуется 128×64 пикселя)
   - Или перетащите файлы прямо в окно

4. **Настройте параметры:**
   - **Frame Rate**: скорость анимации (FPS)
   - **Duration**: длительность цикла (мс)
   - **Animation Name**: имя анимации
   - **Butthurt/Level**: диапазоны отображения
   - **Weight**: вероятность появления

5. **Проверьте превью** — анимация воспроизводится автоматически

6. **Экспортируйте:**
   - Нажмите **"💾 Export Pack"**
   - Выберите папку
   - Выберите формат (рекомендуется `.bmx`)
   - Готово!

### Создание иконки приложения

1. **Перейдите на вкладку "📱 Icons"**

2. **Укажите параметры Passport file**

3. **Добавьте кадр**

4. **Нажмите "Export"**

5. **Скопируйте результат** на SD-карту в папку `asset_packs/`

---

## 🏗️ Структура проекта

```
flipper-asset-studio/
├── main.py                     # Точка входа в приложение (GUI)
├── FlipperAssetStudio.spec     # Конфигурация сборки PyInstaller
├── requirements.txt            # Зависимости для запуска
├── requirements-dev.txt        # Зависимости для разработки и тестов
├── README.md                   # Документация
├── .gitignore
│
├── core/                       # Логика: обработка изображений/экспорт/валидация
│   ├── __init__.py
│   ├── animation_manager.py    # Управление кадрами анимации и генерация meta/manifest
│   ├── bm_bmx_decoder.py       # Декодер/утилиты для .bm/.bmx
│   ├── exporter.py             # Экспорт анимаций и упаковка meta/manifest
│   ├── icon_builder.py         # Экспорт иконок (статические и анимированные)
│   ├── image_processor.py      # PNG -> 1-bit, дизеринг, ресайз/центрирование
│   └── validator.py            # Проверка структуры asset pack
│
├── ui/                         # UI (PyQt6)
│   ├── __init__.py
│   ├── main_window.py          # Главное окно
│   ├── styles.py               # Стили и оформление интерфейса
│   ├── background.py           # Фоновые декоративные элементы
│   ├── i18n.py                 # Интернационализация (RU / EN)
│   ├── resources.py            # Управление ресурсами (иконки/логотип в рантайме)
│   ├── animation_timeline.py   # Таймлайн/управление кадрами
│   ├── icon_editor.py          # Редактор иконок
│   ├── gif_crop_editor.py      # GIF → PNG (кадрирование анимации)
│   ├── jpg_crop_editor.py      # Редактор кадрирования (jpg)
│   ├── validator_widget.py     # Виджет результатов валидации
│   ├── drag_drop_widget.py     # Drag-and-Drop обработка
│   └── create_editor.py        # Редактор/страницы создания
│
├── scripts/
│   ├── asset_packer.py         # Утилита упаковки/создания asset pack
│   ├── build.sh                # Сборка исполняемого файла (macOS/Linux)
│   └── build_windows.bat       # Сборка исполняемого файла (Windows)
│
├── assets/                     # Ресурсы приложения
│   ├── icons/                  # SVG-иконки интерфейса
│   └── logo/                   # Логотип (png/ico/icns)
│
└── tests/                      # Автотесты (unittest)
    ├── __init__.py
    ├── test_animation_manager.py
    ├── test_background.py
    ├── test_create_editor.py
    ├── test_exporter.py
    ├── test_gif_crop_editor.py
    ├── test_i18n.py
    ├── test_icon_builder.py
    ├── test_main_window.py
    ├── test_preview_render.py
    ├── test_roundtrip.py
    ├── test_validator.py
    └── smoke_create_editor.py

```

---

## 📚 Форматы файлов


### Поддерживаемые входные форматы
- **PNG** (рекомендуется) — любой размер, цветность, прозрачность

### Генерируемые выходные форматы
- **.bm** — raw бинарный формат Flipper (без сжатия)
- **.bmx** — сжатый формат с заголовком Heatshrink
- **meta.txt** — текстовый файл параметров анимации
- **manifest.txt** — файл манифеста для анимаций дельфина
- **meta** (бинарный) — 6-байтовый файл для иконок

### Структура экспортируемого asset pack

Формат соответствует проверкам в `core/validator.py`.

```
MyAssetPack/
├── Anims/
│   ├── manifest.txt
│   └── MyAnimation/
│       ├── meta.txt
│       ├── frame_0.bm
│       ├── frame_1.bm
│       └── frame_3.bm
│
└── Icons/
    └── Passport/
        ├── passport_bad_46x49.bmx
        ├── passport_happy_46x49.bmx
        └── passport_okay_46x49.bmx

```


---

## 🛠️ Разработка

### Сборка исполняемого файла

Сборка создаёт **один автономный исполняемый файл** (без дополнительных папок):
логотип и все ресурсы упаковываются внутрь бинарника, иконка `.ico`/`.icns`
встраивается в сам исполняемый файл, а в окне/панели задач логотип
отображается в рантайме.

Файлы логотипа: `assets/logo/fast_logo.png` (рантайм),
`assets/logo/fast_logo.ico` (Windows), `assets/logo/fast_logo.icns` (macOS).

**Автоматически (рекомендуется):**

- **Windows:** запустите `scripts\build_windows.bat`
  → результат `dist\FlipperAssetStudio.exe`
- **macOS / Linux:** запустите `./scripts/build.sh`
  → macOS: `dist/FlipperAssetStudio.app`; Linux: `dist/FlipperAssetStudio`

**Вручную:**

```bash
pip install pyinstaller
pyinstaller --clean --noconfirm FlipperAssetStudio.spec
```

или напрямую от CLI:

```bash
# Windows
pyinstaller --onefile --windowed --name "FlipperAssetStudio" ^
  --icon=assets/logo/fast_logo.ico --add-data "assets;assets" main.py
```

```bash
# macOS
pyinstaller --onefile --windowed --name "FlipperAssetStudio" \
  --icon=assets/logo/fast_logo.icns --add-data "assets:assets" main.py
```

```bash
# Linux
pyinstaller --onefile --windowed --name "FlipperAssetStudio" \
  --add-data "assets:assets" main.py
```

### ⚠️ macOS: приложение «не открывается» (Gatekeeper)

Сборки не подписаны Developer ID и не нотаризованы, поэтому macOS может
блокировать запуск скачанного из интернета `.app`. Решения:

- **Первый запуск через контекстное меню:** кликните по приложению правой
  кнопкой → **Открыть** → **Открыть** в появившемся диалоге (делается один раз).
- **Через терминал** (убирает флаг карантина):
  ```bash
  xattr -dr com.apple.quarantine /Applications/FlipperAssetStudio.app
  ```
- Если появляется сообщение «повреждён и не может быть открыт» — скачайте
  [последний релиз](https://github.com/D13young/flipper-asset-studio/releases)
  заново (в ранних сборках у бинарника был снят бит выполнения).

---

## 🤝 Вклад в проект

Приветствуются pull requests! Для добавления новых функций:

1. **Fork** репозиторий
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Закоммитьте изменения (`git commit -m 'Add some AmazingFeature'`)
4. Отправьте в ветку (`git push origin feature/AmazingFeature`)
5. Откройте **Pull Request**

### Guidelines
- Используйте **PEP 8** для форматирования кода
- Добавляйте **type hints** где это возможно
- Пишите **docstrings** для публичных методов
- Тестируйте на **Windows и Linux**

---

## 🔗 Полезные ссылки

- [Официальная документация Flipper](https://developer.flipper.net/)
- [Momentum Firmware Wiki](https://momentum-fw.dev/wiki/Assets)
- [Flipper Devices](https://github.com/flipperdevices)

---

**Made with ❤️ for the Flipper Zero Community**