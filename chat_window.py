# ================================================================
# ИМПОРТЫ
# ================================================================
import sys
import os
import threading

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QScrollArea, QFrame, QApplication,
    QDialog, QDialogButtonBox,
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize,
)
from PyQt5.QtGui import QFont, QTextCursor

from assistant import (
    process_message, load_history, clear_history,
    load_chat_settings, save_chat_settings,
    search_history, save_user_slang,
    load_user_prompt, save_user_prompt,
    add_to_history,
)
from config import load_pet_name


# ================================================================
# РАЗМЕРЫ ШРИФТА
# ================================================================
FONT_SIZES = {
    "small":  13,
    "medium": 15,
    "large":  18,
}



# ================================================================
# КАСТОМНЫЙ ГРИП ИЗМЕНЕНИЯ РАЗМЕРА
# В отличие от QSizeGrip не двигает окно при растягивании —
# меняет только ширину и высоту, верхний левый угол остаётся
# на месте.
# ================================================================
class _ResizeGrip(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.SizeFDiagCursor)
        self.setToolTip("Потяни чтобы изменить размер")
        self._resizing  = False
        self._start_pos = None
        self._start_size = None

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QColor
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        color = QColor(0, 120, 215, 80) if not self._resizing else QColor(0, 120, 215, 160)
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, 24, 24, 6, 6)
        # Три диагональные полоски
        p.setPen(QColor(0, 120, 215, 200))
        for i in range(3):
            offset = 6 + i * 5
            p.drawLine(offset, 22, 22, offset)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._resizing   = True
            self._start_pos  = event.globalPos()
            self._start_size = self.parent().size()
            self.update()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._resizing and self._start_pos:
            delta = event.globalPos() - self._start_pos
            new_w = max(320, self._start_size.width()  + delta.x())
            new_h = max(400, self._start_size.height() + delta.y())

            # Ограничиваем экраном
            screen = QApplication.primaryScreen().availableGeometry()
            win    = self.parent()
            max_w  = screen.right()  - win.pos().x() - 10
            max_h  = screen.bottom() - win.pos().y() - 10
            new_w  = min(new_w, max_w)
            new_h  = min(new_h, max_h)

            # Меняем только размер — позиция окна не трогается
            win.resize(new_w, new_h)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._resizing = False
        self.update()
        event.accept()


# ================================================================
# ПОТОК ДЛЯ ОБРАБОТКИ СООБЩЕНИЯ
# Запускается в отдельном потоке чтобы не блокировать UI.
# ================================================================
class MessageThread(QThread):
    finished        = pyqtSignal(str)  # ответ готов
    error_occurred  = pyqtSignal(str)  # ошибка
    events_changed  = pyqtSignal()     # события изменились — вызвать из главного потока

    def __init__(self, text, on_events_changed=None):
        super().__init__()
        self.text              = text
        self.on_events_changed = on_events_changed

    def run(self):
        try:
            # Передаём сигнал вместо прямого вызова колбэка
            def _notify():
                self.events_changed.emit()

            response = process_message(self.text, _notify)
            self.finished.emit(response)
        except Exception as e:
            self.error_occurred.emit(str(e))


# ================================================================
# ПУЗЫРЬ СООБЩЕНИЯ
# ================================================================
class MessageBubble(QFrame):
    def __init__(self, text, role, time_str, font_size, parent=None):
        super().__init__(parent)

        self.role      = role
        self._text     = text
        self._time_str = time_str

        is_user = role == "user"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Текст сообщения
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.set_font_size(font_size)
        layout.addWidget(self.text_label)

        # Время
        time_label = QLabel(time_str)
        time_label.setStyleSheet("font-size: 11px; color: #aaa;")
        time_label.setAlignment(Qt.AlignRight if is_user else Qt.AlignLeft)
        layout.addWidget(time_label)

        # Стиль пузыря
        if is_user:
            self.setStyleSheet("""
                QFrame {
                    background-color: #DCF1FF;
                    border-radius: 14px;
                    border-bottom-right-radius: 3px;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #F0F0F0;
                    border-radius: 14px;
                    border-bottom-left-radius: 3px;
                }
            """)

        # Макс. ширина пузыря задаётся снаружи методом set_max_width
        # (вызывается ChatWindow при resize). Дефолт безопасный — 280.
        self.setMaximumWidth(280)

    def set_max_width(self, w):
        """Меняет максимальную ширину пузыря (вызывается при ресайзе окна)."""
        self.setMaximumWidth(max(160, int(w)))

    def set_font_size(self, size_key):
        """Обновляет размер шрифта."""
        size = FONT_SIZES.get(size_key, 15)
        self.text_label.setStyleSheet(f"font-size: {size}px; color: #222;")

    def append_text(self, token):
        """Добавляет токен к тексту (для стриминга)."""
        self._text += token
        self.text_label.setText(self._text)


