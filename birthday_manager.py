# ================================================================
# ИМПОРТЫ
# ================================================================
import os
import json
from datetime import date

from PyQt5.QtWidgets import (
    QApplication, QWidget,
    QVBoxLayout,
    QLabel,
    QTableWidget, QTableWidgetItem,
    QPushButton,
    QDateEdit,
)
from PyQt5.QtCore import Qt, QTimer, QDate, QPropertyAnimation, QEasingCurve, QPoint

from config import app_dir  # общий путь к папке данных


# ================================================================
# СКЛОНЕНИЯ ЧИСЛИТЕЛЬНЫХ
# ================================================================
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


# ================================================================
# РАБОТА С ФАЙЛАМИ ДР
# ================================================================
def load_birthdays():
    """Загружает список дней рождения из JSON. При ошибке возвращает []."""
    try:
        with open(os.path.join(app_dir, "birthdays.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[birthday_manager] load_birthdays: {e}")
        return []


def save_birthdays(data):
    """Сохраняет список дней рождения в JSON."""
    try:
        with open(os.path.join(app_dir, "birthdays.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[birthday_manager] save_birthdays: {e}")


def load_last_check():
    """Загружает дату последней проверки ДР. При ошибке возвращает {}."""
    try:
        with open(os.path.join(app_dir, "birthday_notified.json"), "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[birthday_manager] load_last_check: {e}")
        return {}


def save_last_check(data):
    """Сохраняет дату последней проверки ДР."""
    try:
        with open(os.path.join(app_dir, "birthday_notified.json"), "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[birthday_manager] save_last_check: {e}")


# ================================================================
# УНИВЕРСАЛЬНЫЙ ТОСТ-УВЕДОМЛЕНИЕ С АНИМАЦИЕЙ
#
# Параметры:
#   text      — текст уведомления
#   color     — цвет фона в формате rgba(...)
#   offset_y  — конечный отступ снизу в пикселях
#
# Анимация: тост появляется снизу экрана и плавно всплывает
# на нужную высоту (easing curve OutCubic — быстрый старт,
# плавное торможение). Через 6 секунд так же плавно уходит вниз.
# ================================================================
class ToastNotification(QWidget):
    def __init__(self, text, color="rgba(40, 40, 40, 230)", offset_y=20):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(350, 120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(label)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {color};
                border-radius: 15px;
            }}
        """)

        screen = QApplication.primaryScreen().availableGeometry()

        # Конечная позиция (где тост должен остановиться)
        self._end_x   = screen.right() - self.width() - 20
        self._end_y   = screen.bottom() - self.height() - offset_y

        # Начальная позиция — за нижним краем экрана (невидима)
        self._start_x = self._end_x
        self._start_y = screen.bottom() + 10

        # Показываем сразу снизу, потом анимируем вверх
        self.move(self._start_x, self._start_y)
        self.show()

        # Анимация появления (всплытие вверх)
        self._anim_in = QPropertyAnimation(self, b"pos")
        self._anim_in.setDuration(350)
        self._anim_in.setStartValue(QPoint(self._start_x, self._start_y))
        self._anim_in.setEndValue(QPoint(self._end_x, self._end_y))
        self._anim_in.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_in.start()

        # Через 6 секунд — анимация исчезновения (уход вниз)
        QTimer.singleShot(6000, self._slide_out)

    def _slide_out(self):
        """Плавно убирает тост вниз за край экрана, затем закрывает."""
        screen = QApplication.primaryScreen().availableGeometry()

        self._anim_out = QPropertyAnimation(self, b"pos")
        self._anim_out.setDuration(300)
        self._anim_out.setStartValue(QPoint(self._end_x, self._end_y))
        self._anim_out.setEndValue(QPoint(self._start_x, screen.bottom() + 10))
        self._anim_out.setEasingCurve(QEasingCurve.InCubic)
        self._anim_out.finished.connect(self.close)
        self._anim_out.start()


# ================================================================
# ОКНО ДНЕЙ РОЖДЕНИЯ
# ================================================================
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

        self.btn_add    = QPushButton("Добавить")
        self.btn_remove = QPushButton("Удалить")
        self.btn_save   = QPushButton("Сохранить")

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
        """Загружает и сортирует ДР по ближайшей дате."""
        data = load_birthdays()
        today = date.today()

        def days_until(b):
            try:
                next_birthday = date(today.year, b["month"], b["day"])
                if next_birthday < today:
                    next_birthday = date(today.year + 1, b["month"], b["day"])
                return (next_birthday - today).days
            except Exception as e:
                print(f"[BirthdayWindow] days_until: {e}")
                return float("inf")

        data.sort(key=days_until)
        self.table.setRowCount(len(data))

        for row, b in enumerate(data):
            self.table.setItem(row, 0, QTableWidgetItem(b["name"]))

            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDate(QDate(b["year"], b["month"], b["day"]))
            self.table.setCellWidget(row, 1, date_edit)

    def add_row(self):
        """Добавляет новую пустую строку с текущей датой."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.currentDate())
        self.table.setCellWidget(row, 1, date_edit)

    def remove_row(self):
        """Удаляет выделенную строку."""
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def save_data(self):
        """Сохраняет данные и перезагружает таблицу."""
        data = []

        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            if not name_item:
                continue

            name = name_item.text().strip()
            if not name:
                continue

            date_edit = self.table.cellWidget(row, 1)
            qdate = date_edit.date()

            data.append({
                "name": name,
                "day": qdate.day(),
                "month": qdate.month(),
                "year": qdate.year()
            })

        save_birthdays(data)
        self.load_data()

        self.btn_save.setText("✔ Сохранено")
        self.btn_save.setEnabled(False)
        QTimer.singleShot(1500, self.restore_save_button)

    def restore_save_button(self):
        self.btn_save.setText("Сохранить")
        self.btn_save.setEnabled(True)

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
