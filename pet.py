import sys
import os
import random
import time
import json
from datetime import date

from PyQt5.QtWidgets import (
    QApplication, QLabel, QMessageBox,
    QMenu, QWidget, QVBoxLayout,
    QTableWidget, QTableWidgetItem,
    QPushButton,
    QDateEdit, QTimeEdit,
    QSystemTrayIcon, QAction
)

from PyQt5.QtCore import Qt, QTimer, QPoint, QDate, QTime
from PyQt5.QtGui import QPixmap, QIcon  # === ДОБАВЛЕНО TRAY ===


# ===============================
# ПУТИ ДЛЯ EXE (РЕСУРСЫ)
# ===============================
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")

# ===============================
# ПАПКА ДЛЯ ХРАНЕНИЯ ДАННЫХ (AppData)
# ===============================
from pathlib import Path

app_data_dir = Path(os.getenv("APPDATA")) / "PetReminder"
app_data_dir.mkdir(parents=True, exist_ok=True)

app_dir = str(app_data_dir)


# ===============================
# СКЛОНЕНИЯ
# ===============================
def years_word(n):
    if 11 <= n % 100 <= 14:
        return "лет"
    if n % 10 == 1:
        return "год"
    if 2 <= n % 10 <= 4:
        return "года"
    return "лет"


def days_word(n):
    if 11 <= n % 100 <= 14:
        return "дней"
    if n % 10 == 1:
        return "день"
    if 2 <= n % 10 <= 4:
        return "дня"
    return "дней"