# ================================================================
# ИНДИКАТОР "ДУМАЮ / ПРОСЫПАЮСЬ"
# ================================================================
class ThinkingIndicator(QWidget):
    def __init__(self, mode="thinking", parent=None):
        """
        mode: "thinking"  — 🐾🐾🐾 Думаю...
              "waking_up" — 💭💭💭 Просыпаюсь, подожди...
        """
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self._icons  = ["🐾", "🐾", "🐾"] if mode == "thinking" else ["💭", "💭", "💭"]
        self._text   = "Думаю..." if mode == "thinking" else "Просыпаюсь, подожди..."
        self._step   = 0

        self.icons_label = QLabel(self._icons[0])
        self.icons_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(self.icons_label)

        self.text_label = QLabel(self._text)
        self.text_label.setStyleSheet("font-size: 13px; color: #888;")
        layout.addWidget(self.text_label)

        # Анимация — иконки появляются по очереди
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(400)

    def _tick(self):
        self._step = (self._step + 1) % 4
        if self._step == 0:
            self.icons_label.setText(self._icons[0])
        elif self._step == 1:
            self.icons_label.setText(f"{self._icons[0]} {self._icons[1]}")
        elif self._step == 2:
            self.icons_label.setText(f"{self._icons[0]} {self._icons[1]} {self._icons[2]}")
        else:
            self.icons_label.setText("")

    def set_status(self, text):
        """Обновляет текст статуса."""
        self.text_label.setText(text)

    def stop(self):
        self._timer.stop()


# ================================================================
# ДИАЛОГ ПОДТВЕРЖДЕНИЯ ОЧИСТКИ
# ================================================================
class ClearDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setFixedSize(280, 140)

        layout = QVBoxLayout(self)

        label = QLabel("Очистить всю историю чата?")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 15px;")
        layout.addWidget(label)

        buttons  = QDialogButtonBox()
        ok_btn   = QPushButton("Очистить")
        no_btn   = QPushButton("Отмена")
        buttons.addButton(ok_btn, QDialogButtonBox.AcceptRole)
        buttons.addButton(no_btn,  QDialogButtonBox.RejectRole)
        ok_btn.clicked.connect(self.accept)
        no_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet("""
        QDialog { background-color: white; border-radius: 15px; }
        QPushButton {
            background-color: #0078D7; color: white;
            border-radius: 8px; padding: 6px 12px;
        }
        QPushButton:hover { background-color: #005ea6; }
        """)


