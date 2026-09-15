from PyQt5.QtWidgets import QCalendarWidget, QToolButton, QAbstractItemView, QHeaderView
from PyQt5.QtCore import Qt, QDate, QPoint, QLocale
from PyQt5.QtGui import QPainter, QColor, QIcon, QPalette


TEAL = "#008F95"
TEAL_DARK = "#00777B"


def _capitalize_first(text: str) -> str:
    text = text.strip()
    return text[:1].upper() + text[1:] if text else text


def calendar_stylesheet(theme="light") -> str:
    """Shared visual language for the main and date-picker calendars."""
    is_dark = theme == "dark"
    if is_dark:
        calendar_bg = "#2D2D2D"
        navigation_bg = "#3A3A3A"
        text = "#EEEEEE"
        muted = "#888888"
        hover_bg = "rgba(255,255,255,0.12)"
        grid = "#555555"
    else:
        calendar_bg = "#FFFFFF"
        navigation_bg = "#EAF7F7"
        text = "#222222"
        muted = "#AAAAAA"
        hover_bg = "rgba(0,143,149,0.12)"
        grid = "#E4E4E4"

    return f"""
    QCalendarWidget {{
        background-color: {calendar_bg};
        color: {text};
        font-size: 16px;
    }}
    QCalendarWidget QWidget#qt_calendar_navigationbar {{
        min-height: 52px;
        background-color: {navigation_bg};
    }}
    QCalendarWidget QToolButton#qt_calendar_prevmonth,
    QCalendarWidget QToolButton#qt_calendar_nextmonth {{
        min-width: 40px;
        max-width: 40px;
        min-height: 40px;
        max-height: 40px;
        margin: 4px;
        padding: 0;
        border: none;
        border-radius: 20px;
        background-color: {TEAL};
        color: white;
        font-size: 26px;
        font-weight: 600;
    }}
    QCalendarWidget QToolButton#qt_calendar_prevmonth:hover,
    QCalendarWidget QToolButton#qt_calendar_nextmonth:hover {{
        background-color: {TEAL_DARK};
    }}
    QCalendarWidget QToolButton#qt_calendar_monthbutton,
    QCalendarWidget QToolButton#qt_calendar_yearbutton {{
        min-height: 36px;
        padding: 5px 10px;
        border: none;
        border-radius: 8px;
        background-color: transparent;
        color: {text};
        font-size: 16px;
        font-weight: 600;
    }}
    QCalendarWidget QToolButton#qt_calendar_monthbutton:hover,
    QCalendarWidget QToolButton#qt_calendar_yearbutton:hover {{
        background-color: {hover_bg};
    }}
    QCalendarWidget QSpinBox {{
        padding: 4px;
        border: none;
        background-color: {calendar_bg};
        color: {text};
    }}
    QCalendarWidget QAbstractItemView {{
        background-color: {calendar_bg};
        color: {text};
        selection-background-color: {TEAL};
        selection-color: white;
        gridline-color: {grid};
        outline: none;
        border: none;
    }}
    QCalendarWidget QAbstractItemView:enabled {{
        background-color: {calendar_bg};
        color: {text};
        selection-background-color: {TEAL};
        selection-color: white;
    }}
    QCalendarWidget QHeaderView,
    QCalendarWidget QHeaderView::section,
    QCalendarWidget QAbstractItemView QHeaderView::section {{
        background-color: {calendar_bg};
        color: {text};
        border: none;
        padding: 6px 2px;
        font-weight: 600;
    }}
    QCalendarWidget QAbstractItemView:disabled {{
        color: {muted};
    }}
    QCalendarWidget QMenu {{
        background-color: {calendar_bg};
        color: {text};
        border: 1px solid {grid};
    }}
    QCalendarWidget QMenu::item:selected {{
        background-color: {TEAL};
        color: white;
    }}
    """


