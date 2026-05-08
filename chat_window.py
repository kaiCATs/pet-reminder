# ================================================================
# CHAT WINDOW
# Uses storage (replaces config/assistant settings imports).
# All UI strings come from locale_app.t().
# ================================================================

import os
import threading

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit,
    QScrollArea, QFrame, QApplication,
    QDialog, QDialogButtonBox, QComboBox,
    QTextEdit, QCheckBox,
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QPainter, QColor

from assistant import process_message, load_history, clear_history, search_history, add_to_history
import storage
from locale_app import t

FONT_SIZES = {"small": 13, "medium": 15, "large": 18}


# ================================================================
# RESIZE GRIP
# ================================================================
class _ResizeGrip(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.SizeFDiagCursor)
        self.setToolTip(t("chat_resize_tip"))
        self._resizing   = False
        self._start_pos  = None
        self._start_size = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        color = QColor(0, 120, 215, 80) if not self._resizing else QColor(0, 120, 215, 160)
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, 24, 24, 6, 6)
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

    def mouseMoveEvent(self, event):
        if self._resizing and self._start_pos:
            delta = event.globalPos() - self._start_pos
            new_w = max(320, self._start_size.width()  + delta.x())
            new_h = max(400, self._start_size.height() + delta.y())
            screen = QApplication.primaryScreen().availableGeometry()
            win    = self.parent()
            new_w  = min(new_w, screen.right()  - win.pos().x() - 10)
            new_h  = min(new_h, screen.bottom() - win.pos().y() - 10)
            win.resize(new_w, new_h)

    def mouseReleaseEvent(self, event):
        self._resizing = False
        self.update()


# ================================================================
# MESSAGE THREAD
# ================================================================
class MessageThread(QThread):
    finished       = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    events_changed = pyqtSignal()

    def __init__(self, text, on_events_changed=None):
        super().__init__()
        self.text              = text
        self.on_events_changed = on_events_changed

    def run(self):
        try:
            response = process_message(self.text, lambda: self.events_changed.emit())
            self.finished.emit(response)
        except Exception as e:
            self.error_occurred.emit(str(e))


# ================================================================
# MESSAGE BUBBLE
# ================================================================
class MessageBubble(QFrame):
    def __init__(self, text, role, time_str, font_size, parent=None):
        super().__init__(parent)
        self.role  = role
        self._text = text
        is_user    = role == "user"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.set_font_size(font_size)
        layout.addWidget(self.text_label)

        time_label = QLabel(time_str)
        time_label.setStyleSheet("font-size: 11px; color: #aaa;")
        time_label.setAlignment(Qt.AlignRight if is_user else Qt.AlignLeft)
        layout.addWidget(time_label)

        if is_user:
            self.setStyleSheet("""
                QFrame { background-color: #DCF1FF; border-radius: 14px; border-bottom-right-radius: 3px; }
            """)
        else:
            self.setStyleSheet("""
                QFrame { background-color: #F0F0F0; border-radius: 14px; border-bottom-left-radius: 3px; }
            """)
        self.setMaximumWidth(280)

    def set_max_width(self, w):
        self.setMaximumWidth(max(160, int(w)))

    def set_font_size(self, size_key):
        size = FONT_SIZES.get(size_key, 15)
        self.text_label.setStyleSheet(f"font-size: {size}px; color: #222;")

    def append_text(self, token):
        self._text += token
        self.text_label.setText(self._text)