# ================================================================
# ОКНО ПОИСКА ПО ИСТОРИИ
# ================================================================
class SearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(380, 320)

        container = QFrame(self)
        container.setGeometry(0, 0, 380, 320)
        container.setObjectName("container")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        QLabel_title = QLabel("🔍 Поиск по истории")
        QLabel_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(QLabel_title)

        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Что ищем?")
        layout.addWidget(self.search_input)

        # Выбор периода
        period_label = QLabel("За какой период:")
        period_label.setStyleSheet("font-size: 13px; color: #555;")
        layout.addWidget(period_label)

        period_layout = QHBoxLayout()
        self.period_buttons = {}
        for label, days in [("Вчера", 1), ("3 дня", 3), ("Неделя", 7), ("Всё", None)]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("periodBtn")
            btn.clicked.connect(lambda _, d=days, b=btn: self._select_period(d, b))
            period_layout.addWidget(btn)
            self.period_buttons[label] = (btn, days)
        layout.addLayout(period_layout)

        self._selected_days = None
        # По умолчанию "Всё"
        self.period_buttons["Всё"][0].setChecked(True)

        # Результаты
        self.results_label = QLabel("")
        self.results_label.setWordWrap(True)
        self.results_label.setStyleSheet("font-size: 13px; color: #444;")
        layout.addWidget(self.results_label)

        # Кнопки
        btn_layout = QHBoxLayout()
        search_btn = QPushButton("Найти")
        close_btn  = QPushButton("Закрыть")
        close_btn.setObjectName("closeBtn")
        search_btn.clicked.connect(self._search)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        btn_layout.addWidget(search_btn)
        layout.addLayout(btn_layout)

        self.setStyleSheet("""
        QFrame#container {
            background-color: rgba(255,255,255,0.97);
            border-radius: 20px;
        }
        QLineEdit {
            border: 1px solid #ccc; border-radius: 6px;
            padding: 6px 10px; font-size: 14px;
        }
        QPushButton {
            background-color: #0078D7; color: white;
            border-radius: 8px; padding: 7px 14px; font-size: 13px;
        }
        QPushButton:hover { background-color: #005ea6; }
        QPushButton#periodBtn {
            background-color: #f0f0f0; color: #444;
            border: 1px solid #ddd;
        }
        QPushButton#periodBtn:checked {
            background-color: #0078D7; color: white;
        }
        QPushButton#closeBtn {
            background-color: transparent; color: #888;
            border: 1px solid #ddd;
        }
        """)

    def _select_period(self, days, btn):
        self._selected_days = days
        for label, (b, _) in self.period_buttons.items():
            b.setChecked(b == btn)

    def _search(self):
        query = self.search_input.text().strip()
        if not query:
            self.results_label.setText("Введи что искать")
            return

        results = search_history(query, self._selected_days)
        if not results:
            self.results_label.setText("Ничего не найдено 🐾")
            return

        lines = []
        for msg in results[-5:]:  # показываем последние 5 совпадений
            role = "Ты" if msg["role"] == "user" else "Питомец"
            lines.append(f"[{msg['time']}] {role}: {msg['text'][:80]}...")
        self.results_label.setText("\n\n".join(lines))



