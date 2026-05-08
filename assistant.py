# ================================================================
# ИМПОРТЫ
# ================================================================
import os
import json
import re
from datetime import datetime, date, timedelta

import storage
from storage import load_pet_name
from events_manager import load_events, save_events
from birthday_manager import days_word, years_word


# ================================================================
# ОБЁРТКИ НАД storage — для совместимости с остальным кодом
# ================================================================
def load_chat_settings():
    return storage.load_chat_settings()

def save_chat_settings(data):
    storage.save_chat_settings(data)

def load_event_window_theme():
    return storage.load_event_window_theme()

def save_event_window_theme(theme):
    storage.save_event_window_theme(theme)

def load_user_prompt():
    return storage.load_user_prompt()

def save_user_prompt(data):
    storage.save_user_prompt(data)

def load_history():
    try:
        with open(storage.HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_history(history):
    try:
        with open(storage.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[assistant] save_history: {e}")

def clear_history():
    save_history([])

def add_to_history(role, text):
    history = load_history()
    history.append({
        "role": role,
        "text": text,
        "time": datetime.now().strftime("%d.%m.%Y %H:%M"),
    })
    save_history(history)

def search_history(query, period_days=None):
    history = load_history()
    results = []
    query_lower = query.lower()
    for msg in history:
        if period_days is not None:
            try:
                msg_date = datetime.strptime(msg["time"], "%d.%m.%Y %H:%M")
                if (datetime.now() - msg_date).days > period_days:
                    continue
            except Exception:
                continue
        if query_lower in msg["text"].lower():
            results.append(msg)
    return results


# ================================================================
# СЛОВАРЬ СЛЕНГА
# ================================================================
BASE_SLANG = {
    "др":   "добавь день рождения",
    "дрожение": "день рождения",
    "дня рождения": "день рождения",
    "дни рождения": "день рождения",
    "нап":  "напомни",
    "сег":  "сегодня",
    "зав":  "завтра",
    "пн":   "понедельник",
    "вт":   "вторник",
    "ср":   "среда",
    "чт":   "четверг",
    "пт":   "пятница",
    "сб":   "суббота",
    "вс":   "воскресенье",
    "мин":  "минут",
    "спс":  "спасибо",
    "пж":   "пожалуйста",
    "ок":   "хорошо",
    "ok":   "хорошо",
}

def load_slang():
    user_slang = storage.load_slang()
    return {**BASE_SLANG, **user_slang}

def save_user_slang(word, meaning):
    storage.save_user_slang(word, meaning)


def expand_slang(text):
    slang = load_slang()
    words = text.split()
    expanded = []
    for i, word in enumerate(words):
        clean = word.lower().strip(".,!?;:")
        # "др" как команду расширяем только если это первое слово фразы.
        # Внутри фразы ("покажи какие др и...") оставляем как есть.
        if clean == "др" and i > 0:
            expanded.append(word)
        else:
            expanded.append(slang.get(clean, word))
    return " ".join(expanded)


# ================================================================
# РАЗБОР ДАТЫ ИЗ ТЕКСТА
# Понимает: сегодня, завтра, послезавтра, дни недели,
# числа типа "15 марта", "15.03", "15.03.2026"
# ================================================================
# Варианты повтора
REPEAT_OPTIONS = {
    "раз":        "Без повтора",
    "один раз":   "Без повтора",
    "однократно": "Без повтора",
    "без повтора":"Без повтора",
    "каждый день":"Каждый день",
    "ежедневно":  "Каждый день",
    "каждую неделю": "Каждую неделю",
    "еженедельно":"Каждую неделю",
    "каждый месяц": "Каждый месяц",
    "ежемесячно": "Каждый месяц",
    "каждый год": "Каждый год",
    "ежегодно":   "Каждый год",
    "каждый":     None,  # уточним
}

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
    "мая": 5, "июня": 6, "июля": 7, "августа": 8,
    "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
}

WEEKDAYS_RU = {
    "понедельник": 0, "вторник": 1, "среда": 2, "среду": 2,
    "четверг": 3, "пятница": 4, "пятницу": 4,
    "суббота": 5, "субботу": 5, "воскресенье": 6,
}


def parse_date(text):
    """
    Разбирает дату из текста.
    Возвращает date или None если не нашёл.
    """
    text = text.lower().strip()
    today = date.today()

    if "сегодня" in text:
        return today
    if "завтра" in text and "послезавтра" not in text:
        return today + timedelta(days=1)
    if "послезавтра" in text:
        return today + timedelta(days=2)

    # День недели
    for name, wd in WEEKDAYS_RU.items():
        if name in text:
            days_ahead = (wd - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return today + timedelta(days=days_ahead)

    # Формат ДД.ММ.ГГГГ или ДД.ММ
    m = re.search(r"(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?", text)
    if m:
        day   = int(m.group(1))
        month = int(m.group(2))
        year  = int(m.group(3)) if m.group(3) else today.year
        try:
            return date(year, month, day)
        except Exception:
            pass

    # Формат "15 марта"
    m = re.search(r"(\d{1,2})\s+(" + "|".join(MONTHS.keys()) + ")", text)
    if m:
        day   = int(m.group(1))
        month = MONTHS[m.group(2)]
        year  = today.year
        d     = date(year, month, day)
        if d < today:
            d = date(year + 1, month, day)
        return d

    return None


def parse_year(text):
    """
    Разбирает год рождения из текста.
    ВНИМАНИЕ: ищет только полные 4-значные годы (1972, 2005),
    чтобы не захватить день из даты типа "28 мая".
    Двузначные числа разбираются через parse_age().
    """
    # Только полный 4-значный год
    m = re.search(r"\b(19|20)\d{2}\b", text)
    if m:
        return int(m.group(0))

    return None


def parse_age(text):
    """
    Разбирает возраст из текста.
    Понимает:
      "28 лет", "1 год", "22 года" — явный возраст
      "28" (одно число без даты/месяца) — возраст
      "1990" — это год рождения, возвращает None
    Возвращает int (возраст) или None.
    """
    t = text.lower().strip()

    # Если есть месяц или дата — точно не возраст
    if any(month in t for month in MONTHS):
        return None
    if re.search(r"\d{1,2}[.:/]\d{1,2}", t):
        return None

    # Явное "N лет / год / года"
    m = re.search(r"\b(\d{1,3})\s*(лет|год|года)\b", t)
    if m:
        return int(m.group(1))

    # 4-значное — это год рождения, не возраст
    if re.search(r"\b(19|20)\d{2}\b", t):
        return None

    # Просто число — считаем возрастом если разумный
    m = re.search(r"\b(\d{1,3})\b", t)
    if m:
        n = int(m.group(1))
        if 0 < n <= 130:
            return n

    return None


def age_to_birth_year(age):
    """Преобразует возраст в год рождения (приблизительно)."""
    return date.today().year - age


def parse_time(text):
    """
    Разбирает время из текста.
    Понимает:
      "15:00", "в 15:00", "13.45"
      "13 45" / "15 00" — цифры через пробел
      "в час дня" → 13:00,  "в час ночи" → 1:00
      "6 дня" → 18:00, "9 утра" → 9:00
      "7 вечера" → 19:00, "11 ночи" → 23:00
      "в три", "в полдень", "в полночь"
      "в 15", "в 15 часов"
    Возвращает (hour, minute) или None.
    """
    text = text.lower().strip()

    # Числовые слова → число (без контекста суток)
    num_words = {
        "ноль": 0, "полночь": 0,
        "час": 1, "один": 1,
        "два": 2, "двух": 2,
        "три": 3, "трёх": 3, "трех": 3,
        "четыре": 4, "четырёх": 4, "четырех": 4,
        "пять": 5, "пяти": 5,
        "шесть": 6, "шести": 6,
        "семь": 7, "семи": 7,
        "восемь": 8, "восьми": 8,
        "девять": 9, "девяти": 9,
        "десять": 10, "десяти": 10,
        "одиннадцать": 11, "одиннадцати": 11,
        "двенадцать": 12, "двенадцати": 12, "полдень": 12,
        "тринадцать": 13,
        "четырнадцать": 14,
        "пятнадцать": 15,
        "шестнадцать": 16,
        "семнадцать": 17,
        "восемнадцать": 18,
        "девятнадцать": 19,
        "двадцать": 20,
    }

    def apply_part(h, part):
        """Применяет контекст суток к числовому значению часа."""
        if part == "утра":
            return h % 12, 0          # 12 утра = 0, 1 утра = 1
        if part == "дня":
            return (12 if h == 12 else h + 12) % 24, 0   # 1 дня=13, 12 дня=12
        if part == "вечера":
            return (h + 12 if h < 12 else h), 0           # 7 вечера=19
        if part == "ночи":
            if h == 12: return 0, 0   # 12 ночи = 0
            if h >= 9:  return (h + 12) % 24, 0  # 11 ночи=23
            return h, 0               # 3 ночи = 3
        return h, 0

    # Формат ЧЧ:ММ или ЧЧ.ММ
    m = re.search(r"\b(\d{1,2})[:.](\d{2})\b", text)
    if m:
        h, mm = int(m.group(1)), int(m.group(2))
        if 0 <= h <= 23 and 0 <= mm <= 59:
            return h, mm

    # "ЧЧ ММ" — два числа через пробел ("13 45", "15 00")
    m = re.search(r"\b(\d{1,2})\s+(\d{2})\b(?!\s*(?:лет|год|года|мин|час|дн|нед|сут))", text)
    if m:
        before = text[:m.start()].rstrip()
        if not before.endswith("за"):
            h, mm = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mm <= 59:
                return h, mm

    # Числовое + контекст суток: "N утра/дня/вечера/ночи", "в N утра/..."
    parts_re = r"(утра|дня|вечера|ночи)"
    m = re.search(r"(?<!\bза)\s*\b(\d{1,2})\s*" + parts_re, text)
    if m:
        before = text[:m.start()].rstrip()
        if not before.endswith("за"):
            h = int(m.group(1))
            return apply_part(h, m.group(2))

    # Буквенный час + контекст суток: "в час дня", "два ночи", "три утра"
    # (должно проверяться ДО "в N", чтоб "в час дня" не попало в "в N = 1")
    for word, hour in num_words.items():
        for part in ("утра", "дня", "вечера", "ночи"):
            patterns = [
                r"\bв\s+" + word + r"(?:\s+час(?:а|ов)?)?\s+" + part + r"\b",
                r"\b" + word + r"(?:\s+час(?:а|ов)?)?\s+" + part + r"\b",
            ]
            for pat in patterns:
                if re.search(pat, text):
                    return apply_part(hour, part)

    # "в N часов" или просто "в N"
    m = re.search(r"\bв\s+(\d{1,2})(?:\s*(?:час(?:ов|а)?|ч\b))?", text)
    if m:
        h = int(m.group(1))
        if 0 <= h <= 23:
            return h, 0

    # Буквенное время без контекста суток: "в три", "в полдень"
    for word, hour in num_words.items():
        if re.search(r"\bв\s+" + word + r"\b", text):
            return hour, 0
        if text.strip() == word:
            return hour, 0

    # Просто число как ответ: "13"
    m = re.match(r"^(\d{1,2})$", text.strip())
    if m:
        h = int(m.group(1))
        if 0 <= h <= 23:
            return h, 0

    return None


# ================================================================
# ОПРЕДЕЛЕНИЕ НАМЕРЕНИЯ
# ================================================================
ADD_KEYWORDS     = ["добавь", "создай", "напомни", "запомни", "поставь", "запиши", "новое", "новый"]
DELETE_KEYWORDS  = ["удали", "убери", "отмени", "удалить"]
EDIT_KEYWORDS    = ["исправь", "измени", "поменяй", "обнови", "редактируй", "переименуй", "перенеси", "исправить", "изменить", "поменять"]
SHOW_KEYWORDS    = ["покажи", "что", "какие", "какое", "какой", "какая", "список", "есть", "будет", "запланировано", "ближайш", "расскажи"]
BIRTHDAY_KEYWORDS = ["день рождения", "др", "рождени", "именинни"]
EVENT_KEYWORDS   = ["событи", "встреч", "напоминани", "дело", "задач", "план"]


def parse_repeat(text):
    """Определяет повтор из текста. Возвращает строку повтора или None."""
    t = text.lower()
    for key, val in REPEAT_OPTIONS.items():
        if key in t and val is not None:
            return val
    return None


def _has_word(text, words):
    """
    Проверяет, есть ли в тексте любое из слов.
    По умолчанию для всех триггеров разрешён суффикс из букв
    ("событи" → "события/событие/событий", "встреч" → "встречу").

    Слова, для которых суффикс НЕДОПУСТИМ (т.е. полное слово должно совпасть),
    перечислены в _STRICT_WORDS — это формы вроде "добавь" (не должно матчить
    "добавишь"), "др" (не должно матчить "другой").
    """
    for w in words:
        # Многословные триггеры — простой подстрочный поиск
        if " " in w:
            if w in text:
                return True
            continue

        # Строгая проверка — должно совпасть полное слово
        if w in _STRICT_WORDS:
            if re.search(r"\b" + re.escape(w) + r"\b", text):
                return True
            continue

        # Обычные триггеры — разрешаем суффикс
        if re.search(r"\b" + re.escape(w) + r"[а-яё]*\b", text):
            return True
    return False


# Слова, у которых суффикс не разрешён — должно совпадать полностью
_STRICT_WORDS = {
    "др",        # не "другой"
    "добавь",    # не "добавишь"
    "удали",     # не "удалишь"
    "напомни",   # не "напомнишь"
    "запомни",   # не "запомнишь"
    "поставь",   # не "поставишь"
    "запиши",    # не "запишешь"
    "покажи",    # не "покажешь"
    "создай",    # не "создашь"
    "убери",     # не "уберёшь"
    "отмени",    # не "отменишь"
    "удалить",
}


def detect_intent(text):
    """
    Определяет намерение пользователя.
    Возвращает строку: add_event, add_birthday, delete_event,
    delete_birthday, show_events, show_birthdays, show_all, unknown
    """
    t = text.lower().strip()

    # Если фраза — вопрос (заканчивается ?), и нет явной команды в начале —
    # это вопрос, а не команда. Например "а время этого др добавишь?"
    is_question = t.endswith("?")

    is_add     = _has_word(t, ADD_KEYWORDS)
    is_delete  = _has_word(t, DELETE_KEYWORDS)
    is_edit    = _has_word(t, EDIT_KEYWORDS)
    is_show    = _has_word(t, SHOW_KEYWORDS)
    is_bd      = _has_word(t, BIRTHDAY_KEYWORDS)
    is_event   = _has_word(t, EVENT_KEYWORDS)

    # Если текст начинается с "день рождени" или "др " — это добавление ДР
    if re.match(r"^(день рождени|дн[её] рождени|др\s+\S)", t):
        is_add = True
        is_bd  = True

    # Если это вопрос и в нём нет явного "покажи/список/что" — игнорируем
    # все команды на добавление/удаление. Вопрос вроде "а ты добавишь?" — не команда.
    if is_question and not is_show:
        is_add    = False
        is_delete = False

    # «Просто фраза с временем/датой» — считаем добавлением события.
    # Например: «зубной завтра в 14», «купить хлеб 5 числа в 9 утра».
    # Срабатывает только когда нет других интентов и нет вопроса.
    if (not is_add and not is_delete and not is_show and not is_question):
        has_date = bool(parse_date(text))
        has_time = bool(parse_time(text))
        # Должна быть хотя бы дата ИЛИ время; и хотя бы 2 слова всего —
        # чтоб одиночное «привет» не превращалось в событие.
        words = [w for w in re.split(r"\s+", t) if w]
        if (has_date or has_time) and len(words) >= 2:
            is_add   = True
            is_event = True

    if is_delete and is_bd:
        return "delete_birthday"
    if is_delete:
        return "delete_event"
    if is_edit:
        return "edit_event"
    if is_add and is_bd:
        return "add_birthday"
    if is_add:
        return "add_event"
    if is_show and is_bd:
        return "show_birthdays"
    if is_show and is_event:
        return "show_events"
    if is_show:
        return "show_all"

    return "unknown"


# ================================================================
# СОСТОЯНИЕ ДИАЛОГА
# Хранит незавершённые команды — когда не хватает данных
# помощник переспрашивает и ждёт ответа.
# ================================================================
class DialogState:
    def __init__(self):
        self.reset()

    def reset(self):
        self.intent         = None   # текущее намерение
        self.title          = None   # название события/имя человека
        self.event_date     = None   # дата
        self.event_time     = None   # время (hour, minute)
        self.birth_year     = None   # год рождения
        self.repeat         = None   # повтор события
        self.waiting_for    = None   # чего ждём от пользователя
        self.gender         = None   # "m" / "f" — пол человека (для ДР)
        self.remind_minutes = None   # за сколько минут напомнить (для ДР)
        self.year_asked     = False  # уже спрашивали про возраст/год


# Глобальное состояние диалога (сбрасывается при каждом новом намерении)
_state = DialogState()


# ================================================================
# ФОРМАТИРОВАНИЕ ОТВЕТОВ
# ================================================================
def _r(ru: str, en: str) -> str:
    """Return ru or en string depending on current language setting."""
    return en if storage.current_language() == "en" else ru


def _fmt_date(d):
    if storage.current_language() == "en":
        months_en = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        return f"{months_en[d.month]} {d.day}"
    months_ru = [
        "", "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    return f"{d.day} {months_ru[d.month]}"


def _tone_greeting():
    tone = load_user_prompt().get("tone", "дружеский")
    if tone in ("краткий", "brief"):
        return ""
    if tone in ("деловой", "business"):
        return _r("Понял. ", "Got it. ")
    return ""


# ================================================================
# ОБРАБОТЧИКИ КОМАНД
# ================================================================

def _is_birthday_event(e):
    """ДР отличается от обычного события признаками 'каждый год' + 'День рождения' в title."""
    title  = (e.get("title") or "").lower()
    repeat = e.get("repeat", "")
    return "день рождения" in title or (repeat == "Каждый год" and "рождени" in title)


def handle_show_events(text="", period_days=30):
    """Показывает ближайшие СОБЫТИЯ (без ДР)."""
    today  = date.today()
    events = load_events()

    upcoming = []
    for e in events:
        if _is_birthday_event(e):
            continue
        try:
            ev_date = date(int(e["year"]), int(e["month"]), int(e["day"]))
            delta   = (ev_date - today).days
            if 0 <= delta <= period_days:
                upcoming.append((delta, e))
        except Exception:
            continue

    upcoming.sort(key=lambda x: x[0])

    if not upcoming:
        return _r(
            f"На ближайшие {period_days} {days_word(period_days)} событий нет 🐾",
            f"No events in the next {period_days} days 🐾"
        )

    lines = [_r("Ближайшие события:", "Upcoming events:")]
    for delta, e in upcoming:
        t = f"{int(e.get('hour',0)):02d}:{int(e.get('minute',0)):02d}"
        ev_date = date(int(e["year"]), int(e["month"]), int(e["day"]))
        if delta == 0:
            when = _r("сегодня", "today")
        elif delta == 1:
            when = _r("завтра", "tomorrow")
        else:
            when = _fmt_date(ev_date)
        lines.append(f"• {e['title']} — {when} {_r('в', 'at')} {t}")

    return "\n".join(lines)


def handle_show_birthdays(period_days=365):
    """Показывает ближайшие ДНИ РОЖДЕНИЯ."""
    today  = date.today()
    events = load_events()

    upcoming = []
    for e in events:
        if not _is_birthday_event(e):
            continue
        try:
            month = int(e["month"]); day = int(e["day"])
            # Ближайшая дата ДР в этом или следующем году
            try:
                next_bd = date(today.year, month, day)
            except ValueError:
                continue
            if next_bd < today:
                next_bd = date(today.year + 1, month, day)
            delta = (next_bd - today).days
            if delta <= period_days:
                upcoming.append((delta, next_bd, e))
        except Exception:
            continue

    upcoming.sort(key=lambda x: x[0])

    if not upcoming:
        return _r("Дней рождения пока нет 🐾", "No birthdays yet 🐾")

    lines = [_r("Ближайшие дни рождения:", "Upcoming birthdays:")]
    for delta, bd, e in upcoming[:10]:
        if delta == 0:
            when = _r("сегодня! 🎂", "today! 🎂")
        elif delta == 1:
            when = _r(f"завтра, {_fmt_date(bd)}", f"tomorrow, {_fmt_date(bd)}")
        else:
            when = _fmt_date(bd)
        lines.append(f"• {e['title']} — {when}")

    return "\n".join(lines)


def handle_show_all():
    ev = handle_show_events()
    bd = handle_show_birthdays()
    ev_empty = ev.startswith("На ближайшие") or ev.startswith("No events")
    bd_empty = bd.startswith("Дней рождения") or bd.startswith("No birthdays")
    if ev_empty and bd_empty:
        return _r("Пока ничего не запланировано 🐾", "Nothing planned yet 🐾")
    if ev_empty:
        return bd
    if bd_empty:
        return ev
    return f"{ev}\n\n{bd}"


def handle_add_event(title, ev_date, ev_time, repeat="Без повтора",
                     remind_minutes=30, on_events_changed=None):
    """Добавляет событие и сохраняет."""
    hour, minute = ev_time if ev_time else (0, 0)

    new_event = {
        "title":  title,
        "day":    ev_date.day,
        "month":  ev_date.month,
        "year":   ev_date.year,
        "hour":   hour,
        "minute": minute,
        "remind_before_minutes": int(remind_minutes),
        "repeat": repeat,
    }

    events = load_events()
    events.append(new_event)
    save_events(events)

    if on_events_changed:
        on_events_changed()

    t_str = f"{hour:02d}:{minute:02d}"

    # Описание периода напоминания
    rm = int(remind_minutes)
    if rm == 0:
        remind_str = _r("в момент события", "at event time")
    elif rm < 60:
        remind_str = _r(f"за {rm} мин", f"{rm} min before")
    elif rm < 24*60:
        h, m = divmod(rm, 60)
        remind_str = _r(f"за {h} ч" + (f" {m} мин" if m else ""), f"{h}h" + (f" {m}m" if m else "") + " before")
    else:
        d, rest = divmod(rm, 24*60)
        h, m = divmod(rest, 60)
        parts = [f"{d} {days_word(d)}"]
        if h: parts.append(f"{h} ч")
        if m: parts.append(f"{m} мин")
        remind_str = _r("за ", "in ") + " ".join(parts)

    if storage.current_language() == "en":
        repeat_str = f"\n• Repeat: {repeat}" if repeat and repeat not in ("Без повтора", "no_repeat", "No repeat") else "\n• One time"
        return (
            f"Done! Event added:\n"
            f"• {title}\n"
            f"• {_fmt_date(ev_date)} at {t_str}\n"
            f"• Reminder: {remind_str}"
            f"{repeat_str} 🐾"
        )
    repeat_str = f"\n• Повтор: {repeat}" if repeat and repeat != "Без повтора" else "\n• Один раз"
    return (
        f"Готово! Добавил событие:\n"
        f"• {title}\n"
        f"• {_fmt_date(ev_date)} в {t_str}\n"
        f"• Напоминание: {remind_str}"
        f"{repeat_str} 🐾"
    )


# ================================================================
# ОПРЕДЕЛЕНИЕ ПОЛА ПО ИМЕНИ
#
# Двуполые имена — те, что одинаково звучат для м и ж.
# При встрече такого имени помощник переспрашивает у пользователя.
# Для остальных угадываем по окончанию.
# ================================================================
AMBIGUOUS_NAMES = {
    "саша", "женя", "валя", "слава", "лёша", "леша",
    "серёжа", "серожа", "серёга", "серога",
    "ваня", "юра", "стёпа", "степа", "митя",
    "сима", "ника", "андрюша", "коля",
    "паша", "вася", "петя", "костя",
    # Женское "Александра" совпадает с косвенными от "Александр"
    "александра",
}

# Имена, которые уверенно мужские но кончаются на -а/-я
MALE_NAMES_ON_A = {
    "никита", "илья", "лёва", "лева", "гриша", "миша", "дима",
    "толя", "алёша", "алеша", "костя", "паша", "вася",
    "петя", "коля", "ваня", "юра",
}

# Уверенно женские (для контроля, остальное по окончанию)
FEMALE_NAMES = {
    "мария", "анна", "ольга", "елена", "татьяна", "ирина", "наталья",
    "светлана", "екатерина", "юлия", "анастасия", "ксения", "дарья",
    "виктория", "вера", "надежда", "любовь",
    "таня", "маша", "оля", "лена", "катя", "юля", "настя", "ксюша",
    "даша", "вика", "ира", "наташа", "света",
}


def is_ambiguous_gender(name):
    """Проверяет, двуполое ли имя — нужно ли переспрашивать пол."""
    if not name:
        return False
    return name.lower() in AMBIGUOUS_NAMES


def detect_gender(name):
    """
    Определяет пол по имени без переспрашивания.
    Возвращает "m" или "f".
    Для двуполых имён возвращает "f" по умолчанию (но вызывающий код
    должен сам проверить is_ambiguous_gender и переспросить).
    """
    if not name:
        return "f"
    lower = name.lower()

    # Явные списки
    if lower in MALE_NAMES_ON_A:
        return "m"
    if lower in FEMALE_NAMES:
        return "f"

    # По окончанию
    if lower.endswith(("а", "я")):
        return "f"
    if lower.endswith("ь"):
        # Имена на -ь чаще мужские (Игорь, Олег...). Женских мало (Любовь).
        return "m"
    # Согласные и -й — мужские (Иван, Алексей)
    return "m"


def _to_genitive(name, gender=None):
    if not name:
        return name
    if storage.current_language() == "en":
        return name
    if gender is None:
        gender = detect_gender(name)

    n = name
    lower = n.lower()

    if gender == "m":
        # Александр → Александра, Иван → Ивана, Олег → Олега
        if lower[-1:] in "бвгджзклмнпрстфхцчшщ":
            return n + "а"
        # Алексей → Алексея, Андрей → Андрея
        if lower.endswith("й"):
            return n[:-1] + "я"
        # Игорь → Игоря, Олесь → Олеся
        if lower.endswith("ь"):
            return n[:-1] + "я"
        # Никита → Никиты, Илья → Ильи (мужские на -а/-я)
        if lower.endswith("я"):
            return n[:-1] + "и"
        if lower.endswith("а"):
            return n[:-1] + "ы" if n[-2] not in "жшщч" else n[:-1] + "и"
        return n

    # Женские
    # Мария → Марии, Анастасия → Анастасии
    if lower.endswith("ия"):
        return n[:-1] + "и"
    # Таня → Тани, Оля → Оли
    if lower.endswith("я"):
        return n[:-1] + "и"
    # Маша → Маши, Лена → Лены
    if lower.endswith("а"):
        return n[:-1] + "ы" if n[-2] not in "жшщч" else n[:-1] + "и"
    # Любовь → Любови
    if lower.endswith("ь"):
        return n[:-1] + "и"
    return n


def _to_dative(name, gender=None):
    if not name:
        return name
    if storage.current_language() == "en":
        return name
    if gender is None:
        gender = detect_gender(name)

    n = name
    lower = n.lower()

    if gender == "m":
        # Александр → Александру, Иван → Ивану
        if lower[-1:] in "бвгджзклмнпрстфхцчшщ":
            return n + "у"
        # Алексей → Алексею
        if lower.endswith("й"):
            return n[:-1] + "ю"
        # Игорь → Игорю
        if lower.endswith("ь"):
            return n[:-1] + "ю"
        # Никита → Никите, Илья → Илье (мужские на -а/-я склоняются как женские)
        if lower.endswith("я"):
            return n[:-1] + "е"
        if lower.endswith("а"):
            return n[:-1] + "е"
        return n

    # Женские
    # Мария → Марии, Анастасия → Анастасии
    if lower.endswith("ия"):
        return n[:-1] + "и"
    # Таня → Тане, Коля → Коле
    if lower.endswith("я"):
        return n[:-1] + "е"
    # Маша → Маше, Лена → Лене
    if lower.endswith("а"):
        return n[:-1] + "е"
    # Любовь → Любови
    if lower.endswith("ь"):
        return n[:-1] + "и"
    return n


def handle_add_birthday_full(name, gender, bd_date, birth_year,
                             event_time, remind_minutes, repeat):
    """
    Полное добавление дня рождения с настройками:
      gender         — "m" или "f"
      event_time     — (hour, minute) во сколько напомнить
      remind_minutes — за сколько минут до даты напомнить
      repeat         — "Каждый год" / "Каждый месяц" / "Без повтора"
    """
    from datetime import date as d
    name_gen     = _to_genitive(name, gender)
    current_year = d.today().year
    hour, minute = event_time if event_time else (9, 0)

    if birth_year:
        age = current_year - birth_year
        if age < 0 or age > 130:
            title   = f"День рождения {name_gen}"
            age_str = ""
        else:
            word    = years_word(age)
            title   = f"День рождения {name_gen} ({age} {word})"
            age_str = f" ({age} {word})"
    else:
        title   = f"День рождения {name_gen}"
        age_str = ""

    new_event = {
        "title":  title,
        "day":    bd_date.day,
        "month":  bd_date.month,
        "year":   bd_date.year,
        "hour":   hour,
        "minute": minute,
        "remind_before_minutes": int(remind_minutes),
        "repeat": repeat,
    }
    events = load_events()
    events.append(new_event)
    save_events(events)

    # Текст подтверждения
    time_str = f"{hour:02d}:{minute:02d}"

    if remind_minutes == 0:
        when_str = f"в день в {time_str}"
    else:
        h, m = divmod(int(remind_minutes), 60)
        days, h = divmod(h, 24)
        parts = []
        if days: parts.append(f"{days} {days_word(days)}")
        if h:    parts.append(f"{h} ч")
        if m:    parts.append(f"{m} мин")
        when_str = f"за {' '.join(parts)} в {time_str}"

    if repeat == "Без повтора":
        repeat_str = "Один раз"
    elif repeat == "Каждый год":
        repeat_str = "Каждый год"
    elif repeat == "Каждый месяц":
        repeat_str = "Каждый месяц"
    else:
        repeat_str = repeat

    if storage.current_language() == "en":
        return (
            f"Got it! Birthday saved:\n"
            f"• {name}{age_str} — {_fmt_date(bd_date)} 🎂\n"
            f"• Reminder: {when_str}\n"
            f"• Repeat: {repeat_str}"
        )
    return (
        f"Запомнил! День рождения:\n"
        f"• {name}{age_str} — {_fmt_date(bd_date)} 🎂\n"
        f"• Напоминание: {when_str}\n"
        f"• Повтор: {repeat_str}"
    )


def handle_add_birthday(name, bd_date, birth_year=None):
    """
    Старая упрощённая версия — оставлена для совместимости.
    Использует значения по умолчанию: 09:00, за день, каждый год.
    """
    return handle_add_birthday_full(
        name, detect_gender(name), bd_date, birth_year,
        event_time=(9, 0), remind_minutes=1440, repeat="Каждый год"
    )


def handle_delete_event(title_query):
    """Удаляет событие по названию (частичное/стемовое совпадение)."""
    matches, events = handle_find_event(title_query)

    if not matches:
        return _r(f"Не нашёл событие «{title_query}» 🐾", f"Event '{title_query}' not found 🐾")

    if len(matches) > 1:
        names = "\n".join(f"• {e['title']}" for e in matches)
        return _r(f"Нашёл несколько событий:\n{names}\n\nУточни название.", f"Found multiple events:\n{names}\n\nPlease be more specific.")

    events.remove(matches[0])
    save_events(events)
    return _r(f"Удалил событие «{matches[0]['title']}» 🐾", f"Deleted event '{matches[0]['title']}' 🐾")


def handle_delete_birthday(name_query):
    """Удаляет день рождения (ежегодное событие) по имени (стемовый поиск)."""
    events = load_events()
    q_low  = name_query.lower()
    stems  = [q_low]
    for cut in (1, 2, 3):
        if len(q_low) - cut >= 2:
            stems.append(q_low[:-cut])

    def matches(e):
        if not _is_birthday_event(e):
            return False
        t = e["title"].lower()
        return any(stem in t for stem in stems)

    found = [e for e in events if matches(e)]

    if not found:
        return _r(f"Не нашёл день рождения «{name_query}» 🐾", f"Birthday for '{name_query}' not found 🐾")
    if len(found) > 1:
        names = "\n".join(f"• {e['title']}" for e in found)
        return _r(f"Нашёл несколько:\n{names}\n\nУточни имя.", f"Found multiple:\n{names}\n\nPlease be more specific.")

    events.remove(found[0])
    save_events(events)
    return _r(f"Удалил {found[0]['title']} 🐾", f"Deleted {found[0]['title']} 🐾")


def handle_find_event(query):
    """
    Ищет событие по подстроке названия (без учёта окончаний).
    Для «встречи», «встречу», «встреча» ищет стем «встреч».
    Возвращает (matches, events_list).
    """
    events = load_events()
    # Берём стем запроса: убираем 1-3 финальных буквы для нечёткого поиска
    q_low  = query.lower()
    # Список вариантов для поиска: полное слово и стемы с 1-3 убранными буквами
    stems  = [q_low]
    for cut in (1, 2, 3):
        if len(q_low) - cut >= 3:
            stems.append(q_low[:-cut])

    def matches_query(title):
        t = title.lower()
        return any(stem in t for stem in stems)

    matches = [e for e in events if matches_query(e["title"])]
    return matches, events


def handle_edit_event(query, field, new_value, on_events_changed=None):
    """
    Изменяет поле у найденного события.
    field: "title" | "date" | "time" | "repeat" | "remind"
    new_value: уже разобранное значение нужного типа
    """
    matches, events = handle_find_event(query)

    if not matches:
        return _r(f"Не нашёл событие «{query}» 🐾", f"Event '{query}' not found 🐾")
    if len(matches) > 1:
        names = "\n".join(f"• {e['title']}" for e in matches)
        return _r(f"Нашёл несколько событий, уточни название:\n{names}", f"Found multiple events, please specify:\n{names}")

    idx   = events.index(matches[0])
    event = events[idx]

    if field == "title":
        event["title"] = new_value
    elif field == "date":
        event["day"]   = new_value.day
        event["month"] = new_value.month
        event["year"]  = new_value.year
    elif field == "time":
        event["hour"]   = new_value[0]
        event["minute"] = new_value[1]
    elif field == "repeat":
        event["repeat"] = new_value
    elif field == "remind":
        event["remind_before_minutes"] = int(new_value)

    events[idx] = event
    save_events(events)
    if on_events_changed:
        on_events_changed()

    # Подтверждение
    t     = f"{int(event['hour']):02d}:{int(event['minute']):02d}"
    ev_d  = date(int(event["year"]), int(event["month"]), int(event["day"]))
    if storage.current_language() == "en":
        return (
            f"Updated! Event:\n"
            f"• {event['title']}\n"
            f"• {_fmt_date(ev_d)} at {t}\n"
            f"• Repeat: {event.get('repeat','no_repeat')} 🐾"
        )
    return (
        f"Исправил! Событие:\n"
        f"• {event['title']}\n"
        f"• {_fmt_date(ev_d)} в {t}\n"
        f"• Повтор: {event.get('repeat','Без повтора')} 🐾"
    )


# ================================================================
# ГЛАВНАЯ ФУНКЦИЯ ОБРАБОТКИ СООБЩЕНИЯ
# Разбирает намерение, собирает данные через диалог,
# выполняет команду и возвращает ответ.
# ================================================================
def process_message(text, on_events_changed=None):
    """
    Обрабатывает сообщение пользователя.
    Возвращает строку — ответ помощника.
    on_events_changed — колбэк для обновления таймеров в Pet.
    """
    global _state

    pet_name = load_pet_name() or "Питомец"
    text     = expand_slang(text.strip())

    # --------------------------------------------------------
    # Если ждём уточнения от пользователя — но если пользователь
    # явно начал новую команду или передумал ("отмена", "стоп",
    # "забудь"), сбрасываем ожидание.
    # --------------------------------------------------------
    if _state.waiting_for:
        t_low = text.lower().strip()
        cancel_words = ("отмена", "отмени", "стоп", "забудь", "не надо", "хватит",
                         "cancel", "stop", "nevermind", "forget it")
        if any(w in t_low for w in cancel_words):
            _state.reset()
            return _r("Хорошо, отменил 🐾", "Got it, cancelled 🐾")

        # Эти состояния обрабатывают ЛЮБОЙ ввод напрямую, без попытки
        # переопределить интент — иначе "др ани" при delete_what
        # интерпретируется как add_birthday
        passthrough_states = ("delete_what", "edit_what", "edit_field",
                              "edit_value_time", "edit_value_date",
                              "edit_value_title", "edit_value_repeat")
        if _state.waiting_for in passthrough_states:
            return _handle_clarification(text, on_events_changed)

        # Если пользователь начал новую явную команду — выходим из ожидания
        new_intent = detect_intent(text)
        # Короткий ответ (≤3 слов, без команды) — скорее всего это ответ на вопрос
        is_short_answer = len(text.split()) <= 3 and not _has_word(t_low, ADD_KEYWORDS + DELETE_KEYWORDS)

        # Исключение: если ждём имя/пол и пришёл текст с датой или временем —
        # это точно не имя, пользователь переключился на событие
        if _state.waiting_for in ("birthday_name", "birthday_gender", "event_title"):
            if parse_date(text) or parse_time(text):
                is_short_answer = False

        if new_intent in ("add_event", "add_birthday", "delete_event",
                          "delete_birthday", "show_events", "show_birthdays",
                          "show_all") and not is_short_answer:
            _state.reset()
            # Падаем дальше — обрабатываем как новую команду
        else:
            return _handle_clarification(text, on_events_changed)

    # --------------------------------------------------------
    # Определяем намерение
    # --------------------------------------------------------
    intent = detect_intent(text)
    _state.reset()
    _state.intent = intent

    # --------------------------------------------------------
    # ПОКАЗАТЬ ВСЕГО
    # --------------------------------------------------------
    if intent == "show_all":
        return handle_show_all()

    if intent == "show_events":
        return handle_show_events(text)

    if intent == "show_birthdays":
        return handle_show_birthdays()

    # --------------------------------------------------------
    # ИСПРАВИТЬ СОБЫТИЕ
    # Формат: "исправь встречу — перенеси на 30 мая"
    #         "измени время встречи на 15:00"
    #         "переименуй встречу в 'совещание'"
    # Если непонятно что менять — переспрашиваем.
    # --------------------------------------------------------
    if intent == "edit_event":
        # Пытаемся разобрать: что менять + на что
        t_low = text.lower()

        # Выбираем поле и новое значение из фразы
        field     = None
        new_value = None
        query     = None

        # Время: "измени время X на Y"
        time_match = parse_time(text)
        date_match = parse_date(text)

        if any(k in t_low for k in ("перенеси", "перенести", "перенос", "переставь")):
            # Перенос = смена даты
            if date_match:
                field     = "date"
                new_value = date_match
        elif any(k in t_low for k in ("время", "в ", "перевод")):
            if time_match:
                field     = "time"
                new_value = time_match
        elif any(k in t_low for k in ("названи", "переименуй", "переименовать")):
            # Переименование — извлекаем новое название после "в" или после кавычек
            m_new = re.search(r"[\"«»\'](.*?)[\"«»\']", text)
            if not m_new:
                m_new = re.search(r"\bна\s+(.+)$", t_low)
            if m_new:
                field     = "title"
                new_value = m_new.group(1).strip().strip("\"«»'")

        # Что редактируем — название из фразы
        skip = EDIT_KEYWORDS + ADD_KEYWORDS + ["время", "дату", "название",
               "перенеси", "переименуй"]
        query = _extract_title(text, skip)

        if not query:
            _state.waiting_for = "edit_what"
            return _r("Что нужно исправить? Напиши название события.", "What should I fix? Write the event name.")

        _state.title = query  # сохраняем что редактируем

        if field and new_value is not None:
            return handle_edit_event(query, field, new_value, on_events_changed)

        # Не смогли разобрать что именно менять — спрашиваем
        _state.waiting_for = "edit_field"
        return _r(
            f"Нашёл «{query}». Что исправить?\n• Напиши дату, время, название или повтор",
            f"Found '{query}'. What to change?\n• Write date, time, title or repeat"
        )

    # --------------------------------------------------------
    # УДАЛИТЬ СОБЫТИЕ
    # --------------------------------------------------------
    if intent == "delete_event":
        # Не передаём EVENT_KEYWORDS в skip — иначе "встреча" → "" (название пропадает)
        title = _extract_title(text, DELETE_KEYWORDS + BIRTHDAY_KEYWORDS)
        if title and len(title) >= 2:
            return handle_delete_event(title)
        _state.waiting_for = "delete_what"
        return _r("Что удалить? Напиши название события или имя (для дня рождения).", "What to delete? Write the event name or person's name (for birthday).")

    if intent == "delete_birthday":
        name = _extract_name(text)
        # _extract_name уже убирает BIRTHDAY_KEYWORDS, но если не нашла —
        # пробуем вырезать вручную
        if not name:
            raw = text.lower()
            for kw in DELETE_KEYWORDS + ["др", "день рождения", "день рождение",
                                          "дня рождения"]:
                raw = re.sub(r"\b" + re.escape(kw) + r"\b", " ", raw)
            raw = re.sub(r"\s+", " ", raw).strip()
            if len(raw) >= 2:
                name = raw.capitalize()
        if name:
            return handle_delete_birthday(name)
        _state.waiting_for = "delete_what"
        return _r("Чей день рождения удалить? Напиши имя.", "Whose birthday should I delete? Write the name.")

    # --------------------------------------------------------
    # ДОБАВИТЬ СОБЫТИЕ
    # Поток: название → дата → время → повтор
    #        → за сколько напомнить → создаём
    # --------------------------------------------------------
    if intent == "add_event":
        _state.title      = _extract_title(text, ADD_KEYWORDS + EVENT_KEYWORDS)
        _state.event_date = parse_date(text)
        _state.event_time = parse_time(text)
        _state.repeat     = parse_repeat(text)
        return _continue_event_flow(on_events_changed)

    # --------------------------------------------------------
    # ДОБАВИТЬ ДЕНЬ РОЖДЕНИЯ
    # Поток: имя → (пол если двуполое) → дата → возраст
    #        → время → за сколько напомнить → повтор → создаём
    # --------------------------------------------------------
    if intent == "add_birthday":
        _state.title      = _extract_name(text)
        _state.event_date = parse_date(text)
        _state.birth_year = parse_year(text)

        # Если года нет — пробуем понять как возраст ("28 лет")
        if _state.birth_year is None:
            age = parse_age(text)
            if age is not None:
                _state.birth_year = age_to_birth_year(age)

        # Если что-то про возраст уже извлекли из первичного текста —
        # больше не переспрашиваем
        if _state.birth_year is not None:
            _state.year_asked = True

        return _continue_birthday_flow(on_events_changed)

    # --------------------------------------------------------
    # ПРИВЕТСТВИЕ
    # --------------------------------------------------------
    greetings = ["привет", "здравствуй", "хай", "салют", "добрый",
                 "hello", "hi", "hey", "good morning", "good evening"]
    if any(g in text.lower() for g in greetings):
        if storage.current_language() == "en":
            return (
                f"Hey! I'm {pet_name} 🐾\n\n"
                f"Here's what I can do:\n"
                f"• Show events and birthdays\n"
                f"• Add an event or birthday\n"
                f"• Delete an event or birthday\n\n"
                f"Just tell me what you need!"
            )
        return (
            f"Привет! Я {pet_name} 🐾\n\n"
            f"Вот что я умею:\n"
            f"• Показать события и дни рождения\n"
            f"• Добавить событие или день рождения\n"
            f"• Удалить событие или день рождения\n\n"
            f"Просто напиши что нужно!"
        )

    # --------------------------------------------------------
    # СПАСИБО
    # --------------------------------------------------------
    if any(w in text.lower() for w in ["спасибо", "спс", "благодарю",
                                        "thanks", "thank you", "thx"]):
        if storage.current_language() == "en":
            return "You're welcome! 🐾"
        return _r("Пожалуйста! 🐾", "You're welcome! 🐾")

    # --------------------------------------------------------
    # НЕ ПОНЯЛ
    # --------------------------------------------------------
    _state.reset()
    if storage.current_language() == "en":
        return (
            "Not sure I understood 🐾\n\n"
            "I can:\n"
            "• «show events» — upcoming events\n"
            "• «show birthdays» — upcoming birthdays\n"
            "• «add event meeting tomorrow at 3pm»\n"
            "• «add birthday Maria March 15 1990»\n"
            "• «delete event meeting»"
        )
    return (
        "Не совсем понял 🐾\n\n"
        "Я умею:\n"
        "• «покажи события» — ближайшие события\n"
        "• «покажи дни рождения» — ближайшие ДР\n"
        "• «добавь событие встреча завтра в 15:00»\n"
        "• «добавь день рождения Маша 15 марта 1990»\n"
        "• «удали событие встреча»"
    )


def _handle_clarification(text, on_events_changed=None):
    """Обрабатывает уточняющий ответ пользователя."""
    global _state

    waiting = _state.waiting_for
    _state.waiting_for = None

    # Умное удаление — ищем и в событиях и в ДР
    if waiting == "delete_what":
        raw = text.strip()
        clean = raw.lower()
        for kw in DELETE_KEYWORDS + ADD_KEYWORDS + ["др", "день рождения", "день рождение",
                                      "дня рождения", "дн рождения"]:
            clean = re.sub(r"\b" + re.escape(kw) + r"\w*\b", " ", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        query = clean if len(clean) >= 2 else raw
        _state.reset()
        bd_result = handle_delete_birthday(query)
        if "Не нашёл" not in bd_result:
            return bd_result
        return handle_delete_event(query)

    # Редактирование — что редактировать (название события)
    if waiting == "edit_what":
        _state.title = text.strip()
        matches, _ = handle_find_event(_state.title)
        if not matches:
            _state.waiting_for = "edit_what"
            return _r(f"Не нашёл событие «{_state.title}». Попробуй написать название точнее.", f"Event '{_state.title}' not found. Try a more specific name.")
        if len(matches) > 1:
            names = "\n".join(f"• {e['title']}" for e in matches)
            _state.waiting_for = "edit_what"
            return f"Нашёл несколько, уточни:\n{names}"
        _state.waiting_for = "edit_field"
        return f"Нашёл «{matches[0]['title']}». Что исправить?\n• Напиши дату, время, название или повтор"

    # Редактирование — что именно менять (поле и значение)
    if waiting == "edit_field":
        t_low = text.lower().strip()
        query = _state.title

        field     = None
        new_value = None

        # Если пользователь написал только тип поля без значения —
        # запоминаем что ждём и переспрашиваем конкретное значение
        _field_hints_ru = {
            "время":      ("edit_value_time",  "Напиши новое время, например «15:00» или «в три дня»"),
            "дата":       ("edit_value_date",  "Напиши новую дату, например «30 мая»"),
            "дату":       ("edit_value_date",  "Напиши новую дату, например «30 мая»"),
            "название":   ("edit_value_title", "Напиши новое название"),
            "повтор":     ("edit_value_repeat","Напиши повтор: Один раз / Каждый день / Каждую неделю / Каждый месяц / Каждый год"),
            "повторение": ("edit_value_repeat","Напиши повтор: Один раз / Каждый день / Каждую неделю / Каждый месяц / Каждый год"),
        }
        _field_hints_en = {
            "time":   ("edit_value_time",  "Write the new time, e.g. '15:00' or '3pm'"),
            "date":   ("edit_value_date",  "Write the new date, e.g. 'May 30'"),
            "title":  ("edit_value_title", "Write the new title"),
            "name":   ("edit_value_title", "Write the new title"),
            "repeat": ("edit_value_repeat","Write repeat: Once / Every day / Every week / Every month / Every year"),
        }
        _field_hints = _field_hints_en if storage.current_language() == "en" else _field_hints_ru
        if t_low in _field_hints:
            wf, prompt = _field_hints[t_low]
            _state.waiting_for = wf
            return prompt

        time_v = parse_time(text)
        date_v = parse_date(text)
        rep_v  = parse_repeat(text)

        if date_v:
            field     = "date"
            new_value = date_v
        elif time_v:
            field     = "time"
            new_value = time_v
        elif rep_v:
            field     = "repeat"
            new_value = rep_v
        else:
            # Попытка найти новое название в кавычках или после "в"/"на"
            m_new = re.search(r"[\"«»\'](.*?)[\"«»\']", text)
            if not m_new:
                m_new = re.search(r"\b(?:на|в)\s+(.{2,})", t_low)
            if m_new:
                candidate = m_new.group(1).strip().strip("\"«»'")
                if len(candidate) >= 2:
                    field     = "title"
                    new_value = candidate.capitalize()

        if field is None or new_value is None:
            _state.waiting_for = "edit_field"
            return _r("Не понял. Напиши что изменить: дату, время, название или повтор.", "Didn't get that. Write what to change: date, time, title or repeat.")

        result = handle_edit_event(query, field, new_value, on_events_changed)
        _state.reset()
        return result

    # Редактирование — ожидаем конкретное время
    if waiting == "edit_value_time":
        time_v = parse_time(text)
        if not time_v:
            _state.waiting_for = "edit_value_time"
            return _r("Не понял время. Напиши например «15:00» или «в три дня».", "Didn't get the time. Write e.g. '15:00' or '3pm'.")
        result = handle_edit_event(_state.title, "time", time_v, on_events_changed)
        _state.reset()
        return result

    # Редактирование — ожидаем конкретную дату
    if waiting == "edit_value_date":
        date_v = parse_date(text)
        if not date_v:
            _state.waiting_for = "edit_value_date"
            return _r("Не понял дату. Напиши например «30 мая».", "Didn't get the date. Write e.g. 'May 30'.")
        result = handle_edit_event(_state.title, "date", date_v, on_events_changed)
        _state.reset()
        return result

    # Редактирование — ожидаем новое название
    if waiting == "edit_value_title":
        candidate = text.strip().strip("\"«»'")
        if len(candidate) < 2:
            _state.waiting_for = "edit_value_title"
            return _r("Название слишком короткое. Напиши новое название события.", "Title is too short. Write a new event name.")
        result = handle_edit_event(_state.title, "title", candidate.capitalize(), on_events_changed)
        _state.reset()
        return result

    # Редактирование — ожидаем повтор
    if waiting == "edit_value_repeat":
        t_low = text.lower().strip()
        rep_v = parse_repeat(text)
        if not rep_v:
            if "один" in t_low or "раз" in t_low or "без" in t_low or "нет" in t_low:
                rep_v = "Без повтора"
            elif "год" in t_low or "ежегодно" in t_low:
                rep_v = "Каждый год"
            elif "месяц" in t_low:
                rep_v = "Каждый месяц"
            elif "недел" in t_low:
                rep_v = "Каждую неделю"
            elif "день" in t_low or "ежедневно" in t_low:
                rep_v = "Каждый день"
        if not rep_v:
            _state.waiting_for = "edit_value_repeat"
            return _r("Не понял. Напиши: Один раз / Каждый день / Каждую неделю / Каждый месяц / Каждый год", "Didn't get that. Write: Once / Every day / Every week / Every month / Every year")
        result = handle_edit_event(_state.title, "repeat", rep_v, on_events_changed)
        _state.reset()
        return result

    # Повтор события
    if waiting == "event_repeat":
        repeat = parse_repeat(text)
        if not repeat:
            t = text.lower().strip()
            if "один" in t or "раз" in t or "нет" in t or "без" in t:
                repeat = "Без повтора"
            elif "день" in t or "ежедневно" in t:
                repeat = "Каждый день"
            elif "недел" in t:
                repeat = "Каждую неделю"
            elif "месяц" in t:
                repeat = "Каждый месяц"
            elif "год" in t or "ежегодно" in t:
                repeat = "Каждый год"
            else:
                _state.waiting_for = "event_repeat"
                return _r("Не понял. Выбери:\n• Один раз\n• Каждый день\n• Каждую неделю\n• Каждый месяц\n• Каждый год", "Didn't get that. Choose:\n• Once\n• Every day\n• Every week\n• Every month\n• Every year")
        _state.repeat = repeat
        return _continue_event_flow(on_events_changed)

    # За сколько до события напомнить
    if waiting == "event_remind":
        t = text.lower().strip()
        if t in ("в момент", "в момент события", "в момент.", "момент",
                 "вмомент", "в момент!"):
            _state.remind_minutes = 0
        elif "момент" in t or "точно" in t:
            _state.remind_minutes = 0
        elif "15" in t:
            _state.remind_minutes = 15
        elif "30" in t or "пол" in t:
            _state.remind_minutes = 30
        elif "час" in t and "пол" not in t:
            # "за час" / "за 1 час" / "за 2 часа"
            m = re.search(r"за\s+(\d+)\s*час", t)
            _state.remind_minutes = int(m.group(1)) * 60 if m else 60
        elif "день" in t or "сутк" in t:
            m = re.search(r"за\s+(\d+)\s*(дн|сут)", t)
            _state.remind_minutes = int(m.group(1)) * 24 * 60 if m else 24 * 60
        elif "недел" in t:
            _state.remind_minutes = 7 * 24 * 60
        else:
            m = re.search(r"за\s+(\d+)\s*(мин|ч|час|дн|нед)", t)
            if m:
                n    = int(m.group(1))
                unit = m.group(2)
                if unit.startswith("мин"):  _state.remind_minutes = n
                elif unit.startswith("ч"):  _state.remind_minutes = n * 60
                elif unit.startswith("дн"): _state.remind_minutes = n * 24 * 60
                elif unit.startswith("нед"):_state.remind_minutes = n * 7 * 24 * 60
            elif t.isdigit():
                _state.remind_minutes = int(t)
            else:
                _state.waiting_for = "event_remind"
                return _r(
                    "Не понял. Выбери:\n• В момент\n• За 15 мин\n• За 30 мин\n• За час\n• За день",
                    "Didn't get that. Choose:\n• At time\n• 15 min before\n• 30 min before\n• 1 hour before\n• 1 day before"
                )
        return _continue_event_flow(on_events_changed)

    # Год рождения / возраст
    if waiting == "birthday_year":
        t = text.lower().strip()
        # В любом случае помечаем — год уже спрашивали
        _state.year_asked = True
        if "пропуст" in t or "не знаю" in t or t in ("нет", "-", "—"):
            _state.birth_year = None
        else:
            # Сначала пробуем 4-значный год
            year = parse_year(text)
            if year:
                _state.birth_year = year
            else:
                # Иначе — возраст
                age = parse_age(text)
                if age is not None:
                    _state.birth_year = age_to_birth_year(age)
                else:
                    _state.waiting_for = "birthday_year"
                    _state.year_asked = False  # ещё не получили валидный ответ
                    return _r(
                        "Не понял. Напиши:\n• возраст — например «28» или «28 лет»\n• год рождения — например «1990»\n• или «пропустить»",
                        "Didn't get that. Write:\n• age — e.g. '28' or '28 years'\n• birth year — e.g. '1990'\n• or 'skip'"
                    )
        return _continue_birthday_flow(on_events_changed)

    # Добавление события — название
    if waiting == "event_title":
        _state.title = text.strip()
        return _continue_event_flow(on_events_changed)

    # Добавление события — дата
    if waiting == "event_date":
        _state.event_date = parse_date(text)
        if not _state.event_date:
            _state.waiting_for = "event_date"
            return _r("Не понял дату. Напиши например «завтра», «15 марта» или «15.03»", "Didn't get the date. Write e.g. 'tomorrow', 'March 15' or '15.03'")
        return _continue_event_flow(on_events_changed)

    # Добавление события — время
    if waiting == "event_time":
        _state.event_time = parse_time(text)
        if not _state.event_time:
            _state.waiting_for = "event_time"
            return _r("Не понял время. Напиши например «в 15:00» или «в три»", "Didn't get the time. Write e.g. '15:00' or '3pm'")
        return _continue_event_flow(on_events_changed)

    # Добавление ДР — имя
    if waiting == "birthday_name":
        _state.title = text.strip()
        return _continue_birthday_flow(on_events_changed)

    # Добавление ДР — пол (для двуполых имён)
    if waiting == "birthday_gender":
        t = text.lower().strip()
        if "муж" in t or "👨" in t or t in ("м", "m"):
            _state.gender = "m"
        elif "жен" in t or "👩" in t or t in ("ж", "f", "w"):
            _state.gender = "f"
        else:
            _state.waiting_for = "birthday_gender"
            return _r(f"Не понял. {_state.title} — это мужчина или женщина?", f"Didn't get that. Is {_state.title} male or female?")
        return _continue_birthday_flow(on_events_changed)

    # Добавление ДР — дата
    if waiting == "birthday_date":
        _state.event_date = parse_date(text)
        # Год пробуем разобрать только если в тексте нет месяца —
        # иначе число дня будет ошибочно принято за год/возраст
        year = parse_year(text)
        if year:
            _state.birth_year = year
        else:
            age = parse_age(text)
            if age is not None:
                _state.birth_year = age_to_birth_year(age)
        if not _state.event_date:
            _state.waiting_for = "birthday_date"
            return _r("Не понял дату. Напиши например «15 марта» или «15.03.1990»", "Didn't get the date. Write e.g. 'March 15' or '15.03.1990'")
        return _continue_birthday_flow(on_events_changed)

    # Добавление ДР — время напоминания
    if waiting == "birthday_time":
        # Готовые варианты с кнопок
        t = text.lower().strip()
        if t in ("утром", "9:00", "09:00"):
            _state.event_time = (9, 0)
        elif t in ("днём", "днем", "12:00"):
            _state.event_time = (12, 0)
        elif t in ("вечером", "18:00", "19:00"):
            _state.event_time = (19, 0)
        else:
            parsed = parse_time(text)
            if parsed:
                _state.event_time = parsed
            else:
                _state.waiting_for = "birthday_time"
                return _r("Не понял время. Напиши например «09:00» или нажми кнопку.", "Didn't get the time. Write e.g. '09:00'.")
        return _continue_birthday_flow(on_events_changed)

    # Добавление ДР — за сколько до даты напомнить
    if waiting == "birthday_remind_period":
        t = text.lower().strip()
        if "в день" in t or t == "день":
            _state.remind_minutes = 0
        elif "за день" in t or "за 1 день" in t or "за сутки" in t:
            _state.remind_minutes = 24 * 60          # 1440
        elif "за 3 дня" in t or "за три" in t:
            _state.remind_minutes = 3 * 24 * 60      # 4320
        elif "за неделю" in t or "за 7" in t:
            _state.remind_minutes = 7 * 24 * 60      # 10080
        else:
            # Попытка разобрать произвольное "за N часов / минут / дней"
            m = re.search(r"за\s+(\d+)\s*(дн|час|мин)", t)
            if m:
                n    = int(m.group(1))
                unit = m.group(2)
                if unit.startswith("дн"):  _state.remind_minutes = n * 24 * 60
                elif unit.startswith("ч"): _state.remind_minutes = n * 60
                else:                      _state.remind_minutes = n
            else:
                _state.waiting_for = "birthday_remind_period"
                return _r("Не понял. Выбери из вариантов или напиши например «за 2 дня».", "Didn't get that. Choose from options or write e.g. '2 days before'.")
        return _continue_birthday_flow(on_events_changed)

    # Добавление ДР — повтор
    if waiting == "birthday_repeat":
        t = text.lower().strip()
        if "год" in t or "ежегодно" in t:
            _state.repeat = "Каждый год"
        elif "месяц" in t or "ежемесячно" in t:
            _state.repeat = "Каждый месяц"
        elif "недел" in t:
            _state.repeat = "Каждую неделю"
        elif "день" in t or "ежедневно" in t:
            _state.repeat = "Каждый день"
        elif "без" in t or "один" in t or "раз" in t or "нет" in t:
            _state.repeat = "Без повтора"
        else:
            _state.waiting_for = "birthday_repeat"
            return _r("Не понял. Выбери из вариантов.", "Didn't get that. Please choose from the options.")
        return _continue_birthday_flow(on_events_changed)

    _state.reset()
    return _r("Не понял. Попробуй снова 🐾", "Didn't understand. Please try again 🐾")


# ================================================================
# ПЕРЕХОД ПО ШАГАМ ДОБАВЛЕНИЯ ДР
# Когда очередной шаг заполнен, идём к следующему незаполненному.
# Когда все заполнены — создаём событие.
# ================================================================
def _continue_birthday_flow(on_events_changed=None):
    global _state

    if not _state.title:
        _state.waiting_for = "birthday_name"
        return _r("Чей день рождения добавить? Напиши имя.", "Whose birthday? Write a name.")

    # Двуполое имя — нужно явно уточнить
    if _state.gender is None and is_ambiguous_gender(_state.title):
        _state.waiting_for = "birthday_gender"
        return _r(f"Имя «{_state.title}» бывает мужским и женским. Подскажи, кто это?", f"The name '{_state.title}' can be male or female. Which one?")

    # Пол ещё не задан — определяем сами
    if _state.gender is None:
        _state.gender = detect_gender(_state.title)

    if not _state.event_date:
        _state.waiting_for = "birthday_date"
        return _r(f"Когда день рождения у {_to_genitive(_state.title, _state.gender)}? Напиши дату.", f"When is {_state.title}'s birthday? Write the date.")

    if _state.birth_year is None and not _state.year_asked:
        _state.waiting_for = "birthday_year"
        if storage.current_language() == "en":
            return (
                f"How old will {_state.title} be?\n"
                f"You can write age ('28') or birth year ('1990').\n"
                f"If you don't know — press Skip."
            )
        return (
            f"Сколько лет исполнится {_to_dative(_state.title, _state.gender)}?\n"
            f"Можно написать возраст («28») или год рождения («1990»).\n"
            f"Если не знаешь — нажми «Пропустить»."
        )

    if _state.event_time is None:
        _state.waiting_for = "birthday_time"
        return _r("В какое время напомнить? Можно написать «09:00» или нажать кнопку.", "What time should I remind you? Write e.g. '09:00'.")

    if _state.remind_minutes is None:
        _state.waiting_for = "birthday_remind_period"
        return _r("За сколько до даты напомнить?", "How far in advance should I remind you?")

    if _state.repeat is None:
        _state.waiting_for = "birthday_repeat"
        return _r("Как часто напоминать?", "How often should I remind you?")

    # Всё собрано — создаём событие
    result = handle_add_birthday_full(
        _state.title, _state.gender, _state.event_date, _state.birth_year,
        _state.event_time, _state.remind_minutes, _state.repeat
    )
    if on_events_changed:
        on_events_changed()
    _state.reset()
    return result


# ================================================================
# ПЕРЕХОД ПО ШАГАМ ДОБАВЛЕНИЯ СОБЫТИЯ
# Когда очередной шаг заполнен — идём к следующему незаполненному.
# Когда всё заполнено — создаём событие.
# ================================================================
def _continue_event_flow(on_events_changed=None):
    global _state

    if not _state.title:
        _state.waiting_for = "event_title"
        return _r("Как назвать событие?", "What's the event name?")

    if not _state.event_date:
        _state.waiting_for = "event_date"
        return _r(f"На какую дату добавить «{_state.title}»?", f"What date for '{_state.title}'?")

    if not _state.event_time:
        _state.waiting_for = "event_time"
        return _r("В какое время?", "What time?")

    if _state.repeat is None:
        _state.waiting_for = "event_repeat"
        return _r(
            "Как часто повторяется?\n• Один раз\n• Каждый день\n• Каждую неделю\n• Каждый месяц\n• Каждый год",
            "How often does it repeat?\n• Once\n• Every day\n• Every week\n• Every month\n• Every year"
        )

    if _state.remind_minutes is None:
        _state.waiting_for = "event_remind"
        return _r(
            "За сколько до события напомнить?\n• В момент\n• За 15 мин\n• За 30 мин\n• За час\n• За день",
            "How long before the event should I remind you?\n• At time\n• 15 min before\n• 30 min before\n• 1 hour before\n• 1 day before"
        )

    # Всё собрано — создаём
    result = handle_add_event(
        _state.title, _state.event_date, _state.event_time,
        _state.repeat, _state.remind_minutes, on_events_changed
    )
    _state.reset()
    return result


# ================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ИЗВЛЕЧЕНИЯ
# ================================================================
def _extract_title(text, skip_words):
    """
    Пытается извлечь название события из текста —
    убирает ключевые слова и служебные хвосты, берёт оставшееся.
    """
    t = text.lower()

    # Убираем ключевые слова с границами слова — иначе "встреч"
    # отрежет хвост у "встреча" и оставит висячую "а".
    # Сначала длинные триггеры — чтоб "день рождени" ушёл целиком до "день".
    for w in sorted(skip_words, key=len, reverse=True):
        if " " in w:
            t = t.replace(w, " ")
        else:
            t = re.sub(r"\b" + re.escape(w) + r"\w*", " ", t)

    # Убираем даты и времена с пометками типа "13 дня", "5 утра"
    t = re.sub(r"\b\d{1,2}[:.]\d{2}\b", "", t)
    t = re.sub(r"\b\d{1,2}\s*(час(?:ов|а)?|ч)\b", "", t)
    t = re.sub(r"\b\d{1,2}\s*(дня|вечера|утра|ночи)\b", "", t)
    for month in MONTHS:
        t = re.sub(r"\b" + month + r"\b", " ", t)
    for wd in WEEKDAYS_RU:
        t = re.sub(r"\b" + wd + r"\b", " ", t)
    t = re.sub(r"\b\d+\b", "", t)

    # Служебные слова — не должны попасть в название
    stop_words = [
        "сегодня", "завтра", "послезавтра", "сейчас", "потом",
        "в", "на", "во", "к", "у", "о", "от", "до", "из", "по", "с", "за", "со",
        "утра", "утром", "вечера", "вечером", "дня", "днём", "днем",
        "ночи", "ночью",
        "час", "часа", "часов",
        "минут", "минута", "минуты",
        "день", "дни",
        "год", "года", "лет", "месяц", "месяца", "месяцев",
        "неделя", "неделю", "недели",
        "это", "этого", "этому", "эту", "эта", "этой",
        "также", "тоже", "ещё", "еще",
        "пожалуйста", "плз", "пж",
        "а", "и", "но", "или", "же",
    ]
    for w in stop_words:
        t = re.sub(r"\b" + w + r"\b", " ", t)

    t = re.sub(r"[?!.,;:]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    if len(t) < 2:
        return None
    # Капитализируем первое слово
    return t[0].upper() + t[1:]


def _extract_name(text):
    """
    Извлекает имя человека из текста.
    Сначала убирает ключевые слова, потом ищет имя.
    """
    # Убираем ключевые слова
    clean = text
    for kw in BIRTHDAY_KEYWORDS + ADD_KEYWORDS + DELETE_KEYWORDS:
        clean = re.sub(r"\b" + re.escape(kw) + r"\b", " ", clean, flags=re.IGNORECASE)

    # Убираем даты и времена
    clean = re.sub(r"\b\d{1,2}[.:]\d{2}\b", "", clean)
    clean = re.sub(r"\b\d{4}\b", "", clean)
    for month in MONTHS:
        clean = re.sub(r"\b" + month + r"\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\b\d+\b", "", clean)

    # Стоп-слова — слова, которые именами быть не могут
    stop_words = [
        "в", "на", "во", "к", "у", "о", "от", "до", "из", "по", "с", "за", "со",
        "утра", "вечера", "дня", "ночи", "утром", "вечером", "ночью", "днём", "днем",
        "сегодня", "завтра", "послезавтра", "сейчас", "потом",
        "время", "дата", "час", "часов", "минут", "минуты", "минута",
        "событие", "событий", "событию", "встреча", "встречу", "встречи",
        "напоминание", "напоминания", "напоминанию",
        "дело", "дела", "делу", "задача", "задачу", "задачи", "план", "планы",
        "год", "года", "лет", "месяц", "месяца", "месяцев", "неделя", "неделю",
        "будет", "был", "была", "это", "этого", "этому", "этой", "ещё", "еще",
        "также", "тоже", "его", "её", "ее", "их", "мне", "тебе", "ему", "ей",
        "что", "когда", "как", "куда", "зачем", "кому", "кем", "чем",
        "пожалуйста", "плз", "пж", "спасибо",
        "добавишь", "удалишь", "покажешь", "напомнишь", "запомнишь",
        "поставишь", "запишешь", "сделаешь",
    ]
    for w in stop_words:
        clean = re.sub(r"\b" + w + r"\b", " ", clean, flags=re.IGNORECASE)

    clean = re.sub(r"\s+", " ", clean).strip()

    # Ищем слово с заглавной буквы — приоритет, имена обычно с большой
    m = re.search(r"\b([А-ЯЁ][а-яё]{1,}(?:\s+[А-ЯЁ][а-яё]+)?)\b", clean)
    if m:
        candidate = m.group(1)
        if candidate.lower() not in stop_words:
            return _normalize_name(candidate)

    # Если нет заглавных — берём первое осмысленное слово
    words = [w for w in clean.split() if len(w) >= 2 and w.lower() not in stop_words]
    if words:
        return _normalize_name(words[0].capitalize())

    return None


def _normalize_name(name):
    """
    Приводит имя из косвенного падежа к именительному.
    Таня/Тани/Тане → Таня, Маши → Маша, Коли → Коля и т.д.
    """
    if not name:
        return name

    # Женские имена: окончания косвенных падежей → именительный
    female_endings = [
        ("ани", "аня"), ("ени", "еня"), ("ини", "иня"),
        ("уни", "уня"), ("ыни", "ыня"),
        ("ане", "аня"), ("ене", "еня"),
        ("аши", "аша"), ("еши", "еша"),
        ("аси", "ася"), ("еси", "еся"),
        ("али", "аля"), ("ели", "еля"),
        ("ари", "аря"), ("ери", "еря"),
        ("аки", "ака"), ("оки", "ока"),
        ("ики", "ика"),
    ]

    # Мужские имена: окончания и → я (Коли → Коля, Пети → Петя)
    male_endings = [
        ("оли", "оля"), ("ети", "етя"), ("ани", "аня"),
        ("ени", "еня"), ("ити", "итя"),
    ]

    lower = name.lower()
    for end, replacement in female_endings + male_endings:
        if lower.endswith(end):
            return name[:-len(end)] + replacement

    return name