# ================================================================
# THINKING INDICATOR
# ================================================================
class ThinkingIndicator(QWidget):
    def __init__(self, mode="thinking", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self._icons = ["🐾", "🐾", "🐾"] if mode == "thinking" else ["💭", "💭", "💭"]
        self._label_text = t("chat_thinking") if mode == "thinking" else t("chat_waking")
        self._step  = 0

        self.icons_label = QLabel(self._icons[0])
        self.icons_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(self.icons_label)

        self.text_label = QLabel(self._label_text)
        self.text_label.setStyleSheet("font-size: 13px; color: #888;")
        layout.addWidget(self.text_label)

        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._timer.start(400)

    def _tick(self):
        self._step = (self._step + 1) % 4
        icons = self._icons
        self.icons_label.setText(
            icons[0] if self._step == 0 else
            f"{icons[0]} {icons[1]}" if self._step == 1 else
            f"{icons[0]} {icons[1]} {icons[2]}" if self._step == 2 else ""
        )

    def set_status(self, text):
        self.text_label.setText(text)

    def stop(self):
        self._timer.stop()


# ================================================================
# CLEAR HISTORY DIALOG
# ================================================================
class ClearDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setFixedSize(280, 140)
        layout = QVBoxLayout(self)
        label = QLabel(t("chat_clear_q"))
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 15px;")
        layout.addWidget(label)
        buttons  = QDialogButtonBox()
        ok_btn   = QPushButton(t("chat_clear_ok"))
        no_btn   = QPushButton(t("ev_cancel"))
        buttons.addButton(ok_btn, QDialogButtonBox.AcceptRole)
        buttons.addButton(no_btn, QDialogButtonBox.RejectRole)
        ok_btn.clicked.connect(self.accept)
        no_btn.clicked.connect(self.reject)
        layout.addWidget(buttons)
        self.setStyleSheet("""
        QDialog { background-color: white; border-radius: 15px; }
        QPushButton { background-color: #0078D7; color: white; border-radius: 8px; padding: 6px 12px; }
        QPushButton:hover { background-color: #005ea6; }
        """)


# ================================================================
# SEARCH DIALOG
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

        layout.addWidget(QLabel(t("search_title")))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("search_ph"))
        layout.addWidget(self.search_input)

        period_label = QLabel(t("search_period"))
        period_label.setStyleSheet("font-size: 13px; color: #555;")
        layout.addWidget(period_label)

        period_layout = QHBoxLayout()
        self.period_buttons = {}
        periods = [
            (t("search_yesterday"), 1),
            (t("search_3days"), 3),
            (t("search_week"), 7),
            (t("search_all"), None),
        ]
        for label, days in periods:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("periodBtn")
            btn.clicked.connect(lambda _, d=days, b=btn: self._select_period(d, b))
            period_layout.addWidget(btn)
            self.period_buttons[label] = (btn, days)
        layout.addLayout(period_layout)

        self._selected_days = None
        # Default = All
        list(self.period_buttons.values())[-1][0].setChecked(True)

        self.results_label = QLabel("")
        self.results_label.setWordWrap(True)
        self.results_label.setStyleSheet("font-size: 13px; color: #444;")
        layout.addWidget(self.results_label)

        btn_layout = QHBoxLayout()
        search_btn = QPushButton(t("search_btn"))
        close_btn  = QPushButton(t("search_close"))
        close_btn.setObjectName("closeBtn")
        search_btn.clicked.connect(self._search)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        btn_layout.addWidget(search_btn)
        layout.addLayout(btn_layout)

        self.setStyleSheet("""
        QFrame#container { background-color: rgba(255,255,255,0.97); border-radius: 20px; }
        QLabel { font-size: 16px; font-weight: bold; }
        QLineEdit { border: 1px solid #ccc; border-radius: 6px; padding: 6px 10px; font-size: 14px; }
        QPushButton { background-color: #0078D7; color: white; border-radius: 8px; padding: 7px 14px; font-size: 13px; }
        QPushButton:hover { background-color: #005ea6; }
        QPushButton#periodBtn { background-color: #f0f0f0; color: #444; border: 1px solid #ddd; }
        QPushButton#periodBtn:checked { background-color: #0078D7; color: white; }
        QPushButton#closeBtn { background-color: transparent; color: #888; border: 1px solid #ddd; }
        """)

    def _select_period(self, days, btn):
        self._selected_days = days
        for _, (b, _) in self.period_buttons.items():
            b.setChecked(b == btn)

    def _search(self):
        query = self.search_input.text().strip()
        if not query:
            self.results_label.setText(t("search_empty"))
            return
        results = search_history(query, self._selected_days)
        if not results:
            self.results_label.setText(t("search_none"))
            return
        lines = []
        for msg in results[-5:]:
            role = t("search_you") if msg["role"] == "user" else t("search_pet")
            lines.append(f"[{msg['time']}] {role}: {msg['text'][:80]}...")
        self.results_label.setText("\n\n".join(lines))


