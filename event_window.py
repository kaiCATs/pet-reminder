# ================================================================
# EVENT WINDOW
# Uses storage (replaces config + assistant settings imports)
# and locale_app for all UI strings.
# ================================================================

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
import storage
from locale_app import t, repeat_options, repeat_to_internal, internal_to_display


# ================================================================
# DELETE CONFIRMATION DIALOG
# ================================================================
class DeleteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setFixedSize(280, 140)

        layout = QVBoxLayout(self)
        label = QLabel(t("ev_delete_q"))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 16px;")
        layout.addWidget(label)

        buttons   = QDialogButtonBox()
        ok_btn    = QPushButton(t("ev_delete_ok"))
        cancel_btn = QPushButton(t("ev_cancel"))
        buttons.addButton(ok_btn,    QDialogButtonBox.AcceptRole)
        buttons.addButton(cancel_btn, QDialogButtonBox.RejectRole)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet("""
        QDialog { background-color: white; border-radius: 12px; }
        QPushButton {
            background-color: #0078D7; color: white;
            border-radius: 8px; padding: 6px 12px;
        }
        QPushButton:hover { background-color: #005ea6; }
        """)


# ================================================================
# ADD / EDIT EVENT DIALOG
# ================================================================
class EventDialog(QDialog):
    def __init__(self, parent=None, existing_event=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 380)
        self._dragging = False
        self._drag_pos = None

        is_edit    = existing_event is not None
        title_text = t("ev_edit_title") if is_edit else t("ev_new")

        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 400, 380)
        self.container.setObjectName("container")

        layout = QVBoxLayout(self.container)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel(title_text)
        header.setStyleSheet("font-size: 15px; font-weight: bold; color: #222;")
        layout.addWidget(header)

        # Title
        layout.addWidget(QLabel(t("ev_name_label")))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(t("ev_name_ph"))
        if is_edit:
            self.name_edit.setText(existing_event.get("title", ""))
        layout.addWidget(self.name_edit)

        # Time
        layout.addWidget(QLabel(t("ev_time_label")))
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

        # Remind before
        layout.addWidget(QLabel(t("ev_remind_label")))
        remind_layout = QHBoxLayout()
        self.remind_hours = QSpinBox()
        self.remind_hours.setRange(0, 23)
        self.remind_hours.setSuffix(t("ev_suffix_h"))
        self.remind_minutes = QSpinBox()
        self.remind_minutes.setRange(0, 59)
        self.remind_minutes.setSuffix(t("ev_suffix_m"))
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

        # Repeat
        layout.addWidget(QLabel(t("ev_repeat_label")))
        self.repeat_combo = QComboBox()
        self.repeat_combo.addItems(repeat_options())
        if is_edit:
            display = internal_to_display(existing_event.get("repeat", "no_repeat"))
            idx = self.repeat_combo.findText(display)
            if idx >= 0:
                self.repeat_combo.setCurrentIndex(idx)
        layout.addWidget(self.repeat_combo)

        # Buttons
        buttons   = QDialogButtonBox()
        ok_btn    = QPushButton(t("ev_save") if is_edit else t("ev_add_btn"))
        cancel_btn = QPushButton(t("ev_cancel"))
        buttons.addButton(ok_btn,    QDialogButtonBox.AcceptRole)
        buttons.addButton(cancel_btn, QDialogButtonBox.RejectRole)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet("""
        QFrame#container {
            background-color: rgba(255,255,255,0.95);
            border-radius: 20px;
        }
        QLineEdit, QTimeEdit, QSpinBox, QComboBox {
            border: 1px solid #ccc; border-radius: 6px;
            padding: 4px 8px; font-size: 14px; background: white;
        }
        QPushButton {
            background-color: #0078D7; color: white;
            border-radius: 8px; padding: 6px 12px;
        }
        QPushButton:hover { background-color: #005ea6; }
        QLabel { font-size: 13px; color: #333; }
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def get_values(self):
        return {
            "name":                  self.name_edit.text().strip(),
            "time":                  self.time_edit.time(),
            "remind_before_minutes": self.remind_hours.value() * 60 + self.remind_minutes.value(),
            "repeat":                repeat_to_internal(self.repeat_combo.currentText()),
        }


# ================================================================
# MAIN EVENT WINDOW
# ================================================================
class EventWindow(QWidget):
    def __init__(self, on_events_changed=None):
        super().__init__()
        self.on_events_changed = on_events_changed
        self.events = load_events()

        theme = storage.load_event_window_theme()
        is_dark = (theme == "dark")

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Window | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(520, 560)

        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width()  // 2,
            screen.center().y() - self.height() // 2,
        )

        container = QFrame(self)
        container.setGeometry(0, 0, 520, 560)
        container.setObjectName("evContainer")

        outer = QVBoxLayout(container)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(12)

        # Header row
        header_row = QHBoxLayout()
        title_lbl = QLabel(t("ev_title"))
        title_lbl.setObjectName("eventsTitle")
        header_row.addWidget(title_lbl)
        header_row.addStretch()

        theme_btn = QPushButton("🌙" if not is_dark else "☀️")
        theme_btn.setObjectName("themeBtn")
        theme_btn.setFixedSize(36, 36)
        theme_btn.clicked.connect(self._toggle_theme)
        header_row.addWidget(theme_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(36, 36)
        close_btn.clicked.connect(self.close)
        header_row.addWidget(close_btn)
        outer.addLayout(header_row)

        # Calendar
        cal_frame = QFrame()
        cal_frame.setObjectName("calFrame")
        cal_layout = QVBoxLayout(cal_frame)
        cal_layout.setContentsMargins(8, 8, 8, 8)
        self.calendar = CustomCalendar()
        self.calendar.set_events(self.events)
        self.calendar.selectionChanged.connect(self.refresh_events)
        cal_layout.addWidget(self.calendar)
        outer.addWidget(cal_frame)

        # Events list
        self.events_list = QListWidget()
        self.events_list.setAlternatingRowColors(True)
        self.events_list.itemDoubleClicked.connect(self.edit_event)
        self.events_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.events_list.customContextMenuRequested.connect(self.delete_event)
        outer.addWidget(self.events_list)

        # Hint
        hint_lbl = QLabel(t("ev_hint"))
        hint_lbl.setObjectName("hintLabel")
        hint_lbl.setAlignment(Qt.AlignCenter)
        outer.addWidget(hint_lbl)

        # Add button
        add_btn = QPushButton(t("ev_add"))
        add_btn.clicked.connect(self.add_event)
        outer.addWidget(add_btn)

        self._apply_theme(is_dark)
        self.refresh_events()

    # ----------------------------------------------------------------
    def _toggle_theme(self):
        current = storage.load_event_window_theme()
        new_theme = "light" if current == "dark" else "dark"
        storage.save_event_window_theme(new_theme)
        self._apply_theme(new_theme == "dark")

    def _apply_theme(self, is_dark: bool):
        if is_dark:
            container_bg = "rgba(30,30,30,0.97)"
            cal_frame_bg = "rgba(45,45,45,0.95)"
            list_bg      = "#2a2a2a"
            list_color   = "#eee"
            list_alt     = "#323232"
            title_color  = "#eee"
            hint_color   = "#888"
            btn_bg       = "#0078D7"
            btn_text     = "white"
            btn_hover    = "#005ea6"
            top_btn_bg   = "rgba(255,255,255,0.08)"
            top_btn_color = "#ccc"
            top_btn_hover = "rgba(255,255,255,0.15)"
        else:
            container_bg = "rgba(255,255,255,0.97)"
            cal_frame_bg = "rgba(240,240,240,0.95)"
            list_bg      = "white"
            list_color   = "#222"
            list_alt     = "#f7f7f7"
            title_color  = "#222"
            hint_color   = "#aaa"
            btn_bg       = "#0078D7"
            btn_text     = "white"
            btn_hover    = "#005ea6"
            top_btn_bg   = "rgba(0,0,0,0.05)"
            top_btn_color = "#555"
            top_btn_hover = "rgba(0,0,0,0.10)"

        self.setStyleSheet(f"""
        QFrame#evContainer {{
            background-color: {container_bg};
            border-radius: 20px;
        }}
        QFrame#calFrame {{
            background-color: {cal_frame_bg};
            border-radius: 14px;
        }}
        QCalendarWidget {{
            background-color: white; font-size: 16px; color: #222;
        }}
        QCalendarWidget QToolButton {{
            font-size: 18px; height: 40px; color: #222; background-color: transparent;
        }}
        QCalendarWidget QMenu {{ font-size: 14px; color: #222; background-color: white; }}
        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            min-height: 45px; background-color: #f0f0f0;
        }}
        QListWidget {{
            background-color: {list_bg}; color: {list_color};
            border-radius: 10px; font-size: 15px;
            alternate-background-color: {list_alt};
            border: none; padding: 4px;
        }}
        QListWidget::item:selected {{ background-color: {btn_bg}; color: white; }}
        QLabel#eventsTitle {{ font-size: 20px; font-weight: bold; color: {title_color}; }}
        QLabel#hintLabel {{ font-size: 11px; color: {hint_color}; }}
        QPushButton {{ background-color: {btn_bg}; color: {btn_text}; border-radius: 10px; padding: 8px; }}
        QPushButton:hover {{ background-color: {btn_hover}; }}
        QPushButton#themeBtn, QPushButton#closeBtn {{
            background-color: {top_btn_bg}; color: {top_btn_color}; border-radius: 10px; font-size: 16px;
        }}
        QPushButton#themeBtn:hover, QPushButton#closeBtn:hover {{
            background-color: {top_btn_hover};
        }}
        """)

    def refresh_events(self):
        self.events_list.clear()
        selected_date = self.calendar.selectedDate()
        for e in self.events:
            if QDate(int(e["year"]), int(e["month"]), int(e["day"])) != selected_date:
                continue
            time_str   = f"{int(e.get('hour',0)):02d}:{int(e.get('minute',0)):02d}"
            repeat     = e.get("repeat", "no_repeat")
            repeat_str = "  🔁" if repeat != "no_repeat" else ""
            remind     = int(e.get("remind_before_minutes", 0))
            if remind == 0:
                remind_str = f"  {t('ev_remind_now')}"
            elif remind < 60:
                remind_str = f"  {t('ev_remind_min', n=remind)}"
            elif remind < 24 * 60:
                h, m = divmod(remind, 60)
                remind_str = f"  {t('ev_remind_hm', h=h, m=m)}" if m else f"  {t('ev_remind_h', h=h)}"
            else:
                d, rest = divmod(remind, 24 * 60)
                if d == 1 and not rest:
                    remind_str = f"  {t('ev_remind_day')}"
                elif d == 7 and not rest:
                    remind_str = f"  {t('ev_remind_week')}"
                else:
                    remind_str = f"  {t('ev_remind_days', d=d)}"
            item = QListWidgetItem(f"{time_str}  |  {e['title']}{remind_str}{repeat_str}")
            item.setData(Qt.UserRole, e)
            self.events_list.addItem(item)

    def _notify_changed(self):
        if self.on_events_changed:
            self.on_events_changed()

    def add_event(self):
        dialog = EventDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        values = dialog.get_values()
        if not values["name"]:
            return
        date = self.calendar.selectedDate()
        self.events.append({
            "title":                 values["name"],
            "day":   date.day(),   "month": date.month(), "year": date.year(),
            "hour":  values["time"].hour(),
            "minute": values["time"].minute(),
            "remind_before_minutes": values["remind_before_minutes"],
            "repeat": values["repeat"],
        })
        save_events(self.events)
        self.calendar.set_events(self.events)
        self.refresh_events()
        self._notify_changed()

    def edit_event(self, item):
        event_copy = item.data(Qt.UserRole)
        idx = next((
            i for i, e in enumerate(self.events)
            if (e.get("title") == event_copy.get("title") and
                e.get("day")   == event_copy.get("day")   and
                e.get("month") == event_copy.get("month") and
                e.get("year")  == event_copy.get("year")  and
                e.get("hour")  == event_copy.get("hour")  and
                e.get("minute")== event_copy.get("minute"))
        ), None)
        if idx is None:
            return
        dialog = EventDialog(self, existing_event=self.events[idx])
        if dialog.exec_() != QDialog.Accepted:
            return
        values = dialog.get_values()
        if not values["name"]:
            return
        e = self.events[idx]
        e["title"]                 = values["name"]
        e["hour"]                  = values["time"].hour()
        e["minute"]                = values["time"].minute()
        e["remind_before_minutes"] = values["remind_before_minutes"]
        e["repeat"]                = values["repeat"]
        save_events(self.events)
        self.calendar.set_events(self.events)
        self.refresh_events()
        self._notify_changed()

    def delete_event(self, pos):
        item = self.events_list.itemAt(pos)
        if not item:
            return
        if DeleteDialog(self).exec_() != QDialog.Accepted:
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

    def mouseMoveEvent(self, event):
        if getattr(self, "dragging", False) and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)

    def mouseReleaseEvent(self, event):
        self.dragging = False