# ===============================
# ФАЙЛЫ
# ===============================
def load_birthdays():
    try:
        with open(os.path.join(app_dir, "birthdays.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_birthdays(data):
    with open(os.path.join(app_dir, "birthdays.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_last_check():
    try:
        with open(os.path.join(app_dir, "birthday_notified.json"), "r") as f:
            return json.load(f)
    except:
        return {}


def save_last_check(data):
    with open(os.path.join(app_dir, "birthday_notified.json"), "w") as f:
        json.dump(data, f)


# ===============================
# СОБЫТИЯ (ОТДЕЛЬНО ОТ ДР)
# ===============================

def load_events():
    try:
        with open(os.path.join(app_dir, "events.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_events(data):
    with open(os.path.join(app_dir, "events.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_events_last_check():
    try:
        with open(os.path.join(app_dir, "events_notified.json"), "r") as f:
            return json.load(f)
    except:
        return {}

def save_events_last_check(data):
    with open(os.path.join(app_dir, "events_notified.json"), "w") as f:
        json.dump(data, f)


# ===============================
# ОКНО WIN 11 (КАЛЕНДАРЬ)
# ===============================
class BirthdayWindow(QWidget):
    def __init__(self):
        super().__init__(None)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Window |
            Qt.WindowStaysOnTopHint
        )

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.setFixedSize(480, 600)

        self.container = QWidget(self)
        self.container.setGeometry(0, 0, 480, 600)
        self.container.setObjectName("container")

        layout = QVBoxLayout(self.container)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(40, 40)
        self.btn_close.setObjectName("closeButton")
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close, alignment=Qt.AlignRight)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Имя", "Дата рождения"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.btn_add = QPushButton("Добавить")
        self.btn_remove = QPushButton("Удалить")
        self.btn_save = QPushButton("Сохранить")

        layout.addWidget(self.btn_add)
        layout.addWidget(self.btn_remove)
        layout.addWidget(self.btn_save)

        self.btn_add.clicked.connect(self.add_row)
        self.btn_remove.clicked.connect(self.remove_row)
        self.btn_save.clicked.connect(self.save_data)

        self.apply_style()
        self.load_data()
        self.show()

    def apply_style(self):
        self.setStyleSheet("""
        QWidget#container {
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
        }
        QTableWidget {
            background-color: white;
            border-radius: 10px;
            font-size: 14px;
        }
        QPushButton {
            background-color: #0078D7;
            color: white;
            border-radius: 10px;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background-color: #005ea6;
        }
        QPushButton#closeButton {
            background-color: transparent;
            color: #444;
            font-size: 20px;
            font-weight: bold;
            border-radius: 20px;
        }
        QPushButton#closeButton:hover {
            background-color: #e81123;
            color: white;
        }
        """)

    def load_data(self):
        data = load_birthdays()

        today = date.today()

        # 🔥 Сортировка по ближайшему ДР
        def days_until(b):
            try:
                next_birthday = date(today.year, b["month"], b["day"])
                if next_birthday < today:
                    next_birthday = date(today.year + 1, b["month"], b["day"])
                return (next_birthday - today).days
            except Exception as e:
                print("Ошибка даты:", e)
                return float("inf")

        data.sort(key=days_until)

        self.table.setRowCount(len(data))

        for row, b in enumerate(data):
            name_item = QTableWidgetItem(b["name"])
            self.table.setItem(row, 0, name_item)

            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDate(QDate(b["year"], b["month"], b["day"]))
            self.table.setCellWidget(row, 1, date_edit)

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)

        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.currentDate())
        self.table.setCellWidget(row, 1, date_edit)

    def remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def save_data(self):
        data = []

        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            if not name_item:
                continue

            name = name_item.text()
            date_edit = self.table.cellWidget(row, 1)
            qdate = date_edit.date()

            data.append({
                "name": name,
                "day": qdate.day(),
                "month": qdate.month(),
                "year": qdate.year()
            })

        save_birthdays(data)

        # Обновляем таблицу (пересортировка)
        self.load_data()

        # 🔥 Мягкое подтверждение
        self.btn_save.setText("✔ Сохранено")
        self.btn_save.setEnabled(False)

        QTimer.singleShot(1500, self.restore_save_button)

    def restore_save_button(self):
        self.btn_save.setText("Сохранить")
        self.btn_save.setEnabled(True)

    # ===============================
    # ПЕРЕТАСКИВАНИЕ ОКНА
    # ===============================

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.dragging = True
            event.accept()

    def mouseMoveEvent(self, event):
        if getattr(self, "dragging", False) and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

# ===============================
# ОКНО СОБЫТИЙ
# ===============================
class EventWindow(QWidget):
    def __init__(self):
        super().__init__(None)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Window |
            Qt.WindowStaysOnTopHint
        )

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.setFixedSize(500, 620)

        self.container = QWidget(self)
        self.container.setGeometry(0, 0, 500, 620)
        self.container.setObjectName("container")

        layout = QVBoxLayout(self.container)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(40, 40)
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close, alignment=Qt.AlignRight)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Название", "Дата", "Время", "Напомнить (дней)"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.btn_add = QPushButton("Добавить")
        self.btn_remove = QPushButton("Удалить")
        self.btn_save = QPushButton("Сохранить")

        layout.addWidget(self.btn_add)
        layout.addWidget(self.btn_remove)
        layout.addWidget(self.btn_save)

        self.btn_add.clicked.connect(self.add_row)
        self.btn_remove.clicked.connect(self.remove_row)
        self.btn_save.clicked.connect(self.save_data)

        self.apply_style()
        self.load_data()
        self.show()

    def apply_style(self):
        self.setStyleSheet("""
        QWidget#container {
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
        }
        QTableWidget {
            background-color: white;
            border-radius: 10px;
            font-size: 14px;
        }
        QPushButton {
            background-color: #0078D7;
            color: white;
            border-radius: 10px;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background-color: #005ea6;
        }
        """)

    def load_data(self):
        data = load_events()

        today = date.today()

        # 🔥 Сортировка по ближайшему событию
        def days_until(e):
            try:
                event_date = date(e["year"], e["month"], e["day"])
                return (event_date - today).days if event_date >= today else 9999
            except:
                return 9999

        data.sort(key=days_until)

        self.table.setRowCount(len(data))

        for row, e in enumerate(data):

            self.table.setItem(row, 0, QTableWidgetItem(e["title"]))

            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDate(QDate(e["year"], e["month"], e["day"]))
            self.table.setCellWidget(row, 1, date_edit)

            time_edit = QTimeEdit()
            time_edit.setDisplayFormat("HH:mm")
            time_edit.setTime(QTime(e.get("hour", 0), e.get("minute", 0)))
            self.table.setCellWidget(row, 2, time_edit)

            remind_item = QTableWidgetItem(str(e.get("remind_before", 0)))
            self.table.setItem(row, 3, remind_item)

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Дата
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.currentDate())
        self.table.setCellWidget(row, 1, date_edit)

        # Время
        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("HH:mm")
        time_edit.setTime(QTime.currentTime())
        self.table.setCellWidget(row, 2, time_edit)

        # Напоминание
        self.table.setItem(row, 3, QTableWidgetItem("0"))

    def remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def save_data(self):
        data = []

        for row in range(self.table.rowCount()):
            title_item = self.table.item(row, 0)
            remind_item = self.table.item(row, 3)

            if not title_item:
                continue

            title = title_item.text()
            remind_before = int(remind_item.text()) if remind_item else 0

            date_edit = self.table.cellWidget(row, 1)
            qdate = date_edit.date()

            time_edit = self.table.cellWidget(row, 2)
            qtime = time_edit.time()

            data.append({
                "title": title,
                "day": qdate.day(),
                "month": qdate.month(),
                "year": qdate.year(),
                "hour": qtime.hour(),
                "minute": qtime.minute(),
                "remind_before": remind_before
            })

        save_events(data)

        # пересортировка
        self.load_data()

        # мягкое подтверждение как у ДР
        self.btn_save.setText("✔ Сохранено")
        self.btn_save.setEnabled(False)

        QTimer.singleShot(1500, self.restore_save_button)

    def restore_save_button(self):
        self.btn_save.setText("Сохранить")
        self.btn_save.setEnabled(True)

    # ===============================
    # ПЕРЕТАСКИВАНИЕ ОКНА
    # ===============================

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            self.dragging = True
            event.accept()

    def mouseMoveEvent(self, event):
        if getattr(self, "dragging", False) and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

# ===============================
# TOAST
# ===============================
class ToastNotification(QWidget):
    def __init__(self, text):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(350, 120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(label)

        self.setStyleSheet("""
            QWidget {
                background-color: rgba(40, 40, 40, 230);
                border-radius: 15px;
            }
        """)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.right() - self.width() - 20,
            screen.bottom() - self.height() - 20
        )

        self.show()
        QTimer.singleShot(6000, self.close)

class EventToastNotification(QWidget):
    def __init__(self, text):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(350, 120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(label)

        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 90, 160, 230);
                border-radius: 15px;
            }
        """)

        screen = QApplication.primaryScreen().availableGeometry()

        # 🔥 Выше окна ДР (смещение вверх)
        self.move(
            screen.right() - self.width() - 20,
            screen.bottom() - self.height() - 160
        )

        self.show()
        QTimer.singleShot(6000, self.close)


# ===============================
# PET
# ===============================
class Pet(QLabel):

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # === TRAY ===
        self.tray = QSystemTrayIcon(self)

        icon_path = os.path.join(base_path, "icon.ico")
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))

        self.tray_menu = QMenu()

        show_action = QAction("🐾 Показать зверька", self)
        hide_action = QAction("📥 Скрыть в трей", self)

        birthdays_action = QAction("🎂 Дни рождения", self)
        nearest_action = QAction("🔔 Показать ближайший ДР", self)
        events_action = QAction("🗓 События", self)

        version_action = QAction("Pet Reminder v9.0", self)
        version_action.setEnabled(False)

        exit_action = QAction("❌ Выход", self)

        # Добавляем пункты один раз
        self.tray_menu.addAction(show_action)
        self.tray_menu.addAction(hide_action)
        self.tray_menu.addSeparator()

        self.tray_menu.addAction(birthdays_action)
        self.tray_menu.addAction(nearest_action)
        self.tray_menu.addAction(events_action)
        self.tray_menu.addSeparator()

        self.tray_menu.addAction(version_action)
        self.tray_menu.addAction(exit_action)

        # Подключаем действия
        show_action.triggered.connect(self.show)
        hide_action.triggered.connect(self.hide)
        birthdays_action.triggered.connect(self.open_birthday_window)
        events_action.triggered.connect(self.open_events_window)
        nearest_action.triggered.connect(self.show_next_birthday)
        exit_action.triggered.connect(QApplication.quit)

        self.tray.setContextMenu(self.tray_menu)
        self.tray.show()
        # === КОНЕЦ TRAY ===

        self.dragging = False
        self.moved = False
        self.offset = QPoint()

        self.idle_frames = self.load_frames("idle_clean")
        self.click_frames = self.load_frames("click_clean")
        self.sleep_frames = self.load_frames("sleeping_clean")

        # 🔴 Защита от пустых кадров
        if not self.idle_frames:
            QMessageBox.critical(
                None,
                "Ошибка",
                "Не найдены кадры idle_clean.\nПроверь сборку PyInstaller."
            )
            sys.exit(1)

        self.current_frames = self.idle_frames
        self.frame_index = 0
        self.playing_click = False
        self.sleeping = False

        self.last_interaction_time = time.time()
        self.sleep_after = 10

        first = self.idle_frames[0]
        self.setPixmap(first)
        self.resize(first.size())

        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.update_frame)
        self.anim_timer.start(33)

        self.behavior_timer = QTimer()
        self.behavior_timer.timeout.connect(self.random_behavior)
        self.behavior_timer.start(random.randint(3000, 6000))

        self.check_birthdays_once()
        QTimer.singleShot(2000, self.show_next_birthday)

        # 🔔 Проверка событий при запуске
        self.check_events_once()

        self.show()
    


    # ✅ Полное закрытие процесса
    def closeEvent(self, event):
        QApplication.quit()
        sys.exit(0)

    def load_frames(self, folder):
        frames = []
        folder_path = os.path.join(base_path, folder)

        if not os.path.exists(folder_path):
            return frames

        for file in sorted(os.listdir(folder_path)):
            if file.endswith(".png"):
                frames.append(QPixmap(os.path.join(folder_path, file)))

        return frames

    # дальше весь твой код БЕЗ ИЗМЕНЕНИЙ

    def update_frame(self):
        if not self.current_frames:
            return

        if not self.sleeping and time.time() - self.last_interaction_time > self.sleep_after:
            self.start_sleep()

        frame = self.current_frames[self.frame_index]

        self.setPixmap(frame)
        self.resize(frame.size())

        self.frame_index += 1
        if self.frame_index >= len(self.current_frames):
            self.frame_index = 0
            if self.playing_click:
                self.playing_click = False
                self.current_frames = self.idle_frames

    def random_behavior(self):
        if not self.sleeping and random.random() < 0.3:
            self.start_click_animation()
        self.behavior_timer.start(random.randint(3000, 6000))

    def start_click_animation(self):
        if self.click_frames:
            self.current_frames = self.click_frames
            self.frame_index = 0
            self.playing_click = True
            self.sleeping = False

    def start_sleep(self):
        if self.sleep_frames:
            self.current_frames = self.sleep_frames
            self.frame_index = 0
            self.sleeping = True
            self.playing_click = False

    def wake_up(self):
        self.sleeping = False
        self.current_frames = self.idle_frames
        self.frame_index = 0

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.moved = False
            self.offset = event.globalPos() - self.pos()
            self.last_interaction_time = time.time()
            if self.sleeping:
                self.wake_up()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.moved = True
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        if not self.moved:
            self.start_click_animation()
        self.dragging = False

    def check_birthdays_once(self):
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")

        last_check = load_last_check()
        if last_check.get("date") == today_str:
            return

        birthdays = load_birthdays()
        messages = []

        for b in birthdays:
            try:
                b_day = int(b["day"])
                b_month = int(b["month"])
                b_year = int(b["year"])

                next_birthday = date(today.year, b_month, b_day)
                if next_birthday < today:
                    next_birthday = date(today.year + 1, b_month, b_day)

                days_left = (next_birthday - today).days

                # ✅ Только 3 и 7 дней
                if days_left == 3:
                    messages.append(
                        f"⏳ Через 3 {days_word(3)} день рождения у {b['name']}!"
                    )

                elif days_left == 7:
                    messages.append(
                        f"📅 Через 7 {days_word(7)} день рождения у {b['name']}!"
                    )

            except:
                continue

        if messages:
            self.birthday_toast = ToastNotification("\n".join(messages))

        save_last_check({"date": today_str})

    def show_next_birthday(self):
        birthdays = load_birthdays()
        if not birthdays:
            return

        today = date.today()
        messages = []

        for b in birthdays:
            try:
                next_birthday = date(today.year, int(b["month"]), int(b["day"]))
                if next_birthday < today:
                    next_birthday = date(today.year + 1, int(b["month"]), int(b["day"]))

                days_left = (next_birthday - today).days

                # ✅ Только если 3 или 7 дней
                if days_left in (3, 7):
                    age = next_birthday.year - int(b["year"])
                    messages.append(
                        f"📅 {b['name']}\n"
                        f"Через {days_left} {days_word(days_left)}\n"
                        f"Исполнится {age} {years_word(age)}"
                    )

            except:
                continue

        if messages:
            self.birthday_toast = ToastNotification("\n\n".join(messages))

    # ===============================
    # ПРОВЕРКА СОБЫТИЙ (НОВОЕ)
    # ===============================
    def check_events_once(self):
        
        today = date.today()   # ← ДОБАВИТЬ ЭТУ СТРОКУ

        events = load_events()
        messages = []

        for e in events:
            try:
                event_date = date(
                    int(e["year"]),
                    int(e["month"]),
                    int(e["day"])
                )

                days_left = (event_date - today).days

                # 🔔 Напоминание за выбранное количество дней
                remind_before = int(e.get("remind_before", 0))

                # если до события осталось ровно столько дней,
                # сколько указано в колонке "Напомнить (дней)"
                if days_left == remind_before:

                    hour = int(e.get("hour", 0))
                    minute = int(e.get("minute", 0))

                    messages.append(
                        f"🗓 {e['title']}\n"
                        f"Через {days_left} {days_word(days_left)}\n"
                        f"В {hour:02d}:{minute:02d}"
                    )

            except:
                continue

        if messages:
            self.event_toast = EventToastNotification(
                "\n\n".join(messages)
            )

    # ===============================
    # ОТКРЫТИЕ ОКОН ИЗ TRAY
    # ===============================
    def open_birthday_window(self):
        self.birthday_window = BirthdayWindow()
        self.birthday_window.show()

    def open_events_window(self):
        self.events_window = EventWindow()
        self.events_window.show()       


# ===============================
# ЗАПУСК
# ===============================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pet = Pet()
    sys.exit(app.exec_())