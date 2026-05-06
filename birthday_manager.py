# ================================================================
# BIRTHDAY MANAGER
# Содержит только утилиты склонений и универсальный тост.
# Дни рождения теперь хранятся в events.json как ежегодные события.
# ================================================================
import os

from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint

from config import app_dir


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
# УНИВЕРСАЛЬНЫЙ ТОСТ-УВЕДОМЛЕНИЕ С АНИМАЦИЕЙ
#
# Параметры:
#   text      — текст уведомления
#   color     — цвет фона в формате rgba(...)
#   offset_y  — конечный отступ снизу в пикселях
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

        self._end_x = screen.right() - self.width() - 20
        self._end_y = screen.bottom() - self.height() - offset_y

        self._start_x = self._end_x
        self._start_y = screen.bottom() + 10

        self.move(self._start_x, self._start_y)
        self.show()

        # Анимация появления
        self._anim_in = QPropertyAnimation(self, b"pos")
        self._anim_in.setDuration(350)
        self._anim_in.setStartValue(QPoint(self._start_x, self._start_y))
        self._anim_in.setEndValue(QPoint(self._end_x, self._end_y))
        self._anim_in.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_in.start()

        QTimer.singleShot(6000, self._slide_out)

    def _slide_out(self):
        """Плавно убирает тост вниз."""
        screen = QApplication.primaryScreen().availableGeometry()
        self._anim_out = QPropertyAnimation(self, b"pos")
        self._anim_out.setDuration(300)
        self._anim_out.setStartValue(QPoint(self._end_x, self._end_y))
        self._anim_out.setEndValue(QPoint(self._start_x, screen.bottom() + 10))
        self._anim_out.setEasingCurve(QEasingCurve.InCubic)
        self._anim_out.finished.connect(self.close)
        self._anim_out.start()
