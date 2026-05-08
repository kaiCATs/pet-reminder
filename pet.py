# ================================================================
# PET  —  entry point
# The Pet widget is intentionally thin: it wires together the
# modules (animation, tray, reminders, chat, tutorial) and handles
# only mouse events and screen geometry.
# ================================================================

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QLabel, QMessageBox
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap

import storage
from storage import (
    load_position, save_position,
    is_first_launch, has_pet_name, is_tutorial_done,
)
from animation import AnimationController, load_frames
from autostart import is_autostart_enabled
from tray import TrayManager, APP_VERSION
from reminders import ReminderScheduler
from event_window import EventWindow
from tutorial import TutorialManager, NameReminderBubble, PetNameDialog
from chat_window import ChatWindow
from locale_app import t


# ----------------------------------------------------------------
# Resource path (works both from source and PyInstaller .exe)
# ----------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_PATH = sys._MEIPASS
    EXE_PATH  = sys.executable
else:
    BASE_PATH = os.path.abspath(".")
    EXE_PATH  = os.path.abspath(__file__)


# ================================================================
# PET WIDGET
# ================================================================
class Pet(QLabel):

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Migrate any old JSON files to app_state.json on first run
        storage.migrate_legacy()

        # References kept alive so Qt doesn't GC them
        self._toasts      = []
        self._chat_window = None

        # --------------------------------------------------------
        # Load animation frames
        # --------------------------------------------------------
        idle_frames  = load_frames(BASE_PATH, "idle_clean")
        click_frames = load_frames(BASE_PATH, "click_clean")
        sleep_frames = load_frames(BASE_PATH, "sleeping_clean")

        if not idle_frames:
            QMessageBox.critical(None, "Error", t("err_no_frames"))
            sys.exit(1)

        self._anim = AnimationController(idle_frames, click_frames, sleep_frames)

        first = idle_frames[0]
        self.setPixmap(first)
        self.resize(first.size())

        # --------------------------------------------------------
        # Position
        # --------------------------------------------------------
        x, y = load_position()
        if x is not None:
            x, y = self._clamp(x, y)
            self.move(x, y)
        else:
            r = self._screen()
            self.move(r.right() - first.width() - 20,
                      r.bottom() - first.height() - 20)

        self._anim.update_direction(
            self.pos().x() + self.width() // 2,
            self._screen().width() // 2
        )

        # --------------------------------------------------------
        # Tray
        # --------------------------------------------------------
        icon_path = os.path.join(BASE_PATH, "icon.ico")
        self._tray = TrayManager(
            icon_path   = icon_path,
            exe_path    = EXE_PATH,
            parent      = self,
            on_show     = self.show,
            on_hide     = self.hide,
            on_events   = self._open_events,
            on_tutorial = self._open_tutorial,
            on_rename   = self._open_rename,
            on_quit     = QApplication.quit,
        )

        # --------------------------------------------------------
        # Reminders
        # --------------------------------------------------------
        self._reminders = ReminderScheduler(self._toasts, parent=self)
        self._reminders.schedule_all()

        # --------------------------------------------------------
        # Timers
        # --------------------------------------------------------
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(33)  # ~30 fps

        self._behavior_timer = QTimer(self)
        self._behavior_timer.timeout.connect(self._random_behavior)
        self._behavior_timer.start(3000)

        # --------------------------------------------------------
        # Mouse state
        # --------------------------------------------------------
        self._dragging = False
        self._moved    = False
        self._offset   = QPoint()

        self.show()

        # --------------------------------------------------------
        # Tutorial / name
        # --------------------------------------------------------
        if is_first_launch() and not is_tutorial_done():
            QTimer.singleShot(500, self._start_tutorial)
        elif not has_pet_name():
            QTimer.singleShot(600_000, self._remind_name)

    # ----------------------------------------------------------------
    # Screen helpers
    # ----------------------------------------------------------------
    def _screen(self):
        return QApplication.primaryScreen().availableGeometry()

    def _clamp(self, x, y):
        r = self._screen()
        x = max(r.left(), min(x, r.right()  - self.width()))
        y = max(r.top(),  min(y, r.bottom() - self.height()))
        return x, y

    # ----------------------------------------------------------------
    # Animation tick
    # ----------------------------------------------------------------
    def _tick(self):
        px = self._anim.tick()
        if px:
            self.setPixmap(px)
            self.resize(px.size())

    def _random_behavior(self):
        interval = self._anim.random_behavior()
        self._behavior_timer.start(interval)

    # ----------------------------------------------------------------
    # Mouse events
    # ----------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._moved    = False
            self._offset   = event.globalPos() - self.pos()
            self._anim.poke()
            if self._anim.sleeping:
                self._anim.wake_up()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._moved = True
            new_pos     = event.globalPos() - self._offset
            x, y        = self._clamp(new_pos.x(), new_pos.y())
            self.move(x, y)
            self._anim.update_direction(
                x + self.width() // 2,
                self._screen().width() // 2
            )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.RightButton:
            self._toggle_chat()
            return
        if not self._moved:
            self._anim.play_click()
        self._dragging = False

    # ----------------------------------------------------------------
    # Windows
    # ----------------------------------------------------------------
    def _open_events(self):
        self._events_window = EventWindow(
            on_events_changed=self._reminders.schedule_all
        )
        self._events_window.show()

    def _toggle_chat(self):
        if self._chat_window and self._chat_window.isVisible():
            self._chat_window._on_close()
            self._chat_window = None
            return

        self._chat_window = ChatWindow(
            on_events_changed=self._reminders.schedule_all
        )
        r      = self._screen()
        px, py = self.pos().x(), self.pos().y()
        cw, ch = self._chat_window.width(), self._chat_window.height()
        x = (px + self.width() + 10
             if px + self.width() + cw + 10 < r.right()
             else px - cw - 10)
        y = max(r.top(), min(py, r.bottom() - ch))
        self._chat_window.move(x, y)
        self._chat_window.show()

    # ----------------------------------------------------------------
    # Tutorial / rename
    # ----------------------------------------------------------------
    def _start_tutorial(self):
        self._tutorial = TutorialManager(on_finished=self._on_tutorial_finished)
        self._tutorial.start()

    def _on_tutorial_finished(self):
        if not has_pet_name():
            QTimer.singleShot(600_000, self._remind_name)

    def _open_tutorial(self):
        self._tutorial = TutorialManager(skip_name=True)
        self._tutorial.start()

    def _open_rename(self):
        self._rename_dialog = PetNameDialog(on_name_saved=lambda name: None)
        self._rename_dialog.closeEvent = lambda event: event.accept()

    def _remind_name(self):
        if not has_pet_name():
            self._name_bubble = NameReminderBubble(on_name_now=lambda name: None)

    # ----------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------
    def _save_position(self):
        save_position(self.pos().x(), self.pos().y())

    def closeEvent(self, event):
        QApplication.quit()
        sys.exit(0)


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pet = Pet()
    app.aboutToQuit.connect(pet._save_position)
    sys.exit(app.exec_())