# ================================================================
# PROMPT SETTINGS DIALOG
# ================================================================
class PromptSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 480)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - 210, screen.center().y() - 240)

        container = QFrame(self)
        container.setGeometry(0, 0, 420, 480)
        container.setObjectName("psContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        layout.addWidget(QLabel(t("ps_title")))

        layout.addWidget(QLabel(t("ps_tone")))
        self.tone_combo = QComboBox()
        self.tone_combo.addItems([t("ps_tone_friendly"), t("ps_tone_business"), t("ps_tone_brief")])
        layout.addWidget(self.tone_combo)

        layout.addWidget(QLabel(t("ps_about")))
        self.about_edit = QTextEdit()
        self.about_edit.setPlaceholderText(t("ps_about_ph"))
        self.about_edit.setFixedHeight(90)
        layout.addWidget(self.about_edit)

        layout.addWidget(QLabel(t("ps_instr")))
        self.instr_edit = QTextEdit()
        self.instr_edit.setPlaceholderText(t("ps_instr_ph"))
        self.instr_edit.setFixedHeight(90)
        layout.addWidget(self.instr_edit)

        self.ask_check = QCheckBox(t("ps_ask"))
        self.ask_check.setChecked(True)
        layout.addWidget(self.ask_check)

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton(t("ps_cancel"))
        cancel_btn.setObjectName("cancelBtn")
        save_btn   = QPushButton(t("ps_save"))
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        self.setStyleSheet("""
        QFrame#psContainer { background-color: rgba(255,255,255,0.97); border-radius: 20px; }
        QComboBox, QTextEdit { border: 1px solid #ddd; border-radius: 8px; padding: 6px 10px; font-size: 14px; background: white; }
        QCheckBox { font-size: 14px; color: #333; }
        QLabel { font-size: 13px; color: #444; }
        QPushButton { background-color: #0078D7; color: white; border-radius: 9px; padding: 9px 20px; font-size: 14px; }
        QPushButton:hover { background-color: #005ea6; }
        QPushButton#cancelBtn { background-color: transparent; color: #888; border: 1px solid #ddd; }
        QPushButton#cancelBtn:hover { background-color: #f5f5f5; }
        """)
        self._load()

    def _load(self):
        data = storage.load_user_prompt()
        # Map stored tone key to localised display
        tone_map = {"дружеский": t("ps_tone_friendly"), "friendly": t("ps_tone_friendly"),
                    "деловой": t("ps_tone_business"), "business": t("ps_tone_business"),
                    "краткий": t("ps_tone_brief"), "brief": t("ps_tone_brief")}
        display_tone = tone_map.get(data.get("tone", "дружеский"), t("ps_tone_friendly"))
        idx = self.tone_combo.findText(display_tone)
        if idx >= 0:
            self.tone_combo.setCurrentIndex(idx)
        self.about_edit.setPlainText(data.get("about_user", ""))
        self.instr_edit.setPlainText(data.get("instructions", ""))
        self.ask_check.setChecked(data.get("ask_if_unsure", True))

    def _save(self):
        # Store tone as internal key
        tone_display = self.tone_combo.currentText()
        tone_reverse = {t("ps_tone_friendly"): "friendly",
                        t("ps_tone_business"): "business",
                        t("ps_tone_brief"): "brief"}
        storage.save_user_prompt({
            "tone":          tone_reverse.get(tone_display, "friendly"),
            "about_user":    self.about_edit.toPlainText().strip(),
            "instructions":  self.instr_edit.toPlainText().strip(),
            "ask_if_unsure": self.ask_check.isChecked(),
        })
        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPos() - self._drag_pos)


