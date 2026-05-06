# ================================================================
# ИМПОРТЫ
# ================================================================
import os

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

from config import save_pet_name, load_pet_name, mark_tutorial_done


# ================================================================
# ФИЛЬТР ЗАПРЕЩЁННЫХ СЛОВ
# ================================================================
_BAD_WORDS = [
    "хуй", "хуе", "хуя", "хуи", "пизд", "ебл", "ёбл", "еба", "ёба",
    "бляд", "блят", "сука", "пидр", "пидо", "мудак", "мудил", "залуп",
    "ёбан", "ебан", "еблан", "шлюх", "дрочи", "дроч", "ёбнут", "ебнут",
    "fuck", "shit", "bitch", "cunt", "dick", "cock", "ass",
]

def _contains_bad_word(text):
    lower = text.lower()
    return any(bad in lower for bad in _BAD_WORDS)


# ================================================================
# ШАГИ ТУТОРИАЛА
# ================================================================
TUTORIAL_STEPS = [
    {
        "title": "Привет! 🐾",
        "text": (
            "Я твой desktop-питомец и помощник.\n\n"
            "Живу прямо на рабочем столе —\n"
            "всегда рядом, но никогда не мешаю.\n\n"
            "Меня можно перетаскивать куда удобно."
        ),
    },
    {
        "title": "Системный трей 🖥",
        "text": (
            "Мою иконку ищи в правом нижнем\n"
            "углу экрана — рядом с часами.\n\n"
            "Если не видишь — нажми стрелку ^\n"
            "рядом с часами, я прячусь там.\n\n"
            "Правый клик по иконке — моё меню."
        ),
    },
    {
        "title": "Дни рождения 🎂",
        "text": (
            "Я помню о днях рождения близких.\n\n"
            "Меню → 🎂 Дни рождения →\n"
            "добавь имя и дату.\n\n"
            "Напомню за 7 и за 3 дня,\n"
            "и сам посчитаю сколько лет."
        ),
    },
    {
        "title": "События 🗓",
        "text": (
            "Меню → 🗓 События → выбери дату\n"
            "→ нажми «Добавить событие».\n\n"
            "Задай время и когда напомнить.\n\n"
            "Двойной клик — редактировать.\n"
            "Правый клик — удалить."
        ),
    },
    {
        "title": "Уведомления 🔔",
        "text": (
            "Когда придёт время — покажу\n"
            "уведомление в правом нижнем углу.\n\n"
            "Тёмное — день рождения.\n"
            "Синее — событие.\n\n"
            "Закроются сами через 6 секунд."
        ),
    },
    {
        "title": "Текстовый помощник 💬",
        "text": (
            "Нажми правой кнопкой мыши\n"
            "на зверька на рабочем столе —\n"
            "откроется окно чата.\n\n"
            "Пиши мне напрямую — задавай\n"
            "вопросы, проси напомнить\n"
            "о событии или узнай что\n"
            "запланировано.\n\n"
            "При первом открытии я сам\n"
            "скачаю нужный модуль."
        ),
    },
    {
        "title": "Всё готово! 🎉",
        "text": (
            "Теперь ты знаешь всё что нужно.\n\n"
            "Я буду рядом и вовремя\n"
            "напомню о важном.\n\n"
            "Туториал снова: меню трея → ❓"
        ),
    },
]