class StyledCalendar(QCalendarWidget):
    """Reusable calendar with the same navigation and typography everywhere."""

    def __init__(self, events=None, theme="light"):
        super().__init__()
        self.events = events or []
        self._month_menu = None

        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setFirstDayOfWeek(Qt.Monday)
        self._apply_locale()
        self.set_calendar_theme(theme)
        self.currentPageChanged.connect(self._refresh_navigation)
        self._refresh_navigation()

    def _apply_locale(self):
        import storage

        language = storage.current_language()
        locale = QLocale(QLocale.English) if language == "en" else QLocale(QLocale.Russian)
        self.setLocale(locale)

    def set_calendar_theme(self, theme="light"):
        self._theme = "dark" if theme == "dark" else "light"
        self.setStyleSheet(calendar_stylesheet(self._theme))
        self._apply_calendar_palette()
        self._refresh_navigation()

    def _apply_calendar_palette(self):
        is_dark = self._theme == "dark"
        background = QColor("#2D2D2D" if is_dark else "#FFFFFF")
        text = QColor("#EEEEEE" if is_dark else "#222222")
        teal = QColor(0, 143, 149)

        view = self.findChild(QAbstractItemView)
        if view is not None:
            palette = view.palette()
            for role in (QPalette.Base, QPalette.Window, QPalette.AlternateBase):
                palette.setColor(role, background)
            for role in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText):
                palette.setColor(role, text)
            palette.setColor(QPalette.Highlight, teal)
            palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
            view.setPalette(palette)

        # The weekday row is a separate header widget and does not always
        # inherit the view palette on Windows' native style.
        for header in self.findChildren(QHeaderView):
            palette = header.palette()
            for role in (QPalette.Base, QPalette.Button, QPalette.Window):
                palette.setColor(role, background)
            for role in (QPalette.ButtonText, QPalette.WindowText, QPalette.Text):
                palette.setColor(role, text)
            header.setPalette(palette)
            header.setAutoFillBackground(True)
            header.setStyleSheet(
                f"QHeaderView {{ background-color: {background.name()}; color: {text.name()}; }} "
                f"QHeaderView::section {{ background-color: {background.name()}; "
                f"color: {text.name()}; border: none; padding: 6px 2px; "
                "font-weight: 600; }}"
            )

    def _refresh_navigation(self, *_args):
        # QCalendarWidget supplies platform-dependent arrow icons. Replacing
        # them with text arrows keeps their colour identical on every Windows
        # theme and makes the circular hit target visibly larger.
        for object_name, symbol in (
            ("qt_calendar_prevmonth", "‹"),
            ("qt_calendar_nextmonth", "›"),
        ):
            button = self.findChild(QToolButton, object_name)
            if button is None:
                continue
            button.setIcon(QIcon())
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setText(symbol)
            button.setCursor(Qt.PointingHandCursor)

        month_button = self.findChild(QToolButton, "qt_calendar_monthbutton")
        if month_button is not None:
            month_button.setText(_capitalize_first(month_button.text()))
            month_menu = month_button.menu()
            if month_menu is not None and month_menu is not self._month_menu:
                self._month_menu = month_menu
                month_menu.aboutToShow.connect(self._capitalize_month_menu)
            self._capitalize_month_menu()

    def _capitalize_month_menu(self):
        if self._month_menu is None:
            return
        for action in self._month_menu.actions():
            action.setText(_capitalize_first(action.text()))

    def set_events(self, events):
        self.events = events or []
        self._apply_locale()
        self._refresh_navigation()
        self.update()


class CustomCalendar(StyledCalendar):
    def __init__(self, events, theme="light"):
        super().__init__(events=events, theme=theme)

    def paintCell(self, painter, rect, date):
        super().paintCell(painter, rect, date)

        try:
            day_events = [
                e for e in self.events
                if QDate(int(e["year"]), int(e["month"]), int(e["day"])) == date
            ]

            if not day_events:
                return

            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(TEAL))

            x = rect.center().x()
            y = rect.bottom() - 6

            count = min(len(day_events), 3)

            for i in range(count):
                painter.drawEllipse(
                    QPoint(x + (i - 1) * 6, y),
                    3, 3
                )

            painter.restore()

        except Exception:
            pass
