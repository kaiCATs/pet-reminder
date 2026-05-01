from PyQt5.QtWidgets import QCalendarWidget
from PyQt5.QtCore import Qt, QDate, QPoint
from PyQt5.QtGui import QPainter, QColor


class CustomCalendar(QCalendarWidget):
    def __init__(self, events):
        super().__init__()

        self.events = events or []

        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setFirstDayOfWeek(Qt.Monday)

    def set_events(self, events):
        self.events = events or []
        self.update()

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
            painter.setBrush(QColor("#1a73e8"))

            x = rect.center().x()
            y = rect.bottom() - 6

            count = min(len(day_events), 3)

            for i in range(count):
                painter.drawEllipse(
                    QPoint(x + (i - 1) * 6, y),
                    3, 3
                )

            painter.restore()

        except:
            pass