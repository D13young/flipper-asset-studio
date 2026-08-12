# 🎨 Flipper Asset Studio

**Flipper Asset Studio** — это мощное кроссплатформенное приложение для создания, редактирования и валидации asset pack'ов (наборов графики) для **Flipper Zero** с прошивкой **Momentum Firmware**.

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

## 🚀 Установка

### 1. Клонируйте репозиторий
```bash
git clone https://github.com/yourusername/flipper_asset_studio.git
cd flipper_asset_studio
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
flipper_asset_studio/
├── main.py                     # Точка входа в приложение (GUI)
├── requirements.txt            # Зависимости Python
├── README.md                   # Документация
│
├── core/                       # Логика: обработка изображений/экспорт/валидация
│   ├── __init__.py
│   ├── animation_manager.py  # Управление кадрами анимации и генерация meta/manifest
│   ├── bm_bmx_decoder.py       # Декодер/утилиты для .bm/.bmx
│   ├── exporter.py             # Экспорт анимаций и упаковка meta/manifest
│   ├── icon_builder.py         # Экспорт иконок (статические и анимированные)
│   ├── image_processor.py      # PNG -> 1-bit, дизеринг, ресайз/центрирование
│   └── validator.py           # Проверка структуры asset pack
│
├── ui/                         # UI (Qt)
│   ├── __init__.py
│   ├── main_window.py         # Главное окно
│   ├── animation_timeline.py  # Таймлайн/управление кадрами
│   ├── icon_editor.py         # Редактор иконок
│   ├── gif_crop_editor.py     # GIF → PNG (кадрирование анимации)
│   ├── jpg_crop_editor.py     # Редактор кадрирования (jpg)
│   ├── validator_widget.py    # Виджет результатов валидации
│   ├── drag_drop_widget.py    # Drag-and-Drop обработка
│   └── create_editor.py       # Редактор/страницы создания
│
└── assets/                     # Ресурсы приложения (иконки/файлы)

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

**Windows:**
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "FlipperAssetStudio" main.py
```

**macOS:**
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "FlipperAssetStudio" --icon=assets/icon.icns main.py
```

**Linux:**
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "FlipperAssetStudio" --icon=assets/icon.png main.py
```

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