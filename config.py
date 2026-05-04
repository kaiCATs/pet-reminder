# ================================================================
# ОБЩИЕ ПУТИ И НАСТРОЙКИ ПРИЛОЖЕНИЯ
# Импортируется во все модули вместо дублирования путей везде.
# ================================================================
import os
import json
from pathlib import Path

app_data_dir = Path(os.getenv("APPDATA")) / "PetReminder"
app_data_dir.mkdir(parents=True, exist_ok=True)

app_dir = str(app_data_dir)  # строковый путь для os.path.join

_position_file = os.path.join(app_dir, "position.json")


# ================================================================
# ПОЗИЦИЯ ПИТОМЦА
# Сохраняется при каждом перемещении, загружается при старте.
# Если файла нет — питомец появляется в правом нижнем углу
# (конкретные координаты вычисляются в pet.py с учётом размера экрана).
# ================================================================
def load_position():
    """Загружает последнюю позицию питомца. При ошибке возвращает None."""
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
