<p align="center">
  <img src="Icon.png" width="200">
</p>

<h1 align="center">🐾 Pet Reminder v10.0</h1>

<p align="center">
Desktop-питомец с системой умных напоминаний<br>
Лёгкий • Ненавязчивый • Всегда рядом
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-10.0-blue">
  <img src="https://img.shields.io/badge/python-3.14+-yellow">
  <img src="https://img.shields.io/badge/platform-Windows-lightgrey">
  <img src="https://img.shields.io/badge/status-stable-brightgreen">
</p>

---

## 🐶 О проекте

**Pet Reminder** — это desktop-приложение с анимированным питомцем,
который живёт на рабочем столе и напоминает о важных датах.

Приложение работает в системном трее и сохраняет данные локально в `%APPDATA%`.

## ✨ Возможности

### 🐾 Анимированный питомец
- Idle анимация
- Click анимация
- Sleep режим при бездействии
- Перетаскивание по экрану
- Поверх всех окон
- Работа через системный трей

### 🎂 Дни рождения
- Добавление и удаление записей
- Сортировка по ближайшей дате
- Уведомления за 3 дня
- Уведомления за 7 дней
- Автоматический подсчёт возраста
- Защита от повторных уведомлений в течение дня

### 🗓 События
- Название события
- Дата и время
- Напоминание за N дней
- Сортировка по ближайшему событию
- Проверка событий при запуске приложения

### 🔔 Уведомления
- Toast-окна в правом нижнем углу
- Раздельный стиль для ДР и событий
- Автоматическое закрытие

---

## 🖥 Tray-меню

```
🐾 Показать зверька
📥 Скрыть в трей
-----------------
🎂 Дни рождения
🔔 Показать ближайший ДР
🗓 События
-----------------
Версия v10.0
❌ Выход
```

---

## 💾 Хранение данных

Данные сохраняются в:

```
%APPDATA%/PetReminder
```

Файлы:
- birthdays.json  
- birthday_notified.json  
- events.json  
- events_notified.json  
- calendar_state.json  
- settings.json

---

## 🛠 Технологии

- Python
- PyQt5
- JSON
- PyInstaller

---

## 🚀 Запуск из исходников

Проект запускается напрямую из файла `pet.py`.

### 📁 Структура проекта должна быть такой:

```
pet-reminder/
│
├── pet.py
├── calendar_widget.py
├── event_window.py
├── events_manager.py
├── license.py
├── icon.ico
├── Icon.png
├── version.txt
│
├── idle_clean/
├── click_clean/
├── sleeping_clean/
└── calendar_assets/
```

⚠️ Файлы `icon.ico` и `Icon.png` должны лежать рядом с `pet.py`.

---

### 1️⃣ Склонируйте репозиторий

```bash
git clone https://github.com/kaiCATs/pet-reminder.git
cd pet-reminder
```

---

### 2️⃣ Проверте Python (3.14+)

```bash
python --version
```

Если Python не установлен — скачайте его с https://www.python.org/

---

### 3️⃣ Установите зависимость

```bash
pip install PyQt5
```

Если `pip` не срабатывает:

```bash
python -m pip install PyQt5
```

---

### 4️⃣ Запустите приложение

```bash
python pet.py
```

---

## ❗ Важно

- Запускать нужно **из корневой папки**, где лежит `pet.py`.
- Все основные модули (`calendar_widget.py`, `event_window.py`, `events_manager.py`) должны находиться рядом с `pet.py`.
- Файлы `icon.ico` и `Icon.png` должны находиться рядом с `pet.py`.
- Папки `idle_clean`, `click_clean`, `sleeping_clean` должны быть в той же директории.
- Папка `calendar_assets` (если используется) также должна лежать рядом с проектом.
- Если запустить из другой папки — иконка, анимации или календарь могут не загрузиться.

---

## 📦 Сборка в exe

```bash
pyinstaller --noconfirm --clean --onefile --windowed ^
--icon=icon.ico ^
--version-file=version.txt ^
--add-data "idle_clean;idle_clean" ^
--add-data "click_clean;click_clean" ^
--add-data "sleeping_clean;sleeping_clean" ^
--add-data "calendar_assets;calendar_assets" ^
--add-data "Icon.png;." ^
pet.py
```

---

## ⚠ Ограничения версии

- Нет автозапуска Windows
- Нет повторяющихся событий
- Проверка событий выполняется при запуске
- exe не подписан цифровой подписью

<p align="center">
<b>Version:</b> 10.0<br>
<b>Status:</b> Stable Demo Build<br><br>
Made with ❤️ in Python
</p>
