import json
from config import app_dir  # общий путь к папке данных
import os


# ================================================================
# СОБЫТИЯ
# ================================================================
def load_events():
    """Загружает список событий из JSON. При ошибке возвращает []."""
    try:
        with open(os.path.join(app_dir, "events.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[events_manager] load_events: {e}")
        return []


def save_events(data):
    """Сохраняет список событий в JSON."""
    try:
        with open(os.path.join(app_dir, "events.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[events_manager] save_events: {e}")
