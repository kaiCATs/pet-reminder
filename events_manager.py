import json
import storage


# ================================================================
# СОБЫТИЯ
# ================================================================
def load_events():
    """Загружает список событий из JSON. При ошибке возвращает []."""
    try:
        with open(storage.EVENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[events_manager] load_events: {e}")
        return []


def save_events(data):
    """Сохраняет список событий в JSON."""
    try:
        storage._atomic_write_json(storage.EVENTS_FILE, data)
    except Exception as e:
        print(f"[events_manager] save_events: {e}")
