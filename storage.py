# ================================================================
# STORAGE
# Single source of truth for all app state.
# Replaces: position.json, pet_name.json, tutorial_done.json,
#           chat_settings.json, user_prompt.json, user_slang.json,
#           birthday_notified.json, events_notified.json,
#           chat_memory.json
#
# Remaining separate files (content is a list, can grow large):
#   events.json       — event list
#   chat_history.json — chat history
# ================================================================

import json
import os
import copy
import shutil
from datetime import datetime
from pathlib import Path

_app_data = Path(os.getenv("APPDATA")) / "PetReminder"
_app_data.mkdir(parents=True, exist_ok=True)
app_dir = str(_app_data)

STATE_FILE   = os.path.join(app_dir, "app_state.json")
EVENTS_FILE  = os.path.join(app_dir, "events.json")
HISTORY_FILE = os.path.join(app_dir, "chat_history.json")

_DEFAULTS = {
    "schema_version":      1,
    # meta
    "language":            "ru",
    "tutorial_done":       False,
    "notifications_enabled": True,
    # pet
    "pet_name":            None,
    "position":            {"x": None, "y": None},
    # autostart flag (actual state read from registry)
    # chat ui
    "font_size":           "medium",
    "window_width":        380,
    "window_height":       500,
    "event_window_theme":  "light",
    # assistant behaviour
    "prompt": {
        "tone":         "дружеский",
        "about_user":   "",
        "instructions": "",
        "ask_if_unsure": True,
    },
    # user shorthand
    "slang": {},
    # notification cache  {event_id: "YYYY-MM-DD"}
    "notified_events":    {},
    "notified_birthdays": {},
    # assistant memory
    "memory": {},
}


def load_state() -> dict:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("app_state.json must contain an object")
        # fill missing keys with defaults
        state = copy.deepcopy(_DEFAULTS)
        state.update(data)
        return state
    except Exception:
        return copy.deepcopy(_DEFAULTS)


def _atomic_write_json(path: str, data):
    """Write JSON safely so an interrupted save cannot destroy the file."""
    temp_path = f"{path}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    except Exception:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except OSError:
            pass
        raise


def save_state(state: dict):
    try:
        _atomic_write_json(STATE_FILE, state)
        return True
    except Exception as e:
        print(f"[storage] save_state: {e}")
        return False


# ----------------------------------------------------------------
# Convenience helpers — each touches only its own slice of state
# ----------------------------------------------------------------

def get(key, default=None):
    return load_state().get(key, default)


def set_key(key, value):
    s = load_state()
    s[key] = value
    save_state(s)


def notifications_enabled() -> bool:
    return bool(get("notifications_enabled", True))


def set_notifications_enabled(enabled: bool):
    set_key("notifications_enabled", bool(enabled))


def create_backup() -> str:
    """Create a timestamped local backup of the user's app data."""
    source_files = (STATE_FILE, EVENTS_FILE, HISTORY_FILE)
    existing = [path for path in source_files if os.path.exists(path)]
    if not existing:
        raise FileNotFoundError("No Pet Reminder data to back up")

    backup_dir = Path(app_dir) / "backups" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    for path in existing:
        shutil.copy2(path, backup_dir / os.path.basename(path))
    return str(backup_dir)


# --- Position ---
def load_position():
    pos = load_state().get("position", {})
    return pos.get("x"), pos.get("y")


def save_position(x, y):
    s = load_state()
    s["position"] = {"x": x, "y": y}
    if not save_state(s):
        return


# --- Pet name ---
def load_pet_name():
    return load_state().get("pet_name")


def save_pet_name(name):
    set_key("pet_name", name)


def has_pet_name():
    return bool(load_pet_name())


# --- Tutorial ---
def is_tutorial_done():
    return bool(load_state().get("tutorial_done", False))


def mark_tutorial_done():
    set_key("tutorial_done", True)


# --- Language ---
def current_language():
    return load_state().get("language", "ru")


def toggle_language():
    s = load_state()
    s["language"] = "en" if s.get("language", "ru") == "ru" else "ru"
    save_state(s)


