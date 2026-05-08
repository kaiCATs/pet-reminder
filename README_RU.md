<div align="center">

# 🐾 Pet Reminder v10.2

Desktop-питомец с системой умных напоминаний  
Лёгкий • Ненавязчивый • Всегда рядом

![version](https://img.shields.io/badge/version-10.2-blue) ![python](https://img.shields.io/badge/python-3.14+-yellow) ![platform](https://img.shields.io/badge/platform-Windows-lightgrey) ![status](https://img.shields.io/badge/status-stable-brightgreen)

</div>

---

## О проекте

**Pet Reminder** — desktop-приложение с анимированным питомцем, который живёт на рабочем столе и напоминает о важных датах. Работает в системном трее, хранит данные локально в `%APPDATA%\PetReminder`.

---

## Возможности

**🐾 Питомец** — анимации idle / click / sleep, перетаскивание, не выходит за границы экрана, запоминает позицию, поверх всех окон.

**💬 Чат** — правый клик по питомцу открывает текстового ассистента. Добавляй события и дни рождения голосом, узнавай что запланировано, ищи по истории.

**🗓 События** — название, дата, время, настраиваемое напоминание, повтор (каждый день / неделю / месяц / год). Редактирование двойным кликом, удаление правым кликом.

**🔔 Уведомления** — тост-попапы в правом нижнем углу, тёмные для ДР, синие для событий, закрываются через 6 с.

**🎓 Туториал** — показывается при первом запуске, можно открыть из трея. Включает диалог имени питомца с фильтром нецензурных слов.

**⚙️ Прочее** — автозапуск с Windows через реестр, смена имени питомца, переключение языка (RU / EN) — всё из трей-меню.

---

## Быстрый старт

```bash
git clone https://github.com/kaiCATs/pet-reminder.git
cd pet-reminder
pip install PyQt5
python pet.py
```

> Требуется Python 3.14+. Запускать из корневой папки проекта.

---

## Структура проекта

```
pet-reminder/
├── pet.py              # точка входа
├── animation.py        # кадры и состояние анимации
├── tray.py             # системный трей и меню
├── reminders.py        # таймеры напоминаний
├── autostart.py        # автозапуск через реестр Windows
├── locale.py           # строки RU / EN
├── storage.py          # единый app_state.json (заменяет 9 мелких файлов)
├── assistant.py        # логика чата
├── chat_window.py      # UI чата
├── event_window.py     # UI событий
├── calendar_widget.py
├── birthday_manager.py
├── tutorial.py
├── config.py
├── icon.ico
├── Icon.png
├── version.txt
├── idle_clean/
├── click_clean/
└── sleeping_clean/
```

---

## Данные

Всё состояние хранится в одном файле: `%APPDATA%\PetReminder\app_state.json`  
Список событий — в `events.json`, история чата — в `chat_history.json`.

---

## Сборка

```bash
pyinstaller --noconfirm --clean --onefile --windowed ^
  --icon=icon.ico --version-file=version.txt ^
  --add-data "idle_clean;idle_clean" ^
  --add-data "click_clean;click_clean" ^
  --add-data "sleeping_clean;sleeping_clean" ^
  --add-data "Icon.png;." ^
  pet.py
```

> Автозапуск работает только в собранном `.exe`.

---

<div align="center">

**Версия:** 10.2 · **Статус:** Stable  
Made with ❤️ in Python

</div>
