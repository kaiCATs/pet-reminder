# ================================================================
# TRAY
# System tray icon and context menu.
# All labels come from locale.t() so they update with language.
# ================================================================

import os

from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtGui import QIcon

import storage
from autostart import is_autostart_enabled, set_autostart
from locale_app import t
from app_version import APP_VERSION as APP_VERSION_NUMBER

APP_VERSION = f"v{APP_VERSION_NUMBER}"


class TrayManager:
    """
    Creates and manages the system tray icon and menu.

    Callbacks passed in __init__:
      on_show        — show the pet widget
      on_hide        — hide the pet widget
      on_events      — open EventWindow
      on_tutorial    — open Tutorial
      on_rename      — open rename dialog
      on_updates     — check GitHub Releases for a newer version
      on_quit        — quit application
    """

    def __init__(self, icon_path: str, exe_path: str, parent,
                 on_show, on_hide, on_events, on_tutorial, on_rename,
                 on_updates, on_quit):
        self._exe_path = exe_path
        self._parent   = parent

        self.tray = QSystemTrayIcon(parent)
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))
        self.tray.setToolTip(f"Pet Reminder {APP_VERSION}")

        self._on_show     = on_show
        self._on_hide     = on_hide
        self._on_events   = on_events
        self._on_tutorial = on_tutorial
        self._on_rename   = on_rename
        self._on_updates  = on_updates
        self._on_quit     = on_quit

        self._build_menu()
        self.tray.show()

    # ----------------------------------------------------------------
    def _build_menu(self):
        menu = QMenu()

        self._act_show     = QAction(t("tray_show"),    self._parent)
        self._act_hide     = QAction(t("tray_hide"),    self._parent)
        self._act_events   = QAction(t("tray_events"),  self._parent)
        self._act_notifications = QAction("", self._parent)
        self._act_backup   = QAction(t("tray_backup"),   self._parent)
        self._act_auto     = QAction("",                self._parent)
        self._act_updates  = QAction(t("tray_updates"), self._parent)
        self._act_tutorial = QAction(t("tray_tutorial"),self._parent)
        self._act_rename   = QAction(t("tray_rename"),  self._parent)
        self._act_lang     = QAction(t("tray_lang"),    self._parent)
        self._act_version  = QAction(t("tray_version", v=APP_VERSION), self._parent)
        self._act_exit     = QAction(t("tray_exit"),    self._parent)

        self._act_version.setEnabled(False)
        self._update_autostart_label()
        self._update_notifications_label()

        menu.addAction(self._act_show)
        menu.addAction(self._act_hide)
        menu.addSeparator()
        menu.addAction(self._act_events)
        menu.addSeparator()
        menu.addAction(self._act_notifications)
        menu.addAction(self._act_backup)
        menu.addSeparator()
        menu.addAction(self._act_auto)
        menu.addAction(self._act_updates)
        menu.addAction(self._act_tutorial)
        menu.addAction(self._act_rename)
        menu.addAction(self._act_lang)
        menu.addAction(self._act_version)
        menu.addAction(self._act_exit)

        self._act_show.triggered.connect(self._on_show)
        self._act_hide.triggered.connect(self._on_hide)
        self._act_events.triggered.connect(self._on_events)
        self._act_notifications.triggered.connect(self._toggle_notifications)
        self._act_backup.triggered.connect(self._create_backup)
        self._act_auto.triggered.connect(self._toggle_autostart)
        self._act_updates.triggered.connect(self._on_updates)
        self._act_tutorial.triggered.connect(self._on_tutorial)
        self._act_rename.triggered.connect(self._on_rename)
        self._act_lang.triggered.connect(self._toggle_language)
        self._act_exit.triggered.connect(self._on_quit)

        self.tray.setContextMenu(menu)

    def _update_autostart_label(self):
        key = "tray_autostart_on" if is_autostart_enabled() else "tray_autostart_off"
        self._act_auto.setText(t(key))

    def _toggle_autostart(self):
        set_autostart(self._exe_path, not is_autostart_enabled())
        self._update_autostart_label()

    def _update_notifications_label(self):
        key = "tray_notifications_on" if storage.notifications_enabled() else "tray_notifications_off"
        self._act_notifications.setText(t(key))

    def _toggle_notifications(self):
        storage.set_notifications_enabled(not storage.notifications_enabled())
        self._update_notifications_label()

    def _create_backup(self):
        try:
            storage.create_backup()
            self.tray.showMessage(
                t("app_name"), t("tray_backup_done"),
                QSystemTrayIcon.Information, 5000,
            )
        except Exception:
            self.tray.showMessage(
                t("app_name"), t("tray_backup_error"),
                QSystemTrayIcon.Critical, 5000,
            )

    def show_notification(self, title: str, message: str) -> bool:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return False
        self.tray.showMessage(
            title, message, QSystemTrayIcon.Information, 10000
        )
        return True

    def shutdown(self):
        """Remove the tray icon before the Qt event loop is stopped."""
        if self.tray is None:
            return
        self.tray.hide()
        self.tray.setContextMenu(None)
        self.tray.deleteLater()
        self.tray = None

    def _rebuild_labels(self):
        """Refresh all menu text after language switch."""
        self._act_show.setText(t("tray_show"))
        self._act_hide.setText(t("tray_hide"))
        self._act_events.setText(t("tray_events"))
        self._update_notifications_label()
        self._act_backup.setText(t("tray_backup"))
        self._act_updates.setText(t("tray_updates"))
        self._act_tutorial.setText(t("tray_tutorial"))
        self._act_rename.setText(t("tray_rename"))
        self._act_lang.setText(t("tray_lang"))
        self._act_version.setText(t("tray_version", v=APP_VERSION))
        self._act_exit.setText(t("tray_exit"))
        self._update_autostart_label()

    def _toggle_language(self):
        storage.toggle_language()
        self._rebuild_labels()
