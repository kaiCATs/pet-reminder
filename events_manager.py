import os
import json
from pathlib import Path

# ===============================
# ПАПКА ДАННЫХ (та же что в pet.py)
# ===============================
app_data_dir = Path(os.getenv("APPDATA")) / "PetReminder"
app_data_dir.mkdir(parents=True, exist_ok=True)

app_dir = str(app_data_dir)


# ===============================
# СОБЫТИЯ
# ===============================
def load_events():
    try:
        with open(os.path.join(app_dir, "events.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except:
        return []


def save_events(data):
    with open(os.path.join(app_dir, "events.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)