# ================================================================
# PET  —  entry point
# The Pet widget is intentionally thin: it wires together the
# modules (animation, tray, reminders, chat, tutorial) and handles
# only mouse events and screen geometry.
# ================================================================

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QLabel, QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt, QTimer, QPoint, QProcess
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
from updater import UpdateManager


# ----------------------------------------------------------------
# Resource path (works both from source and PyInstaller .exe)
# ----------------------------------------------------------------
if getattr(sys, "frozen", False):
    BASE_PATH = sys._MEIPASS
    EXE_PATH  = sys.executable
else:
    # Resolve resources relative to this file, not to the IDE's
    # current working directory.
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    EXE_PATH  = os.path.abspath(__file__)


# ================================================================
# PET WIDGET
# ================================================================
class Pet(QLabel):

    def __init__(self):
        super().__init__()
        self._shutting_down = False

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
            on_updates  = self._check_updates_manual,
            on_quit     = self._shutdown,
        )

        # The updater checks GitHub in a worker thread so the pet remains
        # responsive even when the network is unavailable.
        self._updater = UpdateManager(self)
        self._updater.update_available.connect(self._on_update_available)
        self._updater.no_update.connect(self._on_no_update)
        self._updater.check_failed.connect(self._on_update_check_failed)
        self._updater.download_progress.connect(self._on_update_progress)
        self._updater.download_ready.connect(self._on_update_ready)
        self._updater.download_failed.connect(self._on_update_download_failed)
        self._update_progress = None
        self._manual_update_check = False

        # --------------------------------------------------------
        # Reminders
        # --------------------------------------------------------
        self._reminders = ReminderScheduler(
            self._toasts,
            parent=self,
            notify=self._tray.show_notification,
        )
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

        # Give the application time to finish its first-run UI before doing
        # a quiet background check for a newer GitHub Release.
        QTimer.singleShot(15_000, self._check_updates_automatic)

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
    # Updates
    # ----------------------------------------------------------------
    def _check_updates_automatic(self):
        if not self._shutting_down:
            self._manual_update_check = False
            self._updater.check()

    def _check_updates_manual(self):
        if self._shutting_down:
            return
        self._manual_update_check = True
        self._updater.check()

    def _on_no_update(self):
        if self._manual_update_check and not self._shutting_down:
            QMessageBox.information(self, t("app_name"), t("update_latest"))

    def _on_update_check_failed(self, _reason):
        if self._manual_update_check and not self._shutting_down:
            QMessageBox.warning(self, t("app_name"), t("update_error"))

    def _on_update_available(self, info):
        if self._shutting_down:
            return
        answer = QMessageBox.question(
            self,
            t("app_name"),
            t("update_available", version=info.version),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer != QMessageBox.Yes:
            return

        progress = QProgressDialog(
            t("update_download"),
            t("update_cancel"),
            0,
            100,
            self,
        )
        progress.setWindowTitle(t("app_name"))
        progress.setWindowModality(Qt.WindowModal)
        progress.setAutoClose(False)
        progress.setMinimumDuration(0)
        progress.canceled.connect(self._updater.cancel_download)
        self._update_progress = progress
        progress.show()
        if not self._updater.download(info):
            progress.close()
            progress.deleteLater()
            self._update_progress = None

    def _on_update_progress(self, value):
        if self._update_progress is not None:
            self._update_progress.setValue(value)

    def _close_update_progress(self):
        if self._update_progress is None:
            return
        self._update_progress.close()
        self._update_progress.deleteLater()
        self._update_progress = None

    def _on_update_download_failed(self, reason):
        self._close_update_progress()
        if self._shutting_down or reason == "cancelled":
            return
        key = "update_checksum_error" if reason in {
            "checksum_missing", "checksum_mismatch", "invalid_checksum"
        } else "update_download_error"
        QMessageBox.warning(self, t("app_name"), t(key))

    def _on_update_ready(self, installer_path):
        self._close_update_progress()
        if self._shutting_down:
            return
        QMessageBox.information(self, t("app_name"), t("update_ready"))
        if not QProcess.startDetached(installer_path, []):
            QMessageBox.warning(self, t("app_name"), t("update_install_error"))
            return
        QTimer.singleShot(100, self._shutdown)

    # ----------------------------------------------------------------
    # Lifecycle
    # ----------------------------------------------------------------
    def _save_position(self):
        save_position(self.pos().x(), self.pos().y())

    def _prepare_shutdown(self):
        """Release every active resource before the Qt loop is stopped."""
        if self._shutting_down:
            return
        self._shutting_down = True

        if hasattr(self, "_anim_timer"):
            self._anim_timer.stop()
        if hasattr(self, "_behavior_timer"):
            self._behavior_timer.stop()
        if hasattr(self, "_reminders"):
            self._reminders.stop()
        if hasattr(self, "_updater"):
            self._updater.shutdown()
        self._close_update_progress()

        chat = getattr(self, "_chat_window", None)
        if chat is not None:
            if hasattr(chat, "shutdown_for_app"):
                chat.shutdown_for_app()
            else:
                chat.close()
            self._chat_window = None

        for attr in ("_events_window", "_rename_dialog", "_name_bubble"):
            window = getattr(self, attr, None)
            if window is not None:
                window.close()
                setattr(self, attr, None)

        tutorial = getattr(self, "_tutorial", None)
        if tutorial is not None:
            for attr in ("_window", "_name_dialog"):
                window = getattr(tutorial, attr, None)
                if window is None:
                    continue
                if hasattr(window, "force_close"):
                    window.force_close()
                else:
                    window.close()

        for toast in self._toasts:
            toast.close()
        self._toasts.clear()

        if hasattr(self, "_tray"):
            self._tray.shutdown()
        self.hide()

    def _shutdown(self):
        """Stop the application completely from the tray or the widget."""
        self._prepare_shutdown()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def closeEvent(self, event):
        self._shutdown()
        event.accept()


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pet = Pet()
    app.aboutToQuit.connect(pet._save_position)
    app.aboutToQuit.connect(pet._prepare_shutdown)
    sys.exit(app.exec_())