# --- First launch ---
def is_first_launch():
    """True when neither app_state nor events exist yet."""
    return not os.path.exists(STATE_FILE) and not os.path.exists(EVENTS_FILE)


# --- Chat settings ---
def load_chat_settings():
    s = load_state()
    return {
        "font_size":          s.get("font_size", "medium"),
        "window_width":       s.get("window_width", 380),
        "window_height":      s.get("window_height", 500),
        "event_window_theme": s.get("event_window_theme", "light"),
    }


def save_chat_settings(data: dict):
    s = load_state()
    for k in ("font_size", "window_width", "window_height", "event_window_theme"):
        if k in data:
            s[k] = data[k]
    save_state(s)


def load_event_window_theme():
    return load_state().get("event_window_theme", "light")


def save_event_window_theme(theme):
    set_key("event_window_theme", theme if theme in ("light", "dark") else "light")


# --- Prompt ---
def load_user_prompt():
    return load_state().get("prompt", dict(_DEFAULTS["prompt"]))


def save_user_prompt(data: dict):
    set_key("prompt", data)


# --- Slang ---
def load_slang() -> dict:
    return load_state().get("slang", {})


def save_user_slang(word: str, meaning: str):
    s = load_state()
    s.setdefault("slang", {})[word.lower()] = meaning
    save_state(s)


# --- Notification cache ---
def load_notified_events() -> dict:
    return load_state().get("notified_events", {})


def save_notified_events(data: dict):
    set_key("notified_events", data)


def load_notified_birthdays() -> dict:
    return load_state().get("notified_birthdays", {})


def save_notified_birthdays(data: dict):
    set_key("notified_birthdays", data)


# --- Memory ---
def load_memory() -> dict:
    return load_state().get("memory", {})


def save_memory(data: dict):
    set_key("memory", data)


# ----------------------------------------------------------------
# One-time migration: pull existing small JSON files into app_state
# ----------------------------------------------------------------
def migrate_legacy():
    """
    Called once on startup. Reads old JSON files and merges them
    into app_state.json, then removes the originals.
    """
    if os.path.exists(STATE_FILE):
        return  # already migrated

    s = copy.deepcopy(_DEFAULTS)

    def _read(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    legacy = {
        "position":   os.path.join(app_dir, "position.json"),
        "pet_name":   os.path.join(app_dir, "pet_name.json"),
        "tutorial":   os.path.join(app_dir, "tutorial_done.json"),
        "settings":   os.path.join(app_dir, "chat_settings.json"),
        "prompt":     os.path.join(app_dir, "user_prompt.json"),
        "slang":      os.path.join(app_dir, "user_slang.json"),
        "notif_ev":   os.path.join(app_dir, "events_notified.json"),
        "notif_bd":   os.path.join(app_dir, "birthday_notified.json"),
        "memory":     os.path.join(app_dir, "chat_memory.json"),
    }

    # Do not create app_state.json on a clean install: that would make
    # is_first_launch() false before the onboarding flow can start.
    if not any(os.path.exists(path) for path in legacy.values()):
        return

    if d := _read(legacy["position"]):
        s["position"] = {"x": d.get("x"), "y": d.get("y")}

    if d := _read(legacy["pet_name"]):
        s["pet_name"] = d.get("name")

    if os.path.exists(legacy["tutorial"]):
        s["tutorial_done"] = True

    if d := _read(legacy["settings"]):
        for k in ("font_size", "window_width", "window_height", "event_window_theme"):
            if k in d:
                s[k] = d[k]

    if d := _read(legacy["prompt"]):
        s["prompt"] = d

    if d := _read(legacy["slang"]):
        s["slang"] = d

    if d := _read(legacy["notif_ev"]):
        s["notified_events"] = d

    if d := _read(legacy["notif_bd"]):
        s["notified_birthdays"] = d

    if d := _read(legacy["memory"]):
        s["memory"] = d

    if not save_state(s):
        return

    # Remove legacy files only after the migrated state is safely on disk.
    for path in legacy.values():
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