# ================================================================
# ОКНО ВВОДА ИМЕНИ ПИТОМЦА
# Защищённое — нельзя закрыть без сохранения имени.
# ================================================================
class PetNameDialog(QWidget):
    def __init__(self, on_name_saved=None):
        super().__init__()

        self.on_name_saved = on_name_saved

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Window
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(440, 300)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )

        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 440, 300)
        self.container.setObjectName("container")

        layout = QVBoxLayout(self.container)
        layout.setSpacing(15)
        layout.setContentsMargins(35, 35, 35, 35)

        title = QLabel("Как меня назвать? 🐾")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #222;")
        layout.addWidget(title)

        hint = QLabel(
            "Придумай мне имя — потом ты сможешь\n"
            "вызывать меня голосом по имени."
        )
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("font-size: 15px; color: #555;")
        layout.addWidget(hint)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введи имя питомца...")
        self.name_input.setMaxLength(20)
        self.name_input.setStyleSheet("font-size: 16px;")
        self.name_input.returnPressed.connect(self._save)
        layout.addWidget(self.name_input)

        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("font-size: 13px; color: #e81123;")
        layout.addWidget(self.error_label)

        self.save_btn = QPushButton("Сохранить имя")
        self.save_btn.clicked.connect(self._save)
        layout.addWidget(self.save_btn)

        self._apply_style()
        self._fade_in()
        self.show()

    def _apply_style(self):
        self.setStyleSheet("""
        QFrame#container {
            background-color: rgba(255, 255, 255, 0.97);
            border-radius: 20px;
        }
        QLineEdit {
            border: 2px solid #0078D7;
            border-radius: 8px;
            padding: 10px 14px;
            font-size: 16px;
        }
        QLineEdit:focus {
            border-color: #005ea6;
        }
        QPushButton {
            background-color: #0078D7;
            color: white;
            border-radius: 10px;
            padding: 12px;
            font-size: 15px;
        }
        QPushButton:hover {
            background-color: #005ea6;
        }
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
            self.error_label.setText("Имя не может быть пустым")
            return
        if len(name) < 2:
            self.error_label.setText("Имя слишком короткое")
            return
        if _contains_bad_word(name):
            self.error_label.setText("Пожалуйста, придумай другое имя 🙏")
            return

        save_pet_name(name)
        self.error_label.setText("")

        if self.on_name_saved:
            self.on_name_saved(name)

        self.close()

    def closeEvent(self, event):
        # Запрещаем закрытие если имя ещё не задано
        if load_pet_name() is None:
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
# СТРАНИЦА ШАГА — один экран внутри слайдера
# ================================================================
class StepPage(QWidget):
    """Один экран туториала — заголовок + текст. Живёт внутри QStackedWidget."""

    def __init__(self, step_data):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignTop)

        title = QLabel(step_data["title"])
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet(
            "font-size: 20px; font-weight: bold; color: #111;"
        )
        layout.addWidget(title)

        text = QLabel(step_data["text"])
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        text.setStyleSheet(
            "font-size: 16px; color: #333; line-height: 1.6;"
        )
        layout.addWidget(text)
        layout.addStretch()


# ================================================================
# ОКНО ТУТОРИАЛА С АНИМАЦИЕЙ ЛИСТАНИЯ
#
# Одно окно, внутри QStackedWidget со страницами.
# При переходе между шагами старая страница уезжает влево,
# новая въезжает справа — эффект листания книги.
# ================================================================
class TutorialWindow(QWidget):
    def __init__(self, on_finished=None):
        super().__init__()

        self.on_finished    = on_finished
        self._current_index = 0
        self._animating     = False  # защита от двойного клика во время анимации

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(440, 420)

        # Позиция — правый нижний угол над тостами
        screen = QApplication.primaryScreen().availableGeometry()
        self._end_x = screen.right() - self.width() - 20
        self._end_y = screen.bottom() - self.height() - 180
        self.move(self._end_x, screen.bottom() + 10)

        # Контейнер
        self.container = QFrame(self)
        self.container.setGeometry(0, 0, 440, 420)
        self.container.setObjectName("tutContainer")

        outer = QVBoxLayout(self.container)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(16)

        # Прогресс-точки
        self._dots_layout = QHBoxLayout()
        self._dots_layout.setSpacing(6)
        self._dots_layout.addStretch()
        self._build_dots()
        self._dots_layout.addStretch()
        outer.addLayout(self._dots_layout)

        # Область слайдов — обрезаем контент по размеру
        self._slide_area = QWidget()
        self._slide_area.setFixedSize(384, 270)
        self._slide_area.setStyleSheet("background: transparent;")
        outer.addWidget(self._slide_area)

        # Создаём все страницы сразу
        self._pages = []
        for step in TUTORIAL_STEPS:
            page = StepPage(step)
            page.setParent(self._slide_area)
            page.setGeometry(0, 0, 384, 270)
            page.hide()
            self._pages.append(page)

        # Показываем первую страницу
        self._pages[0].show()

        # Кнопки
        btn_layout = QHBoxLayout()

        self._skip_btn = QPushButton("Пропустить всё")
        self._skip_btn.setObjectName("skipBtn")
        self._skip_btn.clicked.connect(self._skip_all)
        btn_layout.addWidget(self._skip_btn)

        btn_layout.addStretch()

        self._next_btn = QPushButton("Далее →")
        self._next_btn.clicked.connect(self._next)
        btn_layout.addWidget(self._next_btn)

        outer.addLayout(btn_layout)

        self._apply_style()
        self._slide_in()
        self.show()

    def _build_dots(self):
        """Строит индикатор прогресса из точек."""
        # Очищаем старые точки (кроме stretch-ов)
        while self._dots_layout.count() > 2:
            item = self._dots_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        # Перестраиваем
        for i in range(len(TUTORIAL_STEPS)):
            dot = QLabel("●" if i == self._current_index else "○")
            dot.setStyleSheet(
                "font-size: 14px; color: #0078D7;" if i == self._current_index
                else "font-size: 14px; color: #ccc;"
            )
            self._dots_layout.insertWidget(i + 1, dot)

    def _apply_style(self):
        self.setStyleSheet("""
        QFrame#tutContainer {
            background-color: rgba(255, 255, 255, 0.97);
            border-radius: 20px;
            border: 1px solid rgba(0, 120, 215, 0.25);
        }
        QPushButton {
            background-color: #0078D7;
            color: white;
            border-radius: 9px;
            padding: 9px 20px;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #005ea6;
        }
        QPushButton#skipBtn {
            background-color: transparent;
            color: #999;
            border: 1px solid #ddd;
        }
        QPushButton#skipBtn:hover {
            background-color: #f5f5f5;
            color: #666;
        }
        """)

    def _slide_in(self):
        """Окно въезжает снизу при открытии."""
        self._anim_win = QPropertyAnimation(self, b"pos")
        self._anim_win.setDuration(380)
        self._anim_win.setStartValue(QPoint(self._end_x, self._end_y + 300))
        self._anim_win.setEndValue(QPoint(self._end_x, self._end_y))
        self._anim_win.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_win.start()

    def _slide_out_window(self, callback):
        """Окно уезжает вниз при закрытии."""
        screen = QApplication.primaryScreen().availableGeometry()
        self._anim_close = QPropertyAnimation(self, b"pos")
        self._anim_close.setDuration(280)
        self._anim_close.setStartValue(QPoint(self._end_x, self._end_y))
        self._anim_close.setEndValue(QPoint(self._end_x, screen.bottom() + 10))
        self._anim_close.setEasingCurve(QEasingCurve.InCubic)
        self._anim_close.finished.connect(lambda: (self.close(), callback()))
        self._anim_close.start()

    def _animate_page_turn(self, old_idx, new_idx):
        """
        Анимация листания страницы:
        - Старая страница уезжает влево за край области
        - Новая страница въезжает справа
        """
        if self._animating:
            return
        self._animating = True

        w = self._slide_area.width()
        old_page = self._pages[old_idx]
        new_page = self._pages[new_idx]

        # Ставим новую страницу справа за видимой областью
        new_page.setGeometry(w, 0, w, self._slide_area.height())
        new_page.show()

        # Анимация старой — уезжает влево
        self._anim_old = QPropertyAnimation(old_page, b"geometry")
        self._anim_old.setDuration(320)
        self._anim_old.setStartValue(QRect(0, 0, w, self._slide_area.height()))
        self._anim_old.setEndValue(QRect(-w, 0, w, self._slide_area.height()))
        self._anim_old.setEasingCurve(QEasingCurve.InOutCubic)

        # Анимация новой — въезжает справа
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
        is_last = self._current_index == len(TUTORIAL_STEPS) - 1

        if is_last:
            self._slide_out_window(self._finish)
            return

        self._current_index += 1
        self._animate_page_turn(old_idx, self._current_index)
        self._build_dots()

        # Обновляем текст кнопки на последнем шаге
        if self._current_index == len(TUTORIAL_STEPS) - 1:
            self._next_btn.setText("Завершить ✓")

    def _skip_all(self):
        if self._animating:
            return
        self._slide_out_window(self._finish)

    def _finish(self):
        mark_tutorial_done()
        if self.on_finished:
            self.on_finished()

    # Перетаскивание окна
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPos() - self._drag_pos)
            # Обновляем конечную позицию для анимации закрытия
            self._end_x = self.pos().x()
            self._end_y = self.pos().y()


# ================================================================
# МЕНЕДЖЕР ТУТОРИАЛА
# ================================================================
class TutorialManager:
    def __init__(self, on_finished=None, skip_name=False):
        """
        on_finished — колбэк после завершения туториала.
        skip_name   — True если имя уже задано (вызов из трея).
                      В этом случае окно имени пропускается.
        """
        self.on_finished = on_finished
        self.skip_name   = skip_name

    def start(self):
        """
        Если имя уже задано — сразу показываем шаги туториала.
        Если нет — сначала окно ввода имени.
        """
        if self.skip_name or load_pet_name() is not None:
            self._window = TutorialWindow(on_finished=self._on_finished)
        else:
            self._name_dialog = PetNameDialog(on_name_saved=self._on_name_saved)

    def _on_name_saved(self, name):
        """Имя сохранено — запускаем шаги."""
        self._window = TutorialWindow(on_finished=self._on_finished)

    def _on_finished(self):
        if self.on_finished:
            self.on_finished()


# ================================================================
# ПУЗЫРЬ-НАПОМИНАНИЕ ОБ ИМЕНИ
# Показывается через 10 минут если имя не задано.
# ================================================================
class NameReminderBubble(QWidget):
    def __init__(self, on_name_now=None):
        super().__init__()

        self.on_name_now = on_name_now

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(340, 140)

        screen = QApplication.primaryScreen().availableGeometry()
        end_x = screen.right() - self.width() - 20
        end_y = screen.bottom() - self.height() - 20

        container = QFrame(self)
        container.setGeometry(0, 0, 340, 140)
        container.setObjectName("bubble")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        text = QLabel(
            "Эй, меня так и не назвали! 🐾\n"
            "Имя нужно для голосовых команд."
        )
        text.setWordWrap(True)
        text.setStyleSheet("font-size: 15px; color: white;")
        layout.addWidget(text)

        btn = QPushButton("Назвать сейчас")
        btn.clicked.connect(self._open_name_dialog)
        layout.addWidget(btn)

        self.setStyleSheet("""
        QFrame#bubble {
            background-color: rgba(40, 40, 40, 230);
            border-radius: 15px;
        }
        QPushButton {
            background-color: #0078D7;
            color: white;
            border-radius: 8px;
            padding: 7px;
            font-size: 14px;
        }
        QPushButton:hover { background-color: #005ea6; }
        """)

        # Анимация появления снизу
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
