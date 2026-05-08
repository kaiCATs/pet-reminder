# ================================================================
# TUTORIAL
# On-boarding flow shown on first launch.
# Uses storage (replaces config) and locale_app for all strings.
# ================================================================

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QFrame, QApplication, QGraphicsOpacityEffect,
    QStackedWidget,
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation,
    QEasingCurve, QPoint, QRect,
)
from PyQt5.QtGui import QFont

import storage
from locale_app import t


# ================================================================
# PROFANITY FILTER
# ================================================================
_BAD_WORDS = [
    "хуй", "хуе", "хуя", "хуи", "пизд", "ебл", "ёбл", "еба", "ёба",
    "бляд", "блят", "сука", "пидр", "пидо", "мудак", "мудил", "залуп",
    "ёбан", "ебан", "еблан", "шлюх", "дрочи", "дроч", "ёбнут", "ебнут",
    "fuck", "shit", "bitch", "cunt", "dick", "cock", "ass",
]

def _contains_bad_word(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in _BAD_WORDS)


# ================================================================
# TUTORIAL STEPS — titles and texts come from locale_app
# ================================================================
_STEP_KEYS = [
    ("tut_s0_title", "tut_s0_text"),
    ("tut_s1_title", "tut_s1_text"),
    ("tut_s2_title", "tut_s2_text"),
    ("tut_s3_title", "tut_s3_text"),
    ("tut_s4_title", "tut_s4_text"),
    ("tut_s5_title", "tut_s5_text"),
    ("tut_s6_title", "tut_s6_text"),
]


# ================================================================
# PET NAME DIALOG
# ================================================================
class PetNameDialog(QWidget):
    def __init__(self, on_name_saved=None):
        super().__init__()
        self.on_name_saved = on_name_saved

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Window
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(440, 300)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )

        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 440, 300)
        self.container.setObjectName("container")

        layout = QVBoxLayout(self.container)
        layout.setSpacing(15)
        layout.setContentsMargins(35, 35, 35, 35)

        title = QLabel(t("name_title"))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #222;")
        layout.addWidget(title)

        hint = QLabel(t("name_hint"))
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("font-size: 15px; color: #555;")
        layout.addWidget(hint)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("name_ph"))
        self.name_input.setMaxLength(20)
        self.name_input.setStyleSheet("font-size: 16px;")
        self.name_input.returnPressed.connect(self._save)
        layout.addWidget(self.name_input)

        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("font-size: 13px; color: #e81123;")
        layout.addWidget(self.error_label)

        self.save_btn = QPushButton(t("name_save"))
        self.save_btn.clicked.connect(self._save)
        layout.addWidget(self.save_btn)

        self._apply_style()
        self._fade_in()
        self.show()

    def _apply_style(self):
        self.setStyleSheet("""
        QFrame#container {
            background-color: rgba(255,255,255,0.97);
            border-radius: 20px;
        }
        QLineEdit {
            border: 2px solid #0078D7;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 16px;
        }
        QLineEdit:focus { border-color: #005ea6; }
        QPushButton {
            background-color: #0078D7;
            color: white;
            border-radius: 10px;
            padding: 12px;
            font-size: 15px;
        }
        QPushButton:hover { background-color: #005ea6; }
        """)

    def _fade_in(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        self._anim = QPropertyAnimation(effect, b"opacity")
        self._anim.setDuration(400)
        self._anim.setStartValue(0)
        self._anim.setEndValue(1)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def _save(self):
        name = self.name_input.text().strip()
        if not name:
            self.error_label.setText(t("name_empty"))
            return
        if len(name) < 2:
            self.error_label.setText(t("name_short"))
            return
        if _contains_bad_word(name):
            self.error_label.setText(t("name_bad"))
            return

        storage.save_pet_name(name)
        self.error_label.setText("")
        if self.on_name_saved:
            self.on_name_saved(name)
        self.close()

    def closeEvent(self, event):
        if storage.load_pet_name() is None:
            event.ignore()
        else:
            event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPos() - self._drag_pos)


