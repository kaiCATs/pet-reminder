import sys
import os

sys.path.append(os.path.dirname(__file__))
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget,
    QListWidgetItem, QInputDialog,
    QDialog, QDialogButtonBox, QTimeEdit,
    QLineEdit, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QDate, QTime
from PyQt5.QtGui import QFont

from calendar_widget import CustomCalendar

# загрузка/сохранение из pet.py
from events_manager import load_events, save_events


# ===============================
# 🔥 КАСТОМНОЕ ОКНО УДАЛЕНИЯ (БЕЗ ❓)
# ===============================
class DeleteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Dialog |
            Qt.WindowStaysOnTopHint
        )

        self.setFixedSize(280, 140)

        layout = QVBoxLayout(self)

        label = QLabel("Удалить событие?")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 16px;")
        layout.addWidget(label)

        buttons = QDialogButtonBox()

        ok_btn = QPushButton("Удалить")
        cancel_btn = QPushButton("Отмена")

        buttons.addButton(ok_btn, QDialogButtonBox.AcceptRole)
        buttons.addButton(cancel_btn, QDialogButtonBox.RejectRole)

        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

        layout.addWidget(buttons)


# ===============================
# 🗓 ОСНОВНОЕ ОКНО
# ===============================
class EventWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Window |
            Qt.WindowStaysOnTopHint
        )

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(900, 600)

        self.events = load_events()

        # ===============================
        # 📦 КОНТЕЙНЕР
        # ===============================
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 900, 600)
        self.container.setObjectName("container")

        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ===============================
        # ❌ КНОПКА ЗАКРЫТИЯ
        # ===============================
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(45, 45)
        self.close_btn.clicked.connect(self.close)
        main_layout.addWidget(self.close_btn, alignment=Qt.AlignRight)

        # ===============================
        # 🧱 ОСНОВНОЙ ЛЕЙАУТ
        # ===============================
        content = QHBoxLayout()
        main_layout.addLayout(content)

        # ===============================
        # 📅 КАЛЕНДАРЬ (ЛЕВО)
        # ===============================
        self.calendar = CustomCalendar(self.events)
        self.calendar.setMinimumWidth(500)
        self.calendar.clicked.connect(self.refresh_events)

        content.addWidget(self.calendar)

        # ===============================
        # 📜 СПИСОК СОБЫТИЙ (ПРАВО)
        # ===============================
        right_layout = QVBoxLayout()

        self.title = QLabel("События")
        self.title.setStyleSheet("font-size: 20px; font-weight: bold;")
        right_layout.addWidget(self.title)

        self.events_list = QListWidget()
        self.events_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.events_list.customContextMenuRequested.connect(self.delete_event)

        right_layout.addWidget(self.events_list)

        # ===============================
        # ➕ ДОБАВИТЬ
        # ===============================
        self.add_btn = QPushButton("Добавить событие")
        self.add_btn.clicked.connect(self.add_event)
        right_layout.addWidget(self.add_btn)

        content.addLayout(right_layout)

        self.apply_style()
        self.refresh_events()

    # ===============================
    # 🎨 СТИЛЬ
    # ===============================
    def apply_style(self):
        self.setStyleSheet("""
        QFrame#container {
            background-color: rgba(255, 255, 255, 0.85);
            border-radius: 20px;
        }

        QCalendarWidget {
            background-color: transparent;
            font-size: 16px;
        }

        QCalendarWidget QToolButton {
            font-size: 18px;
            height: 40px;
        }

        QCalendarWidget QMenu {
            font-size: 14px;
        }

        QCalendarWidget QWidget#qt_calendar_navigationbar {
            min-height: 45px;
        }

        QListWidget {
            background-color: white;
            border-radius: 10px;
            font-size: 15px;
        }

        QPushButton {
            background-color: #0078D7;
            color: white;
            border-radius: 10px;
            padding: 8px;
        }

        QPushButton:hover {
            background-color: #005ea6;
        }
        """)

    # ===============================
    # 🔄 ОБНОВЛЕНИЕ
    # ===============================
    def refresh_events(self):
        self.events_list.clear()

        selected_date = self.calendar.selectedDate()

        for e in self.events:
            date = QDate(int(e["year"]), int(e["month"]), int(e["day"]))

            if date != selected_date:
                continue

            time_str = f"{int(e.get('hour', 0)):02d}:{int(e.get('minute', 0)):02d}"

            item = QListWidgetItem(f"{time_str}  |  {e['title']}")
            item.setData(Qt.UserRole, e)

            self.events_list.addItem(item)

    # ===============================
    # ➕ ДОБАВЛЕНИЕ
    # ===============================
    def add_event(self):
        text, ok = QInputDialog.getText(self, "Событие", "Название:")

        if not ok or not text.strip():
            return

        time_dialog = QTimeEdit()
        time_dialog.setTime(QTime.currentTime())

        dialog = QDialog(self)
        dialog.setWindowTitle("Время")
        layout = QVBoxLayout(dialog)
        layout.addWidget(time_dialog)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        if dialog.exec_() != QDialog.Accepted:
            return

        time = time_dialog.time()
        date = self.calendar.selectedDate()

        new_event = {
            "title": text,
            "day": date.day(),
            "month": date.month(),
            "year": date.year(),
            "hour": time.hour(),
            "minute": time.minute(),
            "remind_before": 0
        }

        self.events.append(new_event)
        save_events(self.events)

        self.calendar.set_events(self.events)
        self.refresh_events()

    # ===============================
    # ❌ УДАЛЕНИЕ (ПКМ)
    # ===============================
    def delete_event(self, pos):
        item = self.events_list.itemAt(pos)
        if not item:
            return

        dialog = DeleteDialog(self)

        if dialog.exec_() != QDialog.Accepted:
            return

        event = item.data(Qt.UserRole)

        if event in self.events:
            self.events.remove(event)

        save_events(self.events)

        self.calendar.set_events(self.events)
        self.refresh_events()

    # ===============================
    # 🖱 ПЕРЕТАСКИВАНИЕ
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