# ================================================================
# ИМПОРТЫ
# ================================================================
import sys
import os
import winreg  # для автозапуска с Windows

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import random
import time
from datetime import date, datetime, timedelta

from PyQt5.QtWidgets import (
    QApplication,
    QLabel, QMessageBox,
    QMenu,
    QSystemTrayIcon, QAction,
)
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QIcon, QTransform

from event_window import EventWindow
from events_manager import load_events
from birthday_manager import (
    BirthdayWindow,
    ToastNotification,
    load_birthdays,
    load_last_check, save_last_check,
    days_word, years_word,
)
from config import load_position, save_position


# ================================================================
# ВЕРСИЯ ПРИЛОЖЕНИЯ
# ================================================================
APP_VERSION = "v10.0"
APP_NAME    = "PetReminder"  # ключ в реестре автозапуска


# ================================================================
# ПУТИ К РЕСУРСАМ
# ================================================================
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    exe_path  = sys.executable  # путь к .exe для автозапуска
else:
    base_path = os.path.abspath(".")
    exe_path  = os.path.abspath(__file__)


# ================================================================
# АВТОЗАПУСК С WINDOWS
# Прописывает путь к exe в реестр HKCU\Software\Microsoft\Windows\
# CurrentVersion\Run. Работает только в собранном .exe.
# ================================================================
def set_autostart(enable=True):
    """
    Включает или отключает автозапуск приложения с Windows.
    enable=True  — добавить в реестр
    enable=False — удалить из реестра
    """
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[autostart] set_autostart: {e}")


def is_autostart_enabled():
    """Проверяет включён ли автозапуск в реестре."""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


