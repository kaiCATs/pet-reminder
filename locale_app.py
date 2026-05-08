# ================================================================
# LOCALE
# All user-facing strings in one place.
# Usage:  from locale_app import t
#         t("tray_show")
#         t("toast_delta_hm", h=2, m=30)
# ================================================================

import storage

_STRINGS = {
    # ---- Tray ----
    "tray_show":            {"ru": "🐾 Показать зверька",      "en": "🐾 Show pet"},
    "tray_hide":            {"ru": "📥 Скрыть в трей",         "en": "📥 Hide to tray"},
    "tray_events":          {"ru": "🗓 События",                "en": "🗓 Events"},
    "tray_autostart_on":    {"ru": "✅ Автозапуск включён",    "en": "✅ Autostart enabled"},
    "tray_autostart_off":   {"ru": "⬜ Автозапуск выключен",   "en": "⬜ Autostart disabled"},
    "tray_tutorial":        {"ru": "❓ Туториал",              "en": "❓ Tutorial"},
    "tray_rename":          {"ru": "🏷️ Сменить имя питомца",  "en": "🏷️ Rename pet"},
    "tray_lang":            {"ru": "🌐 Язык: RU",              "en": "🌐 Language: EN"},
    "tray_version":         {"ru": "Версия: {v}",              "en": "Version: {v}"},
    "tray_exit":            {"ru": "❌ Выход",                 "en": "❌ Exit"},

    # ---- Toast notifications ----
    "toast_event_now":      {"ru": "Начинается сейчас!",       "en": "Starting now!"},
    "toast_event_at":       {"ru": "Начало в {time}",          "en": "Starts at {time}"},
    "toast_delta_hm":       {"ru": "через {h}ч {m}мин",       "en": "in {h}h {m}m"},
    "toast_delta_h":        {"ru": "через {h}ч",              "en": "in {h}h"},
    "toast_delta_m":        {"ru": "через {m}мин",            "en": "in {m}m"},

    # ---- Event window ----
    "ev_title":             {"ru": "События",                  "en": "Events"},
    "ev_add":               {"ru": "Добавить событие",         "en": "Add event"},
    "ev_hint":              {"ru": "Двойной клик — изменить • ПКМ — удалить",
                             "en": "Double-click to edit • Right-click to delete"},
    "ev_delete_q":          {"ru": "Удалить событие?",         "en": "Delete event?"},
    "ev_delete_ok":         {"ru": "Удалить",                  "en": "Delete"},
    "ev_cancel":            {"ru": "Отмена",                   "en": "Cancel"},
    "ev_new":               {"ru": "Новое событие",            "en": "New event"},
    "ev_edit_title":        {"ru": "Редактировать событие",    "en": "Edit event"},
    "ev_name_label":        {"ru": "Название:",                "en": "Title:"},
    "ev_name_ph":           {"ru": "Введите название...",      "en": "Enter title..."},
    "ev_time_label":        {"ru": "Время события:",           "en": "Event time:"},
    "ev_remind_label":      {"ru": "Напомнить за:",            "en": "Remind before:"},
    "ev_repeat_label":      {"ru": "Повтор:",                  "en": "Repeat:"},
    "ev_save":              {"ru": "Сохранить",                "en": "Save"},
    "ev_add_btn":           {"ru": "Добавить",                 "en": "Add"},
    "ev_suffix_h":          {"ru": " ч",                      "en": " h"},
    "ev_suffix_m":          {"ru": " мин",                    "en": " min"},
    "ev_remind_now":        {"ru": "🔔 в момент",             "en": "🔔 at time"},
    "ev_remind_min":        {"ru": "🔔 за {n} мин",           "en": "🔔 {n} min before"},
    "ev_remind_hm":         {"ru": "🔔 за {h}ч {m}мин",      "en": "🔔 {h}h {m}m before"},
    "ev_remind_h":          {"ru": "🔔 за {h} ч",            "en": "🔔 {h}h before"},
    "ev_remind_day":        {"ru": "🔔 за день",              "en": "🔔 1 day before"},
    "ev_remind_week":       {"ru": "🔔 за неделю",            "en": "🔔 1 week before"},
    "ev_remind_days":       {"ru": "🔔 за {d} дн",           "en": "🔔 {d} days before"},

    # ---- Repeat options ----
    "rep_none":             {"ru": "Без повтора",              "en": "No repeat"},
    "rep_day":              {"ru": "Каждый день",              "en": "Every day"},
    "rep_week":             {"ru": "Каждую неделю",            "en": "Every week"},
    "rep_month":            {"ru": "Каждый месяц",             "en": "Every month"},
    "rep_year":             {"ru": "Каждый год",               "en": "Every year"},

    # ---- Tutorial ----
    "tut_next":             {"ru": "Далее →",                  "en": "Next →"},
    "tut_finish":           {"ru": "Завершить ✓",             "en": "Finish ✓"},
    "tut_skip":             {"ru": "Пропустить",               "en": "Skip"},

    # Tutorial step titles & texts
    "tut_s0_title":         {"ru": "Привет! 🐾",              "en": "Hey there! 🐾"},
    "tut_s0_text":          {"ru": "Я твой desktop-питомец и помощник.\n\nЖиву прямо на рабочем столе —\nвсегда рядом, но никогда не мешаю.\n\nМеня можно перетаскивать куда удобно.",
                             "en": "I'm your desktop pet and assistant.\n\nI live right on your desktop —\nalways nearby, never in the way.\n\nYou can drag me wherever you like."},
    "tut_s1_title":         {"ru": "Системный трей 🖥",       "en": "System tray 🖥"},
    "tut_s1_text":          {"ru": "Мою иконку ищи в правом нижнем\nуглу экрана — рядом с часами.\n\nЕсли не видишь — нажми стрелку ^\nрядом с часами, я прячусь там.\n\nПравый клик по иконке — моё меню.",
                             "en": "Find my icon in the bottom-right\ncorner of the screen — near the clock.\n\nIf you don't see it, click the ^ arrow\nnear the clock — I'm hiding there.\n\nRight-click the icon to open my menu."},
    "tut_s2_title":         {"ru": "Дни рождения 🎂",         "en": "Birthdays 🎂"},
    "tut_s2_text":          {"ru": "Я помню о днях рождения близких.\n\nМеню → 🎂 Дни рождения →\nдобавь имя и дату.\n\nНапомню за 7 и за 3 дня,\nи сам посчитаю сколько лет.",
                             "en": "I remember birthdays of your loved ones.\n\nMenu → 🎂 Birthdays →\nadd a name and date.\n\nI'll remind you 7 and 3 days before\nand calculate the age automatically."},
    "tut_s3_title":         {"ru": "События 🗓",              "en": "Events 🗓"},
    "tut_s3_text":          {"ru": "Меню → 🗓 События → выбери дату\n→ нажми «Добавить событие».\n\nЗадай время и когда напомнить.\n\nДвойной клик — редактировать.\nПравый клик — удалить.",
                             "en": "Menu → 🗓 Events → pick a date\n→ click 'Add event'.\n\nSet the time and when to remind you.\n\nDouble-click to edit.\nRight-click to delete."},
    "tut_s4_title":         {"ru": "Уведомления 🔔",          "en": "Notifications 🔔"},
    "tut_s4_text":          {"ru": "Когда придёт время — покажу\nуведомление в правом нижнем углу.\n\nТёмное — день рождения.\nСинее — событие.\n\nЗакроются сами через 6 секунд.",
                             "en": "When it's time — I'll show\na notification in the bottom-right corner.\n\nDark — birthday.\nBlue — event.\n\nThey close automatically after 6 seconds."},
    "tut_s5_title":         {"ru": "Текстовый помощник 💬",   "en": "Chat assistant 💬"},
    "tut_s5_text":          {"ru": "Нажми правой кнопкой мыши\nна зверька на рабочем столе —\nоткроется окно чата.\n\nПиши мне напрямую — задавай\nвопросы, проси напомнить\nо событии или узнай что\nзапланировано.",
                             "en": "Right-click the pet on your desktop\nto open the chat window.\n\nWrite to me directly — ask questions,\nrequest reminders, or check\nwhat's coming up."},
    "tut_s6_title":         {"ru": "Всё готово! 🎉",          "en": "All set! 🎉"},
    "tut_s6_text":          {"ru": "Теперь ты знаешь всё что нужно.\n\nЯ буду рядом и вовремя\nнапомню о важном.\n\nТуториал снова: меню трея → ❓",
                             "en": "Now you know everything you need.\n\nI'll be here and remind you\nof what matters.\n\nTutorial again: tray menu → ❓"},

    # ---- Pet name dialog ----
    "name_title":           {"ru": "Как меня назвать? 🐾",    "en": "What's my name? 🐾"},
    "name_hint":            {"ru": "Придумай мне имя — потом ты сможешь\nвызывать меня по имени.",
                             "en": "Give me a name — you'll be able\nto call me by name."},
    "name_ph":              {"ru": "Введи имя питомца...",     "en": "Enter pet name..."},
    "name_save":            {"ru": "Сохранить имя",            "en": "Save name"},
    "name_empty":           {"ru": "Имя не может быть пустым", "en": "Name cannot be empty"},
    "name_short":           {"ru": "Имя слишком короткое",     "en": "Name is too short"},
    "name_bad":             {"ru": "Пожалуйста, придумай другое имя 🙏",
                             "en": "Please choose a different name 🙏"},

    # ---- Name reminder bubble ----
    "bubble_text":          {"ru": "Эй, меня так и не назвали! 🐾\nИмя нужно для голосовых команд.",
                             "en": "Hey, I still have no name! 🐾\nNeeded for voice commands."},
    "bubble_btn":           {"ru": "Назвать сейчас",           "en": "Name me now"},

    # ---- Chat window ----
    "chat_placeholder":     {"ru": "Напиши сюда...",           "en": "Type here..."},
    "chat_resize_tip":      {"ru": "Потяни чтобы изменить размер", "en": "Drag to resize"},
    "chat_font_down":       {"ru": "Уменьшить шрифт",          "en": "Smaller font"},
    "chat_font_up":         {"ru": "Увеличить шрифт",          "en": "Larger font"},
    "chat_search_tip":      {"ru": "Поиск по истории",         "en": "Search history"},
    "chat_clear_tip":       {"ru": "Очистить историю",         "en": "Clear history"},
    "chat_clear_q":         {"ru": "Очистить всю историю чата?", "en": "Clear all chat history?"},
    "chat_clear_ok":        {"ru": "Очистить",                 "en": "Clear"},
    "chat_cleared":         {"ru": "История очищена 🐾",       "en": "History cleared 🐾"},
    "chat_error":           {"ru": "Что-то пошло не так. Попробуй ещё раз 🐾",
                             "en": "Something went wrong. Please try again 🐾"},
    "chat_thinking":        {"ru": "Думаю...",                 "en": "Thinking..."},
    "chat_waking":          {"ru": "Просыпаюсь, подожди...",   "en": "Waking up, please wait..."},

    # Search dialog
    "search_title":         {"ru": "🔍 Поиск по истории",     "en": "🔍 Search history"},
    "search_ph":            {"ru": "Что ищем?",               "en": "What are you looking for?"},
    "search_period":        {"ru": "За какой период:",        "en": "Time period:"},
    "search_yesterday":     {"ru": "Вчера",                   "en": "Yesterday"},
    "search_3days":         {"ru": "3 дня",                   "en": "3 days"},
    "search_week":          {"ru": "Неделя",                  "en": "Week"},
    "search_all":           {"ru": "Всё",                     "en": "All"},
    "search_btn":           {"ru": "Найти",                   "en": "Search"},
    "search_close":         {"ru": "Закрыть",                 "en": "Close"},
    "search_empty":         {"ru": "Введи что искать",        "en": "Enter a search query"},
    "search_none":          {"ru": "Ничего не найдено 🐾",    "en": "Nothing found 🐾"},
    "search_you":           {"ru": "Ты",                      "en": "You"},
    "search_pet":           {"ru": "Питомец",                 "en": "Pet"},

    # Prompt settings dialog
    "ps_title":             {"ru": "⚙️ Настройка помощника",  "en": "⚙️ Assistant settings"},
    "ps_tone":              {"ru": "Тон общения:",             "en": "Tone:"},
    "ps_tone_friendly":     {"ru": "дружеский",               "en": "friendly"},
    "ps_tone_business":     {"ru": "деловой",                 "en": "business"},
    "ps_tone_brief":        {"ru": "краткий",                 "en": "brief"},
    "ps_about":             {"ru": "О себе (необязательно):", "en": "About you (optional):"},
    "ps_about_ph":          {"ru": "Например: работаю дизайнером, не люблю длинные ответы...",
                             "en": "E.g.: I'm a designer, I prefer short answers..."},
    "ps_instr":             {"ru": "Дополнительные инструкции (необязательно):",
                             "en": "Extra instructions (optional):"},
    "ps_instr_ph":          {"ru": "Например: всегда отвечай на русском...",
                             "en": "E.g.: always reply in English..."},
    "ps_ask":               {"ru": "Переспрашивать если не понял",
                             "en": "Ask for clarification if unsure"},
    "ps_save":              {"ru": "Сохранить",               "en": "Save"},
    "ps_cancel":            {"ru": "Отмена",                  "en": "Cancel"},

    # ---- Quick buttons (chat suggestions) ----
    "qb_skip":              {"ru": "Пропустить",              "en": "Skip"},
    "qb_once":              {"ru": "Один раз",                "en": "Once"},
    "qb_every_day":         {"ru": "Каждый день",             "en": "Every day"},
    "qb_every_week":        {"ru": "Каждую неделю",           "en": "Every week"},
    "qb_every_month":       {"ru": "Каждый месяц",            "en": "Every month"},
    "qb_every_year":        {"ru": "Каждый год",              "en": "Every year"},
    "qb_at_time":           {"ru": "В момент",                "en": "At time"},
    "qb_15min":             {"ru": "За 15 мин",               "en": "15 min before"},
    "qb_30min":             {"ru": "За 30 мин",               "en": "30 min before"},
    "qb_1hour":             {"ru": "За час",                  "en": "1 hour before"},
    "qb_1day":              {"ru": "За день",                 "en": "1 day before"},
    "qb_on_day":            {"ru": "В день",                  "en": "On the day"},
    "qb_3days":             {"ru": "За 3 дня",                "en": "3 days before"},
    "qb_1week":             {"ru": "За неделю",               "en": "1 week before"},
    "qb_male":              {"ru": "👨 Мужское",              "en": "👨 Male"},
    "qb_female":            {"ru": "👩 Женское",              "en": "👩 Female"},

    # ---- Errors ----
    "err_no_frames":        {"ru": "Не найдены кадры idle_clean.\nПроверь сборку PyInstaller.",
                             "en": "idle_clean frames not found.\nCheck your PyInstaller build."},
}

# Internal repeat key → locale key
REPEAT_KEYS = [
    ("no_repeat",    "rep_none"),
    ("every_day",    "rep_day"),
    ("every_week",   "rep_week"),
    ("every_month",  "rep_month"),
    ("every_year",   "rep_year"),
]


def t(key: str, **kwargs) -> str:
    """Return the localised string, optionally formatted with kwargs."""
    lang  = storage.current_language()
    entry = _STRINGS.get(key, {})
    text  = entry.get(lang) or entry.get("ru") or key
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text


def repeat_options() -> list:
    """Localised list for QComboBox."""
    return [t(lk) for _, lk in REPEAT_KEYS]


def repeat_to_internal(display: str) -> str:
    """Display string → internal key."""
    for ik, lk in REPEAT_KEYS:
        if t(lk) == display:
            return ik
    return "no_repeat"


def internal_to_display(internal: str) -> str:
    """Internal key → display string."""
    for ik, lk in REPEAT_KEYS:
        if ik == internal:
            return t(lk)
    return t("rep_none")