# ================================================================
# TUTORIAL WINDOW
# ================================================================
class TutorialWindow(QWidget):
    def __init__(self, on_finished=None):
        super().__init__()
        self.on_finished    = on_finished
        self._current_index = 0
        self._animating     = False

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Window
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 340)

        screen = QApplication.primaryScreen().availableGeometry()
        self._end_x = screen.right()  - self.width()  - 30
        self._end_y = screen.bottom() - self.height() - 30
        self.move(self._end_x, screen.bottom() + 10)

        # Container
        self._cont = QFrame(self)
        self._cont.setGeometry(0, 0, 400, 340)
        self._cont.setObjectName("tutContainer")

        outer = QVBoxLayout(self._cont)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(10)

        # Slide area
        self._slide_area = QFrame()
        self._slide_area.setFixedSize(352, 210)
        self._slide_area.setStyleSheet("background: transparent;")
        outer.addWidget(self._slide_area)

        # Pages
        self._pages = []
        for title_key, text_key in _STEP_KEYS:
            page = QWidget(self._slide_area)
            page.setGeometry(0, 0, 352, 210)
            pl = QVBoxLayout(page)
            pl.setContentsMargins(0, 0, 0, 0)
            pl.setSpacing(12)

            lbl_title = QLabel(t(title_key))
            lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #222;")
            pl.addWidget(lbl_title)

            lbl_text = QLabel(t(text_key))
            lbl_text.setWordWrap(True)
            lbl_text.setStyleSheet("font-size: 14px; color: #444; line-height: 1.4;")
            pl.addWidget(lbl_text)
            pl.addStretch()

            self._pages.append(page)

        for i, p in enumerate(self._pages):
            p.setVisible(i == 0)

        # Dots
        dots_layout = QHBoxLayout()
        dots_layout.setSpacing(6)
        self._dots_layout = dots_layout
        outer.addLayout(dots_layout)
        self._build_dots()

        # Buttons
        btn_layout = QHBoxLayout()
        self._skip_btn = QPushButton(t("tut_skip"))
        self._skip_btn.setObjectName("skipBtn")
        self._skip_btn.clicked.connect(self._skip_all)

        self._next_btn = QPushButton(t("tut_next"))
        self._next_btn.clicked.connect(self._next)

        btn_layout.addWidget(self._skip_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self._next_btn)
        outer.addLayout(btn_layout)

        self._apply_style()
        self._slide_in()
        self.show()

    def _build_dots(self):
        while self._dots_layout.count():
            item = self._dots_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._dots_layout.addStretch()
        for i in range(len(_STEP_KEYS)):
            dot = QLabel("●" if i == self._current_index else "○")
            dot.setStyleSheet(
                "font-size: 14px; color: #0078D7;" if i == self._current_index
                else "font-size: 14px; color: #ccc;"
            )
            self._dots_layout.insertWidget(i + 1, dot)
        self._dots_layout.addStretch()

    def _apply_style(self):
        self.setStyleSheet("""
        QFrame#tutContainer {
            background-color: rgba(255,255,255,0.97);
            border-radius: 20px;
            border: 1px solid rgba(0,120,215,0.25);
        }
        QPushButton {
            background-color: #0078D7;
            color: white;
            border-radius: 9px;
            padding: 9px 20px;
            font-size: 14px;
        }
        QPushButton:hover { background-color: #005ea6; }
        QPushButton#skipBtn {
            background-color: transparent;
            color: #999;
            border: 1px solid #ddd;
        }
        QPushButton#skipBtn:hover { background-color: #f5f5f5; color: #666; }
        """)

    def _slide_in(self):
        self._anim_win = QPropertyAnimation(self, b"pos")
        self._anim_win.setDuration(380)
        self._anim_win.setStartValue(QPoint(self._end_x, self._end_y + 300))
        self._anim_win.setEndValue(QPoint(self._end_x, self._end_y))
        self._anim_win.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_win.start()

    def _slide_out_window(self, callback):
        screen = QApplication.primaryScreen().availableGeometry()
        self._anim_close = QPropertyAnimation(self, b"pos")
        self._anim_close.setDuration(280)
        self._anim_close.setStartValue(QPoint(self._end_x, self._end_y))
        self._anim_close.setEndValue(QPoint(self._end_x, screen.bottom() + 10))
        self._anim_close.setEasingCurve(QEasingCurve.InCubic)
        self._anim_close.finished.connect(lambda: (self.close(), callback()))
        self._anim_close.start()

    def _animate_page_turn(self, old_idx, new_idx):
        if self._animating:
            return
        self._animating = True
        w = self._slide_area.width()
        old_page = self._pages[old_idx]
        new_page = self._pages[new_idx]
        new_page.setGeometry(w, 0, w, self._slide_area.height())
        new_page.show()

        self._anim_old = QPropertyAnimation(old_page, b"geometry")
        self._anim_old.setDuration(320)
        self._anim_old.setStartValue(QRect(0, 0, w, self._slide_area.height()))
        self._anim_old.setEndValue(QRect(-w, 0, w, self._slide_area.height()))
        self._anim_old.setEasingCurve(QEasingCurve.InOutCubic)

        self._anim_new = QPropertyAnimation(new_page, b"geometry")
        self._anim_new.setDuration(320)
        self._anim_new.setStartValue(QRect(w, 0, w, self._slide_area.height()))
        self._anim_new.setEndValue(QRect(0, 0, w, self._slide_area.height()))
        self._anim_new.setEasingCurve(QEasingCurve.InOutCubic)

        def on_done():
            old_page.hide()
            old_page.setGeometry(0, 0, w, self._slide_area.height())
            self._animating = False

        self._anim_new.finished.connect(on_done)
        self._anim_old.start()
        self._anim_new.start()

    def _next(self):
        if self._animating:
            return
        old_idx = self._current_index
        if self._current_index == len(_STEP_KEYS) - 1:
            self._slide_out_window(self._finish)
            return
        self._current_index += 1
        self._animate_page_turn(old_idx, self._current_index)
        self._build_dots()
        if self._current_index == len(_STEP_KEYS) - 1:
            self._next_btn.setText(t("tut_finish"))

    def _skip_all(self):
        if not self._animating:
            self._slide_out_window(self._finish)

    def _finish(self):
        storage.mark_tutorial_done()
        if self.on_finished:
            self.on_finished()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPos() - self._drag_pos)
            self._end_x = self.pos().x()
            self._end_y = self.pos().y()