# ================================================================
# MAIN CHAT WINDOW
# ================================================================
class ChatWindow(QWidget):
    def __init__(self, parent=None, on_events_changed=None):
        super().__init__(parent)
        self._on_events_changed = on_events_changed
        self._settings    = storage.load_chat_settings()
        self._font_size   = self._settings.get("font_size", "medium")
        self._is_thinking = False

        pet_name = storage.load_pet_name() or "Pet"

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        w = self._settings.get("window_width",  400)
        h = self._settings.get("window_height", 500)
        self.resize(w, h)
        self.setMinimumSize(380, 400)

        screen = QApplication.primaryScreen().availableGeometry()
        self.setMaximumSize(screen.width() - 40, screen.height() - 40)
        self.move(screen.right() - w - 20, screen.bottom() - h - 60)

        # Container
        self.container = QFrame(self)
        self.container.setObjectName("chatContainer")
        self.container.setGeometry(0, 0, w, h)

        outer = QVBoxLayout(self.container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("chatHeader")
        header.setFixedHeight(50)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(15, 0, 10, 0)
        header_layout.setSpacing(6)

        name_label = QLabel(f"🐾 {pet_name}")
        name_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #222;")
        header_layout.addWidget(name_label)
        header_layout.addStretch()

        for icon, tip_key, slot in [
            ("A-", "chat_font_down",   self._font_smaller),
            ("A+", "chat_font_up",     self._font_larger),
            ("🔍", "chat_search_tip",  self._open_search),
            ("🗑", "chat_clear_tip",   self._clear_history),
        ]:
            btn = QPushButton(icon)
            btn.setFixedSize(32, 32)
            btn.setToolTip(t(tip_key))
            btn.setObjectName("headerBtn")
            btn.clicked.connect(slot)
            header_layout.addWidget(btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self._on_close)
        header_layout.addWidget(close_btn)
        outer.addWidget(header)

        # Messages area
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

        # Input
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_frame.setFixedHeight(55)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(t("chat_placeholder"))
        self.input_field.setMaxLength(500)
        self.input_field.returnPressed.connect(self._send)
        input_layout.addWidget(self.input_field)

        send_btn = QPushButton("→")
        send_btn.setFixedSize(36, 36)
        send_btn.setObjectName("sendBtn")
        send_btn.clicked.connect(self._send)
        input_layout.addWidget(send_btn)
        outer.addWidget(input_frame)

        self._grip = _ResizeGrip(self)
        self._grip.setFixedSize(24, 24)

        self._apply_style()
        self._load_history_messages()

    def resizeEvent(self, event):
        self.container.setGeometry(0, 0, self.width(), self.height())
        self._grip.move(self.width() - 24, self.height() - 24)
        max_bubble = max(200, min(500, int(self.width() * 0.75)))
        for bubble in self.findChildren(MessageBubble):
            bubble.set_max_width(max_bubble)
        super().resizeEvent(event)

    def _apply_style(self):
        self.setStyleSheet("""
        QFrame#chatContainer { background-color: rgba(255,255,255,0.97); border-radius: 20px; }
        QFrame#chatHeader {
            background-color: rgba(0,120,215,0.08);
            border-top-left-radius: 20px; border-top-right-radius: 20px;
            border-bottom: 1px solid rgba(0,0,0,0.06);
        }
        QFrame#inputFrame {
            background-color: rgba(0,0,0,0.03);
            border-top: 1px solid rgba(0,0,0,0.06);
            border-bottom-left-radius: 20px; border-bottom-right-radius: 20px;
        }
        QLineEdit { border: 1px solid #ddd; border-radius: 18px; padding: 6px 14px; font-size: 14px; background: white; }
        QLineEdit:focus { border-color: #0078D7; }
        QPushButton#sendBtn { background-color: #0078D7; color: white; border-radius: 18px; font-size: 16px; }
        QPushButton#sendBtn:hover { background-color: #005ea6; }
        QPushButton#headerBtn { background-color: transparent; color: #555; border-radius: 6px; font-size: 13px; }
        QPushButton#headerBtn:hover { background-color: rgba(0,0,0,0.06); }
        QPushButton#closeBtn { background-color: transparent; color: #888; border-radius: 6px; font-size: 14px; }
        QPushButton#closeBtn:hover { background-color: #e81123; color: white; }
        """)

    def _load_history_messages(self):
        for msg in load_history()[-20:]:
            self._add_bubble(msg["text"], msg["role"], msg.get("time", ""))
        self._scroll_to_bottom()

    def _add_bubble(self, text, role, time_str=""):
        bubble = MessageBubble(text, role, time_str, self._font_size)
        bubble.set_max_width(max(200, min(500, int(self.width() * 0.75))))
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        if role == "user":
            row.addStretch(); row.addWidget(bubble)
        else:
            row.addWidget(bubble); row.addStretch()
        self.messages_layout.insertLayout(self.messages_layout.count() - 1, row)
        self._scroll_to_bottom()
        return bubble

    def _add_widget_to_chat(self, widget, align="left"):
        row = QHBoxLayout()
        if align == "right":
            row.addStretch(); row.addWidget(widget)
        else:
            row.addWidget(widget); row.addStretch()
        self.messages_layout.insertLayout(self.messages_layout.count() - 1, row)
        self._scroll_to_bottom()

    def _add_system_message(self, text):
        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 13px; color: #888; padding: 8px;")
        row = QHBoxLayout()
        row.addStretch(); row.addWidget(label); row.addStretch()
        self.messages_layout.insertLayout(self.messages_layout.count() - 1, row)
        self._scroll_to_bottom()

    def _add_quick_buttons(self, labels):
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 4, 0, 4)
        outer.setSpacing(6)

        def make_handler(text, holder):
            def handler():
                holder.hide(); holder.deleteLater()
                self.input_field.setText(text); self._send()
            return handler

        win_w  = max(self.width(), self.minimumWidth(), 380)
        avail_w = max(220, int(win_w * 0.80) - 32)
        widths  = [max(70, len(label) * 9 + 28) for label in labels]

        rows, current, current_w = [], [], 0
        for label, w in zip(labels, widths):
            if current and current_w + w + 6 > avail_w:
                rows.append(current); current = []; current_w = 0
            current.append(label); current_w += w + 6
        if current:
            rows.append(current)

        for row_labels in rows:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0); row.setSpacing(6)
            for label in row_labels:
                btn = QPushButton(label)
                btn.setObjectName("quickBtn")
                btn.setCursor(Qt.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton#quickBtn {
                        background-color: rgba(0,120,215,0.10); color: #0078D7;
                        border: 1px solid rgba(0,120,215,0.35);
                        border-radius: 14px; padding: 6px 14px; font-size: 13px;
                    }
                    QPushButton#quickBtn:hover { background-color: rgba(0,120,215,0.20); }
                """)
                btn.clicked.connect(make_handler(label, container))
                row.addWidget(btn)
            row.addStretch()
            outer.addLayout(row)

        row = QHBoxLayout()
        row.setContentsMargins(8, 0, 8, 0)
        row.addWidget(container)
        self.messages_layout.insertLayout(self.messages_layout.count() - 1, row)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))

    # ----------------------------------------------------------------
    # SEND / RESPONSE
    # ----------------------------------------------------------------
    def _send(self):
        if self._is_thinking:
            return
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()
        self.input_field.setEnabled(False)

        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M")
        add_to_history("user", text)
        self._add_bubble(text, "user", time_str)

        self._indicator = ThinkingIndicator(mode="thinking")
        self._add_widget_to_chat(self._indicator, align="left")
        self._is_thinking = True

        self._thread = MessageThread(text, self._on_events_changed)
        self._thread.finished.connect(self._on_response_done)
        self._thread.error_occurred.connect(self._on_error)
        if self._on_events_changed:
            self._thread.events_changed.connect(self._on_events_changed)
        self._thread.start()

    def _on_response_done(self, response):
        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M")
        if hasattr(self, "_indicator"):
            self._indicator.stop(); self._indicator.hide()
        add_to_history("assistant", response)
        self._add_bubble(response, "assistant", time_str)

        # Quick buttons — detect by localised phrases inside response
        lang = storage.current_language()

        def _has(*phrases):
            return any(p in response for p in phrases)

        if _has("Пропустить", "Skip"):
            self._add_quick_buttons([t("qb_skip")])

        if _has("Как часто повторяется", "How often does it repeat"):
            self._add_quick_buttons([
                t("qb_once"), t("qb_every_day"), t("qb_every_week"),
                t("qb_every_month"), t("qb_every_year"),
            ])

        if _has("За сколько до события напомнить", "How long before the event"):
            self._add_quick_buttons([
                t("qb_at_time"), t("qb_15min"), t("qb_30min"),
                t("qb_1hour"),   t("qb_1day"),
            ])

        if _has("Что исправить", "What to change"):
            if lang == "ru":
                self._add_quick_buttons(["Дата", "Время", "Название", "Повтор"])
            else:
                self._add_quick_buttons(["Date", "Time", "Title", "Repeat"])

        if _has("мужским и женским", "male or female"):
            self._add_quick_buttons([t("qb_male"), t("qb_female")])

        if _has("В какое время напомнить", "What time should I remind"):
            self._add_quick_buttons(["09:00", "12:00", "19:00"])

        if _has("За сколько до даты напомнить", "How far in advance"):
            self._add_quick_buttons([
                t("qb_on_day"), t("qb_1day"), t("qb_3days"), t("qb_1week"),
            ])

        if _has("Как часто напоминать", "How often should I remind"):
            self._add_quick_buttons([
                t("qb_every_year"), t("qb_every_month"), t("qb_skip"),
            ])

        self._is_thinking = False
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def _on_error(self, error):
        if hasattr(self, "_indicator"):
            self._indicator.stop(); self._indicator.hide()
        self._add_system_message(t("chat_error"))
        self._is_thinking = False
        self.input_field.setEnabled(True)

    # ----------------------------------------------------------------
    # FONT / SEARCH / CLEAR
    # ----------------------------------------------------------------
    def _font_smaller(self):
        keys = list(FONT_SIZES.keys())
        idx  = keys.index(self._font_size)
        if idx > 0:
            self._font_size = keys[idx - 1]; self._save_settings()

    def _font_larger(self):
        keys = list(FONT_SIZES.keys())
        idx  = keys.index(self._font_size)
        if idx < len(keys) - 1:
            self._font_size = keys[idx + 1]; self._save_settings()

    def _open_search(self):
        self._search_dialog = SearchDialog(self); self._search_dialog.show()

    def _open_prompt_settings(self):
        PromptSettingsDialog(self).exec_()

    def _clear_history(self):
        if ClearDialog(self).exec_() == QDialog.Accepted:
            clear_history()
            while self.messages_layout.count() > 1:
                item = self.messages_layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()
                elif item.layout(): self._clear_layout(item.layout())
            self._add_system_message(t("chat_cleared"))

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _save_settings(self):
        s = storage.load_chat_settings()
        s["font_size"]     = self._font_size
        s["window_width"]  = self.width()
        s["window_height"] = self.height()
        storage.save_chat_settings(s)

    def _on_close(self):
        self._save_settings(); self.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPos() - self._drag_pos)
