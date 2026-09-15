<div align="center">

# 🐾 Pet Reminder v11.0.1

Desktop pet with a smart reminder system  
Lightweight • Unobtrusive • Always by your side

![version](https://img.shields.io/badge/version-11.0.1-blue) ![python](https://img.shields.io/badge/python-3.14+-yellow) ![platform](https://img.shields.io/badge/platform-Windows-lightgrey) ![status](https://img.shields.io/badge/status-stable-brightgreen)

</div>

---

## About

**Pet Reminder** is a desktop app with an animated pet that lives on your desktop and reminds you of important dates. Runs in the system tray, stores all data locally in `%APPDATA%\PetReminder`.

---

## Features

**🐾 Pet** — idle / click / sleep animations, draggable, stays on screen, remembers position, always on top.

**💬 Chat** — right-click the pet to open a text assistant. Add events and birthdays by typing, check what's upcoming, search history.

**🗓 Events** — name, date, time, custom remind offset, recurring (daily / weekly / monthly / yearly). Edit with double-click, delete with right-click.

**🔔 Notifications** — toast popups (bottom-right), dark for birthdays, blue for events, auto-dismiss after 6 s.

**🎓 Tutorial** — shown on first launch, reopenable from tray. Includes pet naming with profanity filter.

**⚙️ Other** — Windows autostart via registry, rename pet anytime, language switch (RU / EN) — all from the tray menu.

---

## Quick Start

```bash
git clone https://github.com/kaiCATs/pet-reminder.git
cd pet-reminder
pip install PyQt5
python pet.py
```

> Python 3.14+ required. Run from the project root folder.

### Installation and updates

Download the [latest GitHub release](https://github.com/kaiCATs/pet-reminder/releases/latest) and run `PetReminder_Setup_v11.0.1_GUI.exe`. It installs per-user, without administrator rights or a console window, into `%LOCALAPPDATA%\Programs\PetReminder`.

User data remains in `%APPDATA%\PetReminder` and is preserved during reinstall or update. The app quietly checks GitHub Releases at startup and can also be checked manually from the tray. A published update must include the GUI installer and its `.sha256` checksum file.

Windows may currently display an “Unknown publisher” warning because the build is not signed with a commercial code-signing certificate yet. Before continuing, confirm that the file came from the [official Pet Reminder release page](https://github.com/kaiCATs/pet-reminder/releases) and that its filename is correct. The adjacent SHA-256 file provides an additional integrity check.

If needed, back up `%APPDATA%\PetReminder` before a major update. Normal updates and reinstalls do not remove this folder.

---

## Project Structure

```
pet-reminder/
├── pet.py              # entry point
├── animation.py        # frame loading & animation state
├── tray.py             # system tray & menu
├── reminders.py        # event reminder timers
├── autostart.py        # Windows registry autostart
├── locale.py           # RU / EN strings
├── storage.py          # single app_state.json (replaces 9 small files)
├── assistant.py        # chat logic
├── chat_window.py      # chat UI
├── event_window.py     # events UI
├── calendar_widget.py
├── birthday_manager.py
├── tutorial.py
├── app_version.py
├── config.py
├── icon.ico
├── Icon.png
├── version.txt
├── idle_clean/
├── click_clean/
└── sleeping_clean/
```

---

## Data

All state is stored in one file: `%APPDATA%\PetReminder\app_state.json`  
Events live in `events.json`, chat history in `chat_history.json`.

---

## Build

```bash
pyinstaller --noconfirm --clean --onefile --windowed ^
  --icon=icon.ico --version-file=version.txt ^
  --add-data "idle_clean;idle_clean" ^
  --add-data "click_clean;click_clean" ^
  --add-data "sleeping_clean;sleeping_clean" ^
  --add-data "Icon.png;." ^
  pet.py
```

> Autostart only works in the compiled `.exe`.

---

<div align="center">

**Version:** 11.0.0 · **Status:** Stable  
Made with ❤️ in Python

</div>