# ================================================================
# TUTORIAL MANAGER
# ================================================================
class TutorialManager:
    def __init__(self, on_finished=None, skip_name=False):
        self.on_finished = on_finished
        self.skip_name   = skip_name

    def start(self):
        if self.skip_name or storage.load_pet_name() is not None:
            self._window = TutorialWindow(on_finished=self._on_finished)
        else:
            self._name_dialog = PetNameDialog(on_name_saved=self._on_name_saved)

    def _on_name_saved(self, name):
        self._window = TutorialWindow(on_finished=self._on_finished)

    def _on_finished(self):
        if self.on_finished:
            self.on_finished()


# ================================================================
# NAME REMINDER BUBBLE
# Shown 10 min after launch if the pet has no name yet.
# ================================================================
class NameReminderBubble(QWidget):
    def __init__(self, on_name_now=None):
        super().__init__()
        self.on_name_now = on_name_now

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(340, 140)

        screen = QApplication.primaryScreen().availableGeometry()
        end_x = screen.right()  - self.width()  - 20
        end_y = screen.bottom() - self.height() - 20

        container = QFrame(self)
        container.setGeometry(0, 0, 340, 140)
        container.setObjectName("bubble")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        text = QLabel(t("bubble_text"))
        text.setWordWrap(True)
        text.setStyleSheet("font-size: 15px; color: white;")
        layout.addWidget(text)

        btn = QPushButton(t("bubble_btn"))
        btn.clicked.connect(self._open_name_dialog)
        layout.addWidget(btn)

        self.setStyleSheet("""
        QFrame#bubble {
            background-color: rgba(40,40,40,230);
            border-radius: 15px;
        }
        QPushButton {
            background-color: #0078D7; color: white;
            border-radius: 8px; padding: 7px; font-size: 14px;
        }
        QPushButton:hover { background-color: #005ea6; }
        """)

        self.move(end_x, screen.bottom() + 10)
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(350)
        self._anim.setStartValue(QPoint(end_x, screen.bottom() + 10))
        self._anim.setEndValue(QPoint(end_x, end_y))
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

        self.show()
        QTimer.singleShot(10000, self.close)

    def _open_name_dialog(self):
        self.close()
        self._name_dialog = PetNameDialog(on_name_saved=self.on_name_now)
