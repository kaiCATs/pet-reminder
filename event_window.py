import sys
import os

sys.path.append(os.path.dirname(__file__))

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget,
    QListWidgetItem, QDialog, QDialogButtonBox,
    QTimeEdit, QSpinBox, QFrame, QLineEdit,
    QComboBox,
)
from PyQt5.QtCore import Qt, QDate, QTime

from calendar_widget import CustomCalendar
from events_manager import load_events, save_events
from assistant import load_event_window_theme, save_event_window_theme


# ================================================================
# ВАРИАНТЫ ПОВТОРА СОБЫТИЯ
# Хранятся как строки в JSON-поле "repeat".
# ================================================================
REPEAT_OPTIONS = [
    "Без повтора",
    "Каждый день",
    "Каждую неделю",
    "Каждый месяц",
    "Каждый год",
]


# ================================================================
# ДИАЛОГ ПОДТВЕРЖДЕНИЯ УДАЛЕНИЯ
# ================================================================
class DeleteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setFixedSize(280, 140)

        layout = QVBoxLayout(self)

        label = QLabel("Удалить событие?")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 16px;")
        layout.addWidget(label)

        buttons = QDialogButtonBox()
        ok_btn     = QPushButton("Удалить")
        cancel_btn = QPushButton("Отмена")
        buttons.addButton(ok_btn, QDialogButtonBox.AcceptRole)
        buttons.addButton(cancel_btn, QDialogButtonBox.RejectRole)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)


