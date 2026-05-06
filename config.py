# ================================================================
# ОБЩИЕ ПУТИ И НАСТРОЙКИ ПРИЛОЖЕНИЯ
# ================================================================
import os
import json
from pathlib import Path

app_data_dir = Path(os.getenv("APPDATA")) / "PetReminder"
app_data_dir.mkdir(parents=True, exist_ok=True)

app_dir = str(app_data_dir)

_position_file  = os.path.join(app_dir, "position.json")
_name_file      = os.path.join(app_dir, "pet_name.json")
_tutorial_file  = os.path.join(app_dir, "tutorial_done.json")
_birthdays_file = os.path.join(app_dir, "birthdays.json")
_events_file    = os.path.join(app_dir, "events.json")


# ================================================================
# ПЕРВЫЙ ЗАПУСК
# Считается первым если отсутствуют все три файла одновременно:
# position.json, birthdays.json, events.json
# ================================================================
def is_first_launch():
    """
    Возвращает True если это первый запуск приложения.
    Определяется по отсутствию всех трёх файлов одновременно.
    """
    return (
        not os.path.exists(_position_file) and
        not os.path.exists(_birthdays_file) and
        not os.path.exists(_events_file)
    )


# ================================================================
# ТУТОРИАЛ
# ================================================================
def is_tutorial_done():
    """Возвращает True если туториал уже был пройден или пропущен."""
    return os.path.exists(_tutorial_file)


def mark_tutorial_done():
    """Помечает туториал как завершённый."""
    try:
        with open(_tutorial_file, "w") as f:
            json.dump({"done": True}, f)
    except Exception as e:
        print(f"[config] mark_tutorial_done: {e}")


# ================================================================
# ИМЯ ПИТОМЦА
# Сохраняется отдельно — используется для голосового вызова.
# ================================================================
def load_pet_name():
    """Загружает имя питомца. При ошибке или отсутствии возвращает None."""
    try:
        with open(_name_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("name")
    except Exception:
        return None


def save_pet_name(name):
    """Сохраняет имя питомца."""
    try:
        with open(_name_file, "w", encoding="utf-8") as f:
            json.dump({"name": name}, f, ensure_ascii=False)
    except Exception as e:
        print(f"[config] save_pet_name: {e}")


def has_pet_name():
    """Возвращает True если имя питомца уже задано."""
    return load_pet_name() is not None


# ================================================================
# ПОЗИЦИЯ ПИТОМЦА
# ================================================================
def load_position():
    """Загружает последнюю позицию питомца. При ошибке возвращает None, None."""
    try:
        with open(_position_file, "r") as f:
            data = json.load(f)
            return data.get("x"), data.get("y")
    except Exception:
        return None, None


def save_position(x, y):
    """Сохраняет текущую позицию питомца."""
    try:
        with open(_position_file, "w") as f:
            json.dump({"x": x, "y": y}, f)
    except Exception as e:
        print(f"[config] save_position: {e}")