# ================================================================
# ОКНО НАСТРОЕК ПОМОЩНИКА
# Пользователь настраивает тон, рассказывает о себе,
# добавляет инструкции для помощника.
# ================================================================
class PromptSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 480)

        # Центрируем на экране
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )

        container = QFrame(self)
        container.setGeometry(0, 0, 420, 480)
        container.setObjectName("psContainer")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Заголовок
        title = QLabel("⚙️ Настройка помощника")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #222;")
        layout.addWidget(title)

        # Тон общения
        layout.addWidget(QLabel("Тон общения:"))
        from PyQt5.QtWidgets import QComboBox
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(["дружеский", "деловой", "краткий"])
        layout.addWidget(self.tone_combo)

        # О пользователе
        layout.addWidget(QLabel("О себе (необязательно):"))
        from PyQt5.QtWidgets import QTextEdit
        self.about_edit = QTextEdit()
        self.about_edit.setPlaceholderText(
            "Например: работаю дизайнером, не люблю длинные ответы, "
            "есть кот по имени Мурка..."
        )
        self.about_edit.setFixedHeight(90)
        layout.addWidget(self.about_edit)

        # Дополнительные инструкции
        layout.addWidget(QLabel("Дополнительные инструкции (необязательно):"))
        self.instr_edit = QTextEdit()
        self.instr_edit.setPlaceholderText(
            "Например: всегда отвечай на русском, "
            "объясняй термины простыми словами..."
        )
        self.instr_edit.setFixedHeight(90)
        layout.addWidget(self.instr_edit)

        # Уточнять если не понял
        from PyQt5.QtWidgets import QCheckBox
        self.ask_check = QCheckBox("Переспрашивать если не понял")
        self.ask_check.setChecked(True)
        layout.addWidget(self.ask_check)

        # Кнопки
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setObjectName("cancelBtn")
        save_btn   = QPushButton("Сохранить")
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        self._apply_style()
        self._load()

    def _apply_style(self):
        self.setStyleSheet("""
        QFrame#psContainer {
            background-color: rgba(255,255,255,0.97);
            border-radius: 20px;
        }
        QComboBox, QTextEdit {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 14px;
            background: white;
        }
        QCheckBox { font-size: 14px; color: #333; }
        QLabel { font-size: 13px; color: #444; }
        QPushButton {
            background-color: #0078D7; color: white;
            border-radius: 9px; padding: 9px 20px; font-size: 14px;
        }
        QPushButton:hover { background-color: #005ea6; }
        QPushButton#cancelBtn {
            background-color: transparent; color: #888;
            border: 1px solid #ddd;
        }
        QPushButton#cancelBtn:hover { background-color: #f5f5f5; }
        """)

    def _load(self):
        """Загружает текущие настройки в поля."""
        data = load_user_prompt()
        idx  = self.tone_combo.findText(data.get("tone", "дружеский"))
        if idx >= 0:
            self.tone_combo.setCurrentIndex(idx)
        self.about_edit.setPlainText(data.get("about_user", ""))
        self.instr_edit.setPlainText(data.get("instructions", ""))
        self.ask_check.setChecked(data.get("ask_if_unsure", True))

    def _save(self):
        """Сохраняет настройки и закрывает диалог."""
        save_user_prompt({
            "tone":         self.tone_combo.currentText(),
            "about_user":   self.about_edit.toPlainText().strip(),
            "instructions": self.instr_edit.toPlainText().strip(),
            "ask_if_unsure": self.ask_check.isChecked(),
        })
        self.accept()

    # Перетаскивание
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPos() - self._drag_pos)