# ================================================================
# ПИТОМЕЦ
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

        # Живые тосты — храним ссылки чтобы Qt не удалял раньше времени
        self._toasts = []

        # Активные singleShot таймеры событий (для пересоздания при изменениях)
        self._event_timers = []

        # Текущее направление: True = оригинал (вправо), False = зеркал (влево)
        self._facing_right = True

        # --------------------------------------------------------
        # ТРЕЙ-ИКОНКА И МЕНЮ
        # --------------------------------------------------------
        self.tray = QSystemTrayIcon(self)

        icon_path = os.path.join(base_path, "icon.ico")
        if os.path.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))
            self.tray.setToolTip("")
            QTimer.singleShot(0, lambda: self.tray.setToolTip(f"Pet Reminder {APP_VERSION}"))

        self.tray_menu = QMenu()

        show_action      = QAction("🐾 Показать зверька", self)
        hide_action      = QAction("📥 Скрыть в трей", self)
        birthdays_action = QAction("🎂 Дни рождения", self)
        nearest_action   = QAction("🔔 Показать ближайший ДР", self)
        events_action    = QAction("🗓 События", self)
        self.autostart_action = QAction("", self)  # текст устанавливается ниже
        version_action   = QAction(f"Версия: {APP_VERSION}", self)
        version_action.setEnabled(False)
        exit_action      = QAction("❌ Выход", self)

        self._update_autostart_label()

        self.tray_menu.addAction(show_action)
        self.tray_menu.addAction(hide_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(birthdays_action)
        self.tray_menu.addAction(nearest_action)
        self.tray_menu.addAction(events_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.autostart_action)
        self.tray_menu.addAction(version_action)
        self.tray_menu.addAction(exit_action)

        show_action.triggered.connect(self.show)
        hide_action.triggered.connect(self.hide)
        birthdays_action.triggered.connect(self.open_birthday_window)
        events_action.triggered.connect(self.open_events_window)
        nearest_action.triggered.connect(self.check_birthdays)
        self.autostart_action.triggered.connect(self.toggle_autostart)
        exit_action.triggered.connect(QApplication.quit)

        self.tray.setContextMenu(self.tray_menu)
        self.tray.show()

        # --------------------------------------------------------
        # СОСТОЯНИЕ МЫШИ
        # --------------------------------------------------------
        self.dragging = False
        self.moved    = False
        self.offset   = QPoint()

        # --------------------------------------------------------
        # ЗАГРУЗКА КАДРОВ
        # --------------------------------------------------------
        self.idle_frames  = self.load_frames("idle_clean")
        self.click_frames = self.load_frames("click_clean")
        self.sleep_frames = self.load_frames("sleeping_clean")

        if not self.idle_frames:
            QMessageBox.critical(
                None, "Ошибка",
                "Не найдены кадры idle_clean.\nПроверь сборку PyInstaller."
            )
            sys.exit(1)

        self.current_frames = self.idle_frames
        self.frame_index    = 0
        self.playing_click  = False
        self.sleeping       = False

        self.last_interaction_time = time.time()
        self.sleep_after = 10

        first = self.idle_frames[0]
        self.setPixmap(first)
        self.resize(first.size())

        # --------------------------------------------------------
        # ВОССТАНОВЛЕНИЕ ПОЗИЦИИ
        # --------------------------------------------------------
        x, y = load_position()
        if x is not None and y is not None:
            # Проверяем что сохранённая позиция ещё в пределах экрана
            x, y = self.clamp_to_screen(x, y)
            self.move(x, y)
        else:
            # Первый запуск — правый нижний угол
            screen = self.screen_rect()
            self.move(
                screen.right() - first.width() - 20,
                screen.bottom() - first.height() - 20
            )

        # Обновляем направление по начальной позиции
        self.update_direction()

        # --------------------------------------------------------
        # ТАЙМЕРЫ
        # --------------------------------------------------------
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.update_frame)
        self.anim_timer.start(33)

        self.behavior_timer = QTimer()
        self.behavior_timer.timeout.connect(self.random_behavior)
        self.behavior_timer.start(random.randint(3000, 6000))

        # --------------------------------------------------------
        # УВЕДОМЛЕНИЯ И СОБЫТИЯ
        # --------------------------------------------------------
        self.check_birthdays()
        self.schedule_event_reminders()

        self.show()

    def closeEvent(self, event):
        """При закрытии окна — завершаем процесс (позиция сохраняется через aboutToQuit)."""
        QApplication.quit()
        sys.exit(0)

    # ----------------------------------------------------------------
    # АВТОЗАПУСК
    # ----------------------------------------------------------------
    def _update_autostart_label(self):
        """Обновляет текст пункта меню автозапуска по текущему состоянию."""
        if is_autostart_enabled():
            self.autostart_action.setText("✅ Автозапуск включён")
        else:
            self.autostart_action.setText("⬜ Автозапуск выключен")

    def toggle_autostart(self):
        """Переключает автозапуск и обновляет пункт меню."""
        enable = not is_autostart_enabled()
        set_autostart(enable)
        self._update_autostart_label()

    # ----------------------------------------------------------------
    # ЭКРАН
    # ----------------------------------------------------------------
    def screen_rect(self):
        """Доступная область рабочего стола (без таскбара)."""
        return QApplication.primaryScreen().availableGeometry()

    def screen_mid_x(self):
        """X середины экрана — граница между левой и правой зонами."""
        return self.screen_rect().width() // 2

    def clamp_to_screen(self, x, y):
        """Ограничивает позицию питомца в пределах рабочего стола."""
        rect = self.screen_rect()
        x = max(rect.left(), min(x, rect.right()  - self.width()))
        y = max(rect.top(),  min(y, rect.bottom() - self.height()))
        return x, y

    # ----------------------------------------------------------------
    # ПОЗИЦИЯ
    # ----------------------------------------------------------------
    def _save_current_position(self):
        """Сохраняет текущую позицию питомца в файл."""
        save_position(self.pos().x(), self.pos().y())

    # ----------------------------------------------------------------
    # ЗАГРУЗКА КАДРОВ
    # ----------------------------------------------------------------
    def load_frames(self, folder):
        """Загружает PNG-кадры из папки. Возвращает список QPixmap."""
        frames = []
        folder_path = os.path.join(base_path, folder)

        if not os.path.exists(folder_path):
            print(f"[Pet] load_frames: папка не найдена — {folder_path}")
            return frames

        files = sorted(f for f in os.listdir(folder_path) if f.endswith(".png"))
        for file in files:
            frames.append(QPixmap(os.path.join(folder_path, file)))

        return frames

    def mirror_frame(self, pixmap):
        """Зеркалит QPixmap по горизонтали (для поворота влево)."""
        return pixmap.transformed(QTransform().scale(-1, 1))

    # ----------------------------------------------------------------
    # НАПРАВЛЕНИЕ
    # ----------------------------------------------------------------
    def update_direction(self):
        """
        Определяет направление взгляда по положению питомца.
        Правая половина экрана → оригинал (вправо).
        Левая половина экрана  → зеркал  (влево).
        """
        pet_center_x = self.pos().x() + self.width() // 2
        facing_right = pet_center_x >= self.screen_mid_x()

        if facing_right != self._facing_right:
            self._facing_right = facing_right
            self.frame_index = 0  # сброс чтобы не было рывка

    def get_frame(self, pixmap):
        """Возвращает кадр с учётом текущего направления."""
        return pixmap if self._facing_right else self.mirror_frame(pixmap)

    # ----------------------------------------------------------------
    # АНИМАЦИЯ
    # ----------------------------------------------------------------
    def update_frame(self):
        """Переключает кадр анимации (~30 fps). Применяет зеркалирование."""
        if not self.current_frames:
            return

        if not self.sleeping and time.time() - self.last_interaction_time > self.sleep_after:
            self.start_sleep()

        pixmap = self.current_frames[self.frame_index]
        self.setPixmap(self.get_frame(pixmap))
        self.resize(pixmap.size())

        self.frame_index += 1
        if self.frame_index >= len(self.current_frames):
            self.frame_index = 0
            if self.playing_click:
                self.playing_click  = False
                self.current_frames = self.idle_frames

    def random_behavior(self):
        """С вероятностью 30% оживляет питомца."""
        if not self.sleeping and random.random() < 0.3:
            self.start_click_animation()
        self.behavior_timer.start(random.randint(3000, 6000))

    def start_click_animation(self):
        if self.click_frames:
            self.current_frames = self.click_frames
            self.frame_index    = 0
            self.playing_click  = True
            self.sleeping       = False

    def start_sleep(self):
        if self.sleep_frames:
            self.current_frames = self.sleep_frames
            self.frame_index    = 0
            self.sleeping       = True
            self.playing_click  = False

    def wake_up(self):
        self.sleeping       = False
        self.current_frames = self.idle_frames
        self.frame_index    = 0

    # ----------------------------------------------------------------
    # МЫШЬ
    # ----------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.moved    = False
            self.offset   = event.globalPos() - self.pos()
            self.last_interaction_time = time.time()
            if self.sleeping:
                self.wake_up()

    def mouseMoveEvent(self, event):
        """Перемещение с ограничением по краям и обновлением направления."""
        if self.dragging:
            self.moved   = True
            new_pos      = event.globalPos() - self.offset
            x, y         = self.clamp_to_screen(new_pos.x(), new_pos.y())
            self.move(x, y)
            self.update_direction()

    def mouseReleaseEvent(self, event):
        if not self.moved:
            self.start_click_animation()
        self.dragging = False

    # ----------------------------------------------------------------
    # ДНИ РОЖДЕНИЯ
    # ----------------------------------------------------------------
    def check_birthdays(self):
        """
        Проверяет ДР и показывает тост если осталось 3 или 7 дней.
        При запуске — только первый раз за день.
        Из трея — всегда.
        """
        today     = date.today()
        today_str = today.strftime("%Y-%m-%d")

        last_check      = load_last_check()
        already_checked = last_check.get("date") == today_str

        birthdays = load_birthdays()
        messages  = []

        for b in birthdays:
            try:
                next_birthday = date(today.year, int(b["month"]), int(b["day"]))
                if next_birthday < today:
                    next_birthday = date(today.year + 1, int(b["month"]), int(b["day"]))

                days_left = (next_birthday - today).days

                if days_left in (3, 7):
                    age = next_birthday.year - int(b["year"])
                    messages.append(
                        f"📅 {b['name']}\n"
                        f"Через {days_left} {days_word(days_left)}\n"
                        f"Исполнится {age} {years_word(age)}"
                    )

            except Exception as e:
                print(f"[Pet] check_birthdays: {e}")
                continue

        if messages:
            toast = ToastNotification(
                "\n\n".join(messages),
                color="rgba(40, 40, 40, 230)",
                offset_y=20
            )
            self._toasts.append(toast)

        if not already_checked:
            save_last_check({"date": today_str})

    # ----------------------------------------------------------------
    # СОБЫТИЯ — таймеры напоминаний
    # ----------------------------------------------------------------
    def schedule_event_reminders(self):
        """
        Перебирает все события и взводит QTimer.singleShot для каждого.
        Учитывает повторяющиеся события: находит ближайшее вхождение
        в будущем и ставит таймер на него.
        Вызывается при старте и после любого изменения событий.
        """
        # Отменяем старые таймеры (останавливаем QTimer-обёртки если есть)
        self._event_timers.clear()

        now    = datetime.now()
        events = load_events()

        for e in events:
            try:
                remind_before = int(e.get("remind_before_minutes", 0))
                repeat        = e.get("repeat", "Без повтора")

                # Базовое время события
                base_dt = datetime(
                    int(e["year"]), int(e["month"]), int(e["day"]),
                    int(e.get("hour", 0)), int(e.get("minute", 0))
                )

                # Находим ближайшее будущее вхождение события
                remind_dt = self._next_remind_dt(base_dt, remind_before, repeat, now)

                if remind_dt is None:
                    continue  # прошлое событие без повтора

                ms_left = int((remind_dt - now).total_seconds() * 1000)
                if ms_left <= 0:
                    continue

                title  = e["title"]
                hour   = int(e.get("hour", 0))
                minute = int(e.get("minute", 0))

                def make_callback(t, h, m, rb, rep, base):
                    def callback():
                        # Показываем тост
                        if rb > 0:
                            h2, m2 = divmod(rb, 60)
                            if h2 > 0 and m2 > 0:
                                remind_str = f"через {h2}ч {m2}мин"
                            elif h2 > 0:
                                remind_str = f"через {h2}ч"
                            else:
                                remind_str = f"через {m2}мин"
                            text = f"🗓 {t}\nНачало в {h:02d}:{m:02d}\n({remind_str})"
                        else:
                            text = f"🗓 {t}\nНачинается сейчас!"

                        toast = ToastNotification(
                            text,
                            color="rgba(30, 90, 160, 230)",
                            offset_y=160
                        )
                        self._toasts.append(toast)

                        # Если событие повторяющееся — взводим следующий таймер
                        if rep != "Без повтора":
                            self._reschedule_one(t, h, m, rb, rep, base)

                    return callback

                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(make_callback(title, hour, minute, remind_before, repeat, base_dt))
                timer.start(ms_left)
                self._event_timers.append(timer)

            except Exception as e:
                print(f"[Pet] schedule_event_reminders: {e}")
                continue

    def _next_remind_dt(self, base_dt, remind_before, repeat, now):
        """
        Вычисляет ближайший момент напоминания для события.
        Для повторяющихся — находит следующее вхождение после now.
        Возвращает datetime или None если событие в прошлом и без повтора.
        """
        remind_dt = base_dt - timedelta(minutes=remind_before)

        if repeat == "Без повтора":
            return remind_dt if remind_dt > now else None

        # Для повторяющихся — прокручиваем вперёд пока не найдём будущее
        dt = remind_dt
        while dt <= now:
            if repeat == "Каждый день":
                dt += timedelta(days=1)
            elif repeat == "Каждую неделю":
                dt += timedelta(weeks=1)
            elif repeat == "Каждый месяц":
                # Добавляем месяц (с учётом разного кол-ва дней)
                month = dt.month + 1 if dt.month < 12 else 1
                year  = dt.year if dt.month < 12 else dt.year + 1
                day   = min(dt.day, [31,28,31,30,31,30,31,31,30,31,30,31][month-1])
                dt    = dt.replace(year=year, month=month, day=day)
            elif repeat == "Каждый год":
                dt = dt.replace(year=dt.year + 1)

        return dt

    def _reschedule_one(self, title, hour, minute, remind_before, repeat, base_dt):
        """
        Взводит следующий таймер для повторяющегося события
        после того как текущий сработал.
        """
        now       = datetime.now()
        remind_dt = self._next_remind_dt(base_dt, remind_before, repeat, now)

        if remind_dt is None:
            return

        ms_left = int((remind_dt - now).total_seconds() * 1000)
        if ms_left <= 0:
            return

        def make_callback(t, h, m, rb, rep, base):
            def callback():
                if rb > 0:
                    h2, m2 = divmod(rb, 60)
                    if h2 > 0 and m2 > 0:
                        remind_str = f"через {h2}ч {m2}мин"
                    elif h2 > 0:
                        remind_str = f"через {h2}ч"
                    else:
                        remind_str = f"через {m2}мин"
                    text = f"🗓 {t}\nНачало в {h:02d}:{m:02d}\n({remind_str})"
                else:
                    text = f"🗓 {t}\nНачинается сейчас!"

                toast = ToastNotification(
                    text,
                    color="rgba(30, 90, 160, 230)",
                    offset_y=160
                )
                self._toasts.append(toast)

                if rep != "Без повтора":
                    self._reschedule_one(t, h, m, rb, rep, base)

            return callback

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(make_callback(title, hour, minute, remind_before, repeat, base_dt))
        timer.start(ms_left)
        self._event_timers.append(timer)

    # ----------------------------------------------------------------
    # ОТКРЫТИЕ ОКОН
    # ----------------------------------------------------------------
    def open_birthday_window(self):
        """Открывает окно управления днями рождения."""
        self.birthday_window = BirthdayWindow()
        self.birthday_window.show()

    def open_events_window(self):
        """
        Открывает окно событий. Передаёт колбэк schedule_event_reminders
        чтобы таймеры пересоздавались сразу после изменений.
        """
        self.events_window = EventWindow(
            on_events_changed=self.schedule_event_reminders
        )
        self.events_window.show()


# ================================================================
# ТОЧКА ВХОДА
# ================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pet = Pet()
    # Сохраняем позицию при любом способе выхода (трей, closeEvent, etc.)
    app.aboutToQuit.connect(pet._save_current_position)
    sys.exit(app.exec_())