# ================================================================
# ДИАЛОГ ДОБАВЛЕНИЯ / РЕДАКТИРОВАНИЯ СОБЫТИЯ
#
# Используется и для добавления и для редактирования —
# при редактировании передаётся existing_event с текущими данными.
# Поля: название, время, напомнить за (ч+мин), повтор.
# ================================================================
class EventDialog(QDialog):
    def __init__(self, parent=None, existing_event=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        # Прозрачный фон — иначе border-radius на контейнере не даст закруглений
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 380)

        # Состояние перетаскивания
        self._dragging = False
        self._drag_pos = None

        is_edit = existing_event is not None
        title_text = "Редактировать событие" if is_edit else "Новое событие"

        # Контейнер с закруглёнными углами (как в EventWindow)
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 400, 380)
        self.container.setObjectName("container")

        layout = QVBoxLayout(self.container)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок диалога
        header = QLabel(title_text)
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #222;")
        layout.addWidget(header)

        # Название
        layout.addWidget(QLabel("Название:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите название...")
        if is_edit:
            self.name_edit.setText(existing_event.get("title", ""))
        layout.addWidget(self.name_edit)

        # Время события
        layout.addWidget(QLabel("Время события:"))
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        if is_edit:
            self.time_edit.setTime(QTime(
                int(existing_event.get("hour", 0)),
                int(existing_event.get("minute", 0))
            ))
        else:
            self.time_edit.setTime(QTime.currentTime())
        layout.addWidget(self.time_edit)

        # Напомнить за (часы + минуты)
        layout.addWidget(QLabel("Напомнить за:"))
        remind_layout = QHBoxLayout()

        self.remind_hours = QSpinBox()
        self.remind_hours.setRange(0, 23)
        self.remind_hours.setSuffix(" ч")

        self.remind_minutes = QSpinBox()
        self.remind_minutes.setRange(0, 59)
        self.remind_minutes.setSuffix(" мин")

        if is_edit:
            total = int(existing_event.get("remind_before_minutes", 30))
            self.remind_hours.setValue(total // 60)
            self.remind_minutes.setValue(total % 60)
        else:
            self.remind_hours.setValue(0)
            self.remind_minutes.setValue(30)

        remind_layout.addWidget(self.remind_hours)
        remind_layout.addWidget(self.remind_minutes)
        layout.addLayout(remind_layout)

        # Повтор
        layout.addWidget(QLabel("Повтор:"))
        self.repeat_combo = QComboBox()
        self.repeat_combo.addItems(REPEAT_OPTIONS)
        if is_edit:
            repeat_val = existing_event.get("repeat", "Без повтора")
            idx = self.repeat_combo.findText(repeat_val)
            if idx >= 0:
                self.repeat_combo.setCurrentIndex(idx)
        layout.addWidget(self.repeat_combo)

        # Кнопки
        buttons = QDialogButtonBox()
        ok_btn     = QPushButton("Сохранить" if is_edit else "Добавить")
        cancel_btn = QPushButton("Отмена")
        buttons.addButton(ok_btn, QDialogButtonBox.AcceptRole)
        buttons.addButton(cancel_btn, QDialogButtonBox.RejectRole)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet("""
        QFrame#container {
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
        }
        QLineEdit, QTimeEdit, QSpinBox, QComboBox {
            border: 1px solid #ccc;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 14px;
            background-color: white;
        }
        QPushButton {
            background-color: #0078D7;
            color: white;
            border-radius: 8px;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background-color: #005ea6;
        }
        QLabel {
            font-size: 13px;
            color: #333;
        }
        """)

    # ----------------------------------------------------------------
    # Перетаскивание диалога
    # ----------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def get_values(self):
        """
        Возвращает введённые значения.
        remind_before_minutes = часы * 60 + минуты.
        """
        return {
            "name":                  self.name_edit.text().strip(),
            "time":                  self.time_edit.time(),
            "remind_before_minutes": self.remind_hours.value() * 60 + self.remind_minutes.value(),
            "repeat":                self.repeat_combo.currentText(),
        }


# ================================================================
# ОСНОВНОЕ ОКНО СОБЫТИЙ
#
# on_events_changed — необязательный колбэк, вызывается после
# любого изменения событий (добавление, редактирование, удаление).
# Pet передаёт сюда свой метод schedule_event_reminders чтобы
# таймеры обновлялись сразу без перезапуска приложения.
# ================================================================
class EventWindow(QWidget):
    def __init__(self, on_events_changed=None):
        super().__init__()

        # Колбэк для обновления таймеров в Pet после изменений
        self.on_events_changed = on_events_changed

        # Тема: "light" или "dark" — применяется к рамке/фону окна,
        # сам календарь остаётся светлым (чтоб не ломать его внутреннюю отрисовку)
        self._theme = load_event_window_theme()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(900, 600)

        self.events = load_events()

        # Контейнер
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 900, 600)
        self.container.setObjectName("container")

        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Верхняя панель: переключатель темы + кнопка закрытия
        top_row = QHBoxLayout()
        top_row.addStretch()

        self.theme_btn = QPushButton("🌙" if self._theme == "light" else "☀️")
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setFixedSize(36, 36)
        self.theme_btn.setToolTip("Переключить тему окна событий")
        self.theme_btn.clicked.connect(self._toggle_theme)
        top_row.addWidget(self.theme_btn)

        # Кнопка закрытия
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("closeBtn")
        self.close_btn.setFixedSize(45, 45)
        self.close_btn.clicked.connect(self.close)
        top_row.addWidget(self.close_btn)

        main_layout.addLayout(top_row)

        # Основной лейаут
        content = QHBoxLayout()
        main_layout.addLayout(content)

        # Календарь (левая панель) — заворачиваем в рамку чтоб тёмная тема
        # обрамляла его, не залезая внутрь
        cal_frame = QFrame()
        cal_frame.setObjectName("calFrame")
        cal_layout = QVBoxLayout(cal_frame)
        cal_layout.setContentsMargins(8, 8, 8, 8)
        self.calendar = CustomCalendar(self.events)
        self.calendar.setMinimumWidth(500)
        self.calendar.clicked.connect(self.refresh_events)
        cal_layout.addWidget(self.calendar)
        content.addWidget(cal_frame)

        # Правая панель
        right_layout = QVBoxLayout()

        self.title = QLabel("События")
        self.title.setObjectName("eventsTitle")
        right_layout.addWidget(self.title)

        self.events_list = QListWidget()
        # ПКМ — удаление
        self.events_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.events_list.customContextMenuRequested.connect(self.delete_event)
        # Двойной клик — редактирование
        self.events_list.itemDoubleClicked.connect(self.edit_event)
        right_layout.addWidget(self.events_list)

        # Подсказка про редактирование
        self.hint = QLabel("Двойной клик — редактировать  |  ПКМ — удалить")
        self.hint.setObjectName("hintLabel")
        self.hint.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.hint)

        self.add_btn = QPushButton("Добавить событие")
        self.add_btn.clicked.connect(self.add_event)
        right_layout.addWidget(self.add_btn)

        content.addLayout(right_layout)

        self.apply_style()
        self.refresh_events()

    def _toggle_theme(self):
        """Переключает тему окна событий."""
        self._theme = "dark" if self._theme == "light" else "light"
        save_event_window_theme(self._theme)
        self.theme_btn.setText("🌙" if self._theme == "light" else "☀️")
        self.apply_style()

    def apply_style(self):
        if self._theme == "dark":
            container_bg = "rgba(34, 34, 38, 0.95)"      # тёмное обрамление
            cal_frame_bg = "rgba(255, 255, 255, 0.96)"   # белая подложка для календаря
            list_bg      = "#2b2b30"
            list_color   = "#e0e0e0"
            list_alt     = "#33333a"
            title_color  = "#f0f0f0"
            hint_color   = "#9a9a9a"
            btn_bg       = "#3a8fff"
            btn_hover    = "#1f6fdc"
            btn_text     = "white"
            top_btn_bg   = "rgba(255,255,255,0.10)"
            top_btn_hover= "rgba(255,255,255,0.18)"
            top_btn_color= "#f0f0f0"
        else:
            container_bg = "rgba(255, 255, 255, 0.85)"
            cal_frame_bg = "rgba(255, 255, 255, 0.95)"
            list_bg      = "white"
            list_color   = "#222"
            list_alt     = "#f7f7f7"
            title_color  = "#222"
            hint_color   = "#888"
            btn_bg       = "#0078D7"
            btn_hover    = "#005ea6"
            btn_text     = "white"
            top_btn_bg   = "rgba(0,0,0,0.05)"
            top_btn_hover= "rgba(0,0,0,0.10)"
            top_btn_color= "#222"

        self.setStyleSheet(f"""
        QFrame#container {{
            background-color: {container_bg};
            border-radius: 20px;
        }}
        QFrame#calFrame {{
            background-color: {cal_frame_bg};
            border-radius: 14px;
        }}
        /* Сам календарь оставляем со светлой палитрой —
           кастомизация QCalendarWidget изнутри ломает отрисовку ячеек */
        QCalendarWidget {{
            background-color: white;
            font-size: 16px;
            color: #222;
        }}
        QCalendarWidget QToolButton {{
            font-size: 18px;
            height: 40px;
            color: #222;
            background-color: transparent;
        }}
        QCalendarWidget QMenu {{
            font-size: 14px;
            color: #222;
            background-color: white;
        }}
        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            min-height: 45px;
            background-color: #f0f0f0;
        }}
        QListWidget {{
            background-color: {list_bg};
            color: {list_color};
            border-radius: 10px;
            font-size: 15px;
            alternate-background-color: {list_alt};
            border: none;
            padding: 4px;
        }}
        QListWidget::item:selected {{
            background-color: {btn_bg};
            color: white;
        }}
        QLabel#eventsTitle {{
            font-size: 20px;
            font-weight: bold;
            color: {title_color};
        }}
        QLabel#hintLabel {{
            font-size: 11px;
            color: {hint_color};
        }}
        QPushButton {{
            background-color: {btn_bg};
            color: {btn_text};
            border-radius: 10px;
            padding: 8px;
        }}
        QPushButton:hover {{
            background-color: {btn_hover};
        }}
        QPushButton#themeBtn, QPushButton#closeBtn {{
            background-color: {top_btn_bg};
            color: {top_btn_color};
            border-radius: 10px;
            font-size: 16px;
        }}
        QPushButton#themeBtn:hover, QPushButton#closeBtn:hover {{
            background-color: {top_btn_hover};
        }}
        """)

    def refresh_events(self):
        """Обновляет список событий для выбранной даты."""
        self.events_list.clear()
        selected_date = self.calendar.selectedDate()

        for e in self.events:
            event_date = QDate(int(e["year"]), int(e["month"]), int(e["day"]))
            if event_date != selected_date:
                continue

            time_str = f"{int(e.get('hour', 0)):02d}:{int(e.get('minute', 0)):02d}"

            # Значок повтора
            repeat = e.get("repeat", "Без повтора")
            repeat_icons = {
                "Каждый день":    "🔁",
                "Каждую неделю":  "🔁",
                "Каждый месяц":   "🔁",
                "Каждый год":     "🔁",
            }
            repeat_str = f"  {repeat_icons[repeat]}" if repeat in repeat_icons else ""

            # Значок напоминания
            remind = int(e.get("remind_before_minutes", 0))
            if remind == 0:
                remind_str = "  🔔 в момент"
            elif remind < 60:
                remind_str = f"  🔔 за {remind} мин"
            elif remind < 24 * 60:
                h, m = divmod(remind, 60)
                if m > 0:
                    remind_str = f"  🔔 за {h}ч {m}мин"
                else:
                    remind_str = f"  🔔 за {h} ч"
            else:
                d, rest = divmod(remind, 24 * 60)
                if rest > 0:
                    h = rest // 60
                    remind_str = f"  🔔 за {d} дн {h} ч"
                elif d == 1:
                    remind_str = "  🔔 за день"
                elif d == 7:
                    remind_str = "  🔔 за неделю"
                else:
                    remind_str = f"  🔔 за {d} дн"

            item = QListWidgetItem(f"{time_str}  |  {e['title']}{remind_str}{repeat_str}")
            item.setData(Qt.UserRole, e)
            self.events_list.addItem(item)

    def _notify_changed(self):
        """Вызывает колбэк обновления таймеров в Pet (если передан)."""
        if self.on_events_changed:
            self.on_events_changed()

    def add_event(self):
        """Открывает диалог добавления нового события."""
        dialog = EventDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        values = dialog.get_values()
        if not values["name"]:
            return

        date = self.calendar.selectedDate()

        new_event = {
            "title":                 values["name"],
            "day":                   date.day(),
            "month":                 date.month(),
            "year":                  date.year(),
            "hour":                  values["time"].hour(),
            "minute":                values["time"].minute(),
            "remind_before_minutes": values["remind_before_minutes"],
            "repeat":                values["repeat"],
        }

        self.events.append(new_event)
        save_events(self.events)

        self.calendar.set_events(self.events)
        self.refresh_events()
        self._notify_changed()  # обновляем таймеры в Pet

    def edit_event(self, item):
        """
        Открывает диалог редактирования для события по двойному клику.
        Ищет событие в self.events по совпадению полей — PyQt5 возвращает
        копию словаря из UserRole, а не ссылку на оригинал.
        """
        event_copy = item.data(Qt.UserRole)

        # Находим реальный объект в списке по совпадению ключевых полей
        idx = None
        for i, e in enumerate(self.events):
            if (e.get("title")  == event_copy.get("title")  and
                e.get("day")    == event_copy.get("day")    and
                e.get("month")  == event_copy.get("month")  and
                e.get("year")   == event_copy.get("year")   and
                e.get("hour")   == event_copy.get("hour")   and
                e.get("minute") == event_copy.get("minute")):
                idx = i
                break

        if idx is None:
            return

        dialog = EventDialog(self, existing_event=self.events[idx])
        if dialog.exec_() != QDialog.Accepted:
            return

        values = dialog.get_values()
        if not values["name"]:
            return

        # Обновляем реальный объект в списке напрямую по индексу
        self.events[idx]["title"]                 = values["name"]
        self.events[idx]["hour"]                  = values["time"].hour()
        self.events[idx]["minute"]                = values["time"].minute()
        self.events[idx]["remind_before_minutes"] = values["remind_before_minutes"]
        self.events[idx]["repeat"]                = values["repeat"]

        save_events(self.events)
        self.calendar.set_events(self.events)
        self.refresh_events()
        self._notify_changed()

    def delete_event(self, pos):
        """Удаляет событие по ПКМ с подтверждением."""
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
        self._notify_changed()

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
