# ================================================================
# REMINDERS
# Schedules QTimer instances for upcoming events.
# Called on startup and after any event change.
# ================================================================

from datetime import datetime, timedelta

from PyQt5.QtCore import QTimer

from events_manager import load_events
from birthday_manager import ToastNotification
from locale_app import t


def _delta_string(remind_before: int) -> str:
    """Format remind_before minutes into a human-readable delta string."""
    if remind_before <= 0:
        return ""
    h, m = divmod(remind_before, 60)
    if h > 0 and m > 0:
        return t("toast_delta_hm", h=h, m=m)
    if h > 0:
        return t("toast_delta_h", h=h)
    return t("toast_delta_m", m=m)


def _next_remind_dt(base_dt: datetime, remind_before: int, repeat: str,
                    now: datetime):
    """
    Return the nearest future reminder datetime for an event.
    Returns None if the event is in the past and has no repeat.
    """
    remind_dt = base_dt - timedelta(minutes=remind_before)

    if repeat == "no_repeat":
        return remind_dt if remind_dt > now else None

    dt = remind_dt
    while dt <= now:
        if repeat == "every_day":
            dt += timedelta(days=1)
        elif repeat == "every_week":
            dt += timedelta(weeks=1)
        elif repeat == "every_month":
            month = dt.month % 12 + 1
            year  = dt.year + (1 if dt.month == 12 else 0)
            day   = min(dt.day, [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            dt    = dt.replace(year=year, month=month, day=day)
        elif repeat == "every_year":
            dt = dt.replace(year=dt.year + 1)
    return dt


class ReminderScheduler:
    """
    Holds all active QTimer references and rebuilds them on demand.
    Pass a list (toast_refs) owned by Pet so Qt doesn't GC the toasts.
    """

    def __init__(self, toast_refs: list, parent=None):
        self._timers    = []
        self._toasts    = toast_refs
        self._parent    = parent  # QObject parent for QTimer

    def schedule_all(self):
        """Cancel existing timers and set new ones for all events."""
        self._timers.clear()

        now    = datetime.now()
        events = load_events()

        for e in events:
            try:
                remind_before = int(e.get("remind_before_minutes", 0))
                repeat        = e.get("repeat", "no_repeat")

                base_dt = datetime(
                    int(e["year"]), int(e["month"]), int(e["day"]),
                    int(e.get("hour", 0)), int(e.get("minute", 0))
                )

                remind_dt = _next_remind_dt(base_dt, remind_before, repeat, now)
                if remind_dt is None:
                    continue

                ms_left = int((remind_dt - now).total_seconds() * 1000)
                if ms_left <= 0:
                    continue

                timer = QTimer(self._parent)
                timer.setSingleShot(True)
                timer.timeout.connect(
                    self._make_callback(
                        e["title"],
                        int(e.get("hour", 0)),
                        int(e.get("minute", 0)),
                        remind_before,
                        repeat,
                        base_dt,
                    )
                )
                timer.start(ms_left)
                self._timers.append(timer)

            except Exception as ex:
                print(f"[reminders] schedule_all: {ex}")

    # ----------------------------------------------------------------
    def _make_callback(self, title, hour, minute, remind_before, repeat, base_dt):
        def callback():
            time_str = f"{hour:02d}:{minute:02d}"
            delta    = _delta_string(remind_before)

            if delta:
                body = f"🗓 {title}\n{t('toast_event_at', time=time_str)}\n({delta})"
            else:
                body = f"🗓 {title}\n{t('toast_event_now')}"

            toast = ToastNotification(body, color="rgba(30, 90, 160, 230)", offset_y=160)
            self._toasts.append(toast)

            if repeat != "no_repeat":
                self._reschedule_one(title, hour, minute, remind_before, repeat, base_dt)

        return callback

    def _reschedule_one(self, title, hour, minute, remind_before, repeat, base_dt):
        now       = datetime.now()
        remind_dt = _next_remind_dt(base_dt, remind_before, repeat, now)
        if remind_dt is None:
            return
        ms_left = int((remind_dt - now).total_seconds() * 1000)
        if ms_left <= 0:
            return

        timer = QTimer(self._parent)
        timer.setSingleShot(True)
        timer.timeout.connect(
            self._make_callback(title, hour, minute, remind_before, repeat, base_dt)
        )
        timer.start(ms_left)
        self._timers.append(timer)