# ================================================================
# ОСНОВНОЕ ОКНО ЧАТА
# ================================================================
class ChatWindow(QWidget):
    def __init__(self, parent=None, on_events_changed=None):
        super().__init__(parent)

        self._on_events_changed = on_events_changed
        self._settings    = load_chat_settings()
        self._font_size   = self._settings.get("font_size", "medium")
        self._is_thinking = False
        self._current_bubble = None
        self._last_response  = ""

        pet_name = load_pet_name() or "Питомец"

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Window |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        w = self._settings.get("window_width",  400)
        h = self._settings.get("window_height", 500)
        self.resize(w, h)
        self.setMinimumSize(380, 400)

        # Ограничиваем максимальный размер экраном
        screen = QApplication.primaryScreen().availableGeometry()
        self.setMaximumSize(screen.width() - 40, screen.height() - 40)

        # Позиция — рядом с питомцем (вычисляется снаружи при открытии)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.right() - self.width() - 20,
            screen.bottom() - self.height() - 60
        )

        # --------------------------------------------------------
        # КОНТЕЙНЕР
        # --------------------------------------------------------
        self.container = QFrame(self)
        self.container.setObjectName("chatContainer")
        self.container.setGeometry(0, 0, w, h)

        outer = QVBoxLayout(self.container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # --------------------------------------------------------
        # ШАПКА
        # --------------------------------------------------------
        header = QFrame()
        header.setObjectName("chatHeader")
        header.setFixedHeight(50)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(15, 0, 10, 0)
        header_layout.setSpacing(6)

        # Имя питомца
        name_label = QLabel(f"🐾 {pet_name}")
        name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #222;")
        header_layout.addWidget(name_label)
        header_layout.addStretch()

        # Кнопки шапки
        for icon, tip, slot in [
            ("A-",  "Уменьшить шрифт",      self._font_smaller),
            ("A+",  "Увеличить шрифт",      self._font_larger),
            ("🔍",  "Поиск по истории",     self._open_search),
            ("🗑",  "Очистить историю",     self._clear_history),
        ]:
            btn = QPushButton(icon)
            btn.setFixedSize(32, 32)
            btn.setToolTip(tip)
            btn.setObjectName("headerBtn")
            btn.clicked.connect(slot)
            header_layout.addWidget(btn)

        # Крестик
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self._on_close)
        header_layout.addWidget(close_btn)

        outer.addWidget(header)

        # --------------------------------------------------------
        # ОБЛАСТЬ СООБЩЕНИЙ
        # --------------------------------------------------------
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.messages_widget = QWidget()
        self.messages_widget.setStyleSheet("background: transparent;")
        self.messages_layout = QVBoxLayout(self.messages_widget)
        self.messages_layout.setContentsMargins(12, 12, 12, 12)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()

        self.scroll.setWidget(self.messages_widget)
        outer.addWidget(self.scroll)

        # --------------------------------------------------------
        # ПОЛЕ ВВОДА
        # --------------------------------------------------------
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_frame.setFixedHeight(55)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Напиши сюда...")
        self.input_field.setMaxLength(500)
        self.input_field.returnPressed.connect(self._send)
        input_layout.addWidget(self.input_field)

        send_btn = QPushButton("→")
        send_btn.setFixedSize(36, 36)
        send_btn.setObjectName("sendBtn")
        send_btn.clicked.connect(self._send)
        input_layout.addWidget(send_btn)

        outer.addWidget(input_frame)

        # Кастомный грип изменения размера
        self._grip = _ResizeGrip(self)
        self._grip.setFixedSize(24, 24)

        self._apply_style()
        self._load_history_messages()

    def resizeEvent(self, event):
        """Подгоняем контейнер и грип под текущий размер окна."""
        self.container.setGeometry(0, 0, self.width(), self.height())
        self._grip.move(self.width() - 24, self.height() - 24)

        # Пузырь не должен занимать больше 75% ширины окна,
        # но не меньше 200px и не больше 500px
        max_bubble = max(200, min(500, int(self.width() * 0.75)))
        for bubble in self.findChildren(MessageBubble):
            bubble.set_max_width(max_bubble)

        super().resizeEvent(event)

    def _apply_style(self):
        self.setStyleSheet("""
        QFrame#chatContainer {
            background-color: rgba(255, 255, 255, 0.97);
            border-radius: 20px;
        }
        QFrame#chatHeader {
            background-color: rgba(0, 120, 215, 0.08);
            border-top-left-radius: 20px;
            border-top-right-radius: 20px;
            border-bottom: 1px solid rgba(0,0,0,0.06);
        }
        QFrame#inputFrame {
            background-color: rgba(0,0,0,0.03);
            border-top: 1px solid rgba(0,0,0,0.06);
            border-bottom-left-radius: 20px;
            border-bottom-right-radius: 20px;
        }
        QLineEdit {
            border: 1px solid #ddd;
            border-radius: 18px;
            padding: 6px 14px;
            font-size: 14px;
            background: white;
        }
        QLineEdit:focus { border-color: #0078D7; }
        QPushButton#sendBtn {
            background-color: #0078D7;
            color: white;
            border-radius: 18px;
            font-size: 16px;
        }
        QPushButton#sendBtn:hover { background-color: #005ea6; }
        QPushButton#headerBtn {
            background-color: transparent;
            color: #555;
            border-radius: 6px;
            font-size: 13px;
        }
        QPushButton#headerBtn:hover { background-color: rgba(0,0,0,0.06); }
        QPushButton#closeBtn {
            background-color: transparent;
            color: #888;
            border-radius: 6px;
            font-size: 14px;
        }
        QPushButton#closeBtn:hover {
            background-color: #e81123;
            color: white;
        }
        """)

    # ----------------------------------------------------------------
    # ЗАПУСК OLLAMA
    # ----------------------------------------------------------------
    def _startup(self):
        """Проверяет состояние Ollama и запускает если нужно."""
        if is_ollama_running() and is_model_installed():
            self._load_history_messages()
            return

        # Показываем индикатор
        self._indicator = ThinkingIndicator(mode="waking_up")
        self._add_widget_to_chat(self._indicator, align="left")

        self._startup_thread = StartupThread()
        self._startup_thread.status.connect(self._on_startup_status)
        self._startup_thread.ready.connect(self._on_startup_ready)
        self._startup_thread.failed.connect(self._on_startup_failed)
        self._startup_thread.start()

    def _on_startup_status(self, status):
        if hasattr(self, "_indicator"):
            self._indicator.set_status(status)

    def _on_startup_ready(self):
        if hasattr(self, "_indicator"):
            self._indicator.stop()
            self._indicator.hide()
        self._load_history_messages()

    def _on_startup_failed(self, reason):
        if hasattr(self, "_indicator"):
            self._indicator.stop()
            self._indicator.hide()

        if reason == "not_installed":
            self._add_system_message(
                "Чтобы я мог отвечать на твои вопросы,\n"
                "нужно установить один компонент —\n"
                "это бесплатно и займёт пару минут 🐾"
            )
            btn = QPushButton("⬇ Установить компонент")
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078D7;
                    color: white;
                    border-radius: 10px;
                    padding: 8px 16px;
                    font-size: 14px;
                }
                QPushButton:hover { background-color: #005ea6; }
            """)
            btn.clicked.connect(
                lambda: webbrowser.open("https://ollama.com/download/windows")
            )
            row = QHBoxLayout()
            row.addWidget(btn)
            row.addStretch()
            self.messages_layout.insertLayout(
                self.messages_layout.count() - 1, row
            )
            self._add_system_message(
                "После установки можно его закрыть —\n"
                "я запущу всё сам когда понадоблюсь.\n"
                "Затем закрой и открой чат заново."
            )
        elif reason == "cant_download":
            self._add_system_message(
                "Не удалось скачать модель.\n"
                "Проверь интернет-соединение и попробуй снова 🐾"
            )
        else:
            self._add_system_message(
                "Что-то пошло не так при запуске помощника.\n"
                "Попробуй перезапустить приложение 🐾"
            )

    # ----------------------------------------------------------------
    # ЗАГРУЗКА ИСТОРИИ
    # ----------------------------------------------------------------
    def _load_history_messages(self):
        """Загружает последние сообщения из истории в UI."""
        history = load_history()
        # Показываем последние 20 сообщений
        for msg in history[-20:]:
            self._add_bubble(
                text=msg["text"],
                role=msg["role"],
                time_str=msg.get("time", ""),
            )
        self._scroll_to_bottom()

    # ----------------------------------------------------------------
    # ДОБАВЛЕНИЕ СООБЩЕНИЙ В UI
    # ----------------------------------------------------------------
    def _add_bubble(self, text, role, time_str=""):
        """Добавляет пузырь сообщения в чат."""
        bubble = MessageBubble(text, role, time_str, self._font_size)
        # Сразу подстраиваем под текущую ширину окна
        max_bubble = max(200, min(500, int(self.width() * 0.75)))
        bubble.set_max_width(max_bubble)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)

        if role == "user":
            row.addStretch()
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch()

        # Вставляем перед stretch в конце
        self.messages_layout.insertLayout(
            self.messages_layout.count() - 1, row
        )

        self._scroll_to_bottom()
        return bubble

    def _add_widget_to_chat(self, widget, align="left"):
        """Добавляет произвольный виджет в область чата."""
        row = QHBoxLayout()
        if align == "right":
            row.addStretch()
            row.addWidget(widget)
        else:
            row.addWidget(widget)
            row.addStretch()
        self.messages_layout.insertLayout(
            self.messages_layout.count() - 1, row
        )
        self._scroll_to_bottom()

    def _add_system_message(self, text):
        """Добавляет системное сообщение (по центру, серый текст)."""
        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(
            "font-size: 13px; color: #888; padding: 8px;"
        )
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(label)
        row.addStretch()
        self.messages_layout.insertLayout(
            self.messages_layout.count() - 1, row
        )
        self._scroll_to_bottom()

    def _add_quick_buttons(self, labels):
        """
        Добавляет ряд кликабельных кнопок-подсказок под последним сообщением.
        Кнопки автоматически переносятся на следующую строку, если не влезают.
        После клика весь ряд исчезает, а текст кнопки отправляется в чат.
        """
        # Контейнер с вертикальным layout — внутри несколько горизонтальных
        # рядов с кнопками. Это даёт авто-перенос без необходимости в FlowLayout.
        container = QWidget()
        container.setStyleSheet("background: transparent;")

        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 4, 0, 4)
        outer.setSpacing(6)

        def make_handler(text, holder):
            def handler():
                holder.hide()
                holder.deleteLater()
                self.input_field.setText(text)
                self._send()
            return handler

        # Оценим, сколько кнопок поместится в ряд. Берём 80% ширины окна
        # минус padding. Если окно ещё не инициализировано (width=0),
        # используем минимальную ширину (380 — minimumWidth главного окна).
        win_w = max(self.width(), self.minimumWidth(), 380)
        avail_w = max(220, int(win_w * 0.80) - 32)

        # Считаем приблизительную ширину каждой кнопки по длине текста
        widths = []
        for label in labels:
            # Эмпирически: 9px на символ + 28px паддинг. Минимум 70px.
            w = max(70, len(label) * 9 + 28)
            widths.append(w)

        # Группируем кнопки по рядам так, чтоб ряд не превышал avail_w
        rows = []
        current = []
        current_w = 0
        for label, w in zip(labels, widths):
            # +6 на spacing
            if current and current_w + w + 6 > avail_w:
                rows.append(current)
                current = []
                current_w = 0
            current.append(label)
            current_w += w + 6
        if current:
            rows.append(current)

        # Создаём ряды
        for row_labels in rows:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            for label in row_labels:
                btn = QPushButton(label)
                btn.setObjectName("quickBtn")
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton#quickBtn {
                        background-color: rgba(0, 120, 215, 0.10);
                        color: #0078D7;
                        border: 1px solid rgba(0, 120, 215, 0.35);
                        border-radius: 14px;
                        padding: 6px 14px;
                        font-size: 13px;
                    }
                    QPushButton#quickBtn:hover {
                        background-color: rgba(0, 120, 215, 0.20);
                    }
                """)
                btn.clicked.connect(make_handler(label, container))
                row.addWidget(btn)
            row.addStretch()
            outer.addLayout(row)

        row = QHBoxLayout()
        row.setContentsMargins(8, 0, 8, 0)
        row.addWidget(container)

        self.messages_layout.insertLayout(
            self.messages_layout.count() - 1, row
        )
        self._scroll_to_bottom()


    def _scroll_to_bottom(self):
        """Прокручивает чат вниз."""
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))

    # ----------------------------------------------------------------
    # ОТПРАВКА СООБЩЕНИЯ
    # ----------------------------------------------------------------
    def _send(self):
        """Отправляет сообщение пользователя."""
        if self._is_thinking:
            return

        text = self.input_field.text().strip()
        if not text:
            return

        self.input_field.clear()
        self.input_field.setEnabled(False)

        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M")

        # Сохраняем и показываем пузырь пользователя
        add_to_history("user", text)
        self._add_bubble(text, "user", time_str)

        # Индикатор "думаю"
        self._indicator = ThinkingIndicator(mode="thinking")
        self._add_widget_to_chat(self._indicator, align="left")
        self._is_thinking = True

        # Запускаем обработку в потоке
        self._thread = MessageThread(text, self._on_events_changed)
        self._thread.finished.connect(self._on_response_done)
        self._thread.error_occurred.connect(self._on_error)
        if self._on_events_changed:
            self._thread.events_changed.connect(self._on_events_changed)
        self._thread.start()

    def _on_response_done(self, response):
        """Ответ готов — показываем пузырь и кнопки-подсказки если нужно."""
        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M")

        if hasattr(self, "_indicator"):
            self._indicator.stop()
            self._indicator.hide()

        add_to_history("assistant", response)
        self._add_bubble(response, "assistant", time_str)

        # Показываем кнопку "Пропустить" если спрашиваем про возраст / год рождения
        if "Пропустить" in response or ("Сколько лет" in response and "пропустить" in response.lower()):
            self._add_quick_buttons(["Пропустить"])

        # Показываем варианты повтора (для событий)
        if "Как часто повторяется" in response:
            self._add_quick_buttons([
                "Один раз", "Каждый день", "Каждую неделю",
                "Каждый месяц", "Каждый год"
            ])

        # За сколько до события напомнить (для событий)
        if "За сколько до события напомнить" in response:
            self._add_quick_buttons([
                "В момент", "За 15 мин", "За 30 мин", "За час", "За день"
            ])

        # Что исправить в событии
        if "Что исправить?" in response and "дату, время" in response:
            self._add_quick_buttons(["Дата", "Время", "Название", "Повтор"])

        # Двуполое имя — кнопки выбора пола
        if "бывает мужским и женским" in response:
            self._add_quick_buttons(["👨 Мужское", "👩 Женское"])

        # Время напоминания для ДР
        if "В какое время напомнить" in response:
            self._add_quick_buttons(["09:00", "12:00", "19:00"])

        # За сколько до даты напомнить (для ДР)
        if "За сколько до даты напомнить" in response:
            self._add_quick_buttons([
                "В день", "За день", "За 3 дня", "За неделю"
            ])

        # Как часто напоминать (для ДР)
        if "Как часто напоминать" in response:
            self._add_quick_buttons([
                "Каждый год", "Каждый месяц", "Без повтора"
            ])

        self._is_thinking = False
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def _on_error(self, error):
        """Ошибка при обработке."""
        if hasattr(self, "_indicator"):
            self._indicator.stop()
            self._indicator.hide()
        self._add_system_message("Что-то пошло не так. Попробуй ещё раз 🐾")
        self._is_thinking = False
        self.input_field.setEnabled(True)

    # ----------------------------------------------------------------
    # ШРИФТ
    # ----------------------------------------------------------------
    def _font_smaller(self):
        sizes = list(FONT_SIZES.keys())
        idx   = sizes.index(self._font_size)
        if idx > 0:
            self._font_size = sizes[idx - 1]
            self._save_settings()

    def _font_larger(self):
        sizes = list(FONT_SIZES.keys())
        idx   = sizes.index(self._font_size)
        if idx < len(sizes) - 1:
            self._font_size = sizes[idx + 1]
            self._save_settings()

    # ----------------------------------------------------------------
    # ПОИСК
    # ----------------------------------------------------------------
    def _open_prompt_settings(self):
        """Открывает окно настройки помощника."""
        dialog = PromptSettingsDialog(self)
        dialog.exec_()

    def _open_search(self):
        self._search_dialog = SearchDialog(self)
        self._search_dialog.show()

    # ----------------------------------------------------------------
    # ОЧИСТКА ИСТОРИИ
    # ----------------------------------------------------------------
    def _clear_history(self):
        dialog = ClearDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            clear_history()
            # Очищаем UI
            while self.messages_layout.count() > 1:
                item = self.messages_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())
            self._add_system_message("История очищена 🐾")

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # ----------------------------------------------------------------
    # СОХРАНЕНИЕ НАСТРОЕК
    # ----------------------------------------------------------------
    def _save_settings(self):
        self._settings["font_size"]     = self._font_size
        self._settings["window_width"]  = self.width()
        self._settings["window_height"] = self.height()
        save_chat_settings(self._settings)

    # ----------------------------------------------------------------
    # ЗАКРЫТИЕ
    # ----------------------------------------------------------------
    def _on_close(self):
        """Закрывает окно и сохраняет настройки."""
        self._save_settings()
        self.close()

    # ----------------------------------------------------------------
    # ПЕРЕТАСКИВАНИЕ
    # ----------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPos() - self._drag_pos)
