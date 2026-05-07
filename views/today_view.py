from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import qtawesome as qta
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

import db
import styles
from icon_utils import icon_for as _icon_for


# ── Habit card ─────────────────────────────────────────────────────────────────

class HabitCard(QFrame):
    toggled = pyqtSignal(int, bool)

    def __init__(self, habit_id: int, name: str, done: bool, icon: str = "", show_text: bool = True):
        super().__init__()
        self.habit_id = habit_id
        self.done = done
        self._icon_key = _icon_for(name, icon)
        self._icon_size = 44 if show_text else 53
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(140)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 16, 8, 12)
        lay.setSpacing(10)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_lbl = QLabel()
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._icon_lbl)

        self._name_lbl = QLabel(name)
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_lbl.setFont(QFont("", 12))
        self._name_lbl.setVisible(show_text)
        lay.addWidget(self._name_lbl)

        self._refresh()

    def _refresh(self):
        color = styles.GREEN if self.done else styles.TEXT_DIM
        px = qta.icon(self._icon_key, color=color).pixmap(QSize(self._icon_size, self._icon_size))
        self._icon_lbl.setPixmap(px)

        if self.done:
            self.setStyleSheet(f"""
                HabitCard {{
                    background-color: {styles.BG_SUCCESS};
                    border: 2px solid {styles.GREEN};
                    border-radius: 12px;
                }}
                HabitCard QLabel {{ border: none; background: transparent; color: {styles.GREEN}; }}
            """)
        else:
            self.setStyleSheet(f"""
                HabitCard {{
                    background-color: {styles.BG_CARD};
                    border: 1px solid {styles.BORDER};
                    border-radius: 12px;
                }}
                HabitCard QLabel {{ border: none; background: transparent; color: {styles.TEXT}; }}
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.done = not self.done
            self._refresh()
            self.toggled.emit(self.habit_id, self.done)
        super().mousePressEvent(event)


# ── Game count card ────────────────────────────────────────────────────────────

class GameCard(QFrame):
    count_changed = pyqtSignal(int)

    def __init__(self, count: int = 0, show_text: bool = True):
        super().__init__()
        self._count = count
        icon_size = 22 if show_text else 32
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(70)
        self.setStyleSheet(f"""
            GameCard {{
                background-color: {styles.BG_CARD};
                border: 1px solid {styles.BORDER};
                border-radius: 12px;
            }}
            GameCard QLabel {{ border: none; background: transparent; }}
            GameCard QPushButton {{
                background-color: {styles.BG_SIDE};
                border: 1px solid {styles.BORDER};
                border-radius: 5px;
                color: {styles.TEXT};
            }}
            GameCard QPushButton:hover {{ background-color: {styles.BORDER}; }}
        """)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 20, 0)
        lay.setSpacing(10)

        icon_lbl = QLabel()
        px = qta.icon("fa5s.gamepad", color=styles.TEXT_DIM).pixmap(QSize(icon_size, icon_size))
        icon_lbl.setPixmap(px)
        lay.addWidget(icon_lbl)

        if show_text:
            title = QLabel("Game Count")
            title.setFont(QFont("", 13))
            title.setStyleSheet(f"color: {styles.TEXT_DIM};")
            lay.addWidget(title)

        lay.addStretch()

        self._minus = QPushButton()
        self._minus.setIcon(qta.icon("fa5s.minus", color=styles.TEXT))
        self._minus.setIconSize(QSize(12, 12))
        self._minus.setFixedSize(32, 32)
        self._minus.clicked.connect(self._decrement)
        lay.addWidget(self._minus)

        self._count_lbl = QLabel(str(count))
        self._count_lbl.setFont(QFont("", 22, QFont.Weight.Bold))
        self._count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._count_lbl.setMinimumWidth(36)
        lay.addWidget(self._count_lbl)

        self._plus = QPushButton()
        self._plus.setIcon(qta.icon("fa5s.plus", color=styles.TEXT))
        self._plus.setIconSize(QSize(12, 12))
        self._plus.setFixedSize(32, 32)
        self._plus.clicked.connect(self._increment)
        lay.addWidget(self._plus)

    def _increment(self):
        self._count = min(99, self._count + 1)
        self._count_lbl.setText(str(self._count))
        self.count_changed.emit(self._count)

    def _decrement(self):
        self._count = max(0, self._count - 1)
        self._count_lbl.setText(str(self._count))
        self.count_changed.emit(self._count)

    @property
    def count(self) -> int:
        return self._count


# ── Today view ─────────────────────────────────────────────────────────────────

COLS = 5


class TodayView(QWidget):
    def __init__(self):
        super().__init__()
        self._date = date.today()
        self._cards: list[HabitCard] = []
        self._game_card: Optional[GameCard] = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(0)

        root.addWidget(self._mk_header())
        root.addSpacing(18)
        root.addWidget(self._mk_score_strip())
        root.addSpacing(18)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._grid_widget = QWidget()
        self._grid = QGridLayout(self._grid_widget)
        self._grid.setSpacing(10)
        for c in range(COLS):
            self._grid.setColumnStretch(c, 1)

        scroll.setWidget(self._grid_widget)
        root.addWidget(scroll, 1)

    def _mk_header(self) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)

        self._prev_btn = QPushButton()
        self._prev_btn.setIcon(qta.icon("fa5s.chevron-left", color=styles.TEXT))
        self._prev_btn.setIconSize(QSize(16, 16))
        self._prev_btn.setFixedSize(36, 36)
        self._prev_btn.clicked.connect(self._go_prev)
        h.addWidget(self._prev_btn)

        self._date_lbl = QLabel()
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._date_lbl.setFont(QFont("", 24, QFont.Weight.Bold))
        h.addWidget(self._date_lbl, 1)

        self._next_btn = QPushButton()
        self._next_btn.setIcon(qta.icon("fa5s.chevron-right", color=styles.TEXT))
        self._next_btn.setIconSize(QSize(16, 16))
        self._next_btn.setFixedSize(36, 36)
        self._next_btn.clicked.connect(self._go_next)
        h.addWidget(self._next_btn)

        return w

    def _mk_score_strip(self) -> QFrame:
        strip = QFrame()
        strip.setObjectName("panel")
        strip.setFixedHeight(80)
        h = QHBoxLayout(strip)
        h.setContentsMargins(0, 0, 0, 0)

        self._score_val = QLabel("0")
        self._score_val.setFont(QFont("", 52, QFont.Weight.Bold))
        self._score_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(self._score_val)

        return strip

    def _load(self):
        today = date.today()
        self._next_btn.setEnabled(self._date < today)

        self._date_lbl.setText(self._date.strftime("%Y - %m - %d  %A"))

        habits   = db.get_habits(self._date.year, self._date.month)
        date_key = self._date.isoformat()

        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards = []
        self._game_card = None

        if not habits:
            placeholder = QLabel(
                "No habits configured for this month.\nGo to Settings to add habits."
            )
            placeholder.setStyleSheet(f"color: {styles.TEXT_DIM}; font-size: 13px;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._grid.addWidget(placeholder, 0, 0, 1, COLS)
        else:
            show_text = db.get_setting("show_habit_text", "1") == "1"
            records = db.get_monthly_records(self._date.year, self._date.month)
            for i, h in enumerate(habits):
                done = records.get(h["id"], {}).get(date_key, False)
                card = HabitCard(h["id"], h["name"], done, h.get("icon", ""), show_text=show_text)
                card.toggled.connect(self._on_toggled)
                self._grid.addWidget(card, i // COLS, i % COLS)
                self._cards.append(card)

            gc = db.get_game_count(date_key)
            self._game_card = GameCard(gc, show_text=show_text)
            self._game_card.count_changed.connect(self._on_game_changed)
            habit_rows = (len(habits) + COLS - 1) // COLS
            self._grid.addWidget(self._game_card, habit_rows, 0, 1, COLS)

        used_rows = ((len(habits) + COLS - 1) // COLS + 1) if habits else 1
        self._grid.setRowStretch(used_rows, 1)

        self._refresh_score()

    def _refresh_score(self):
        finish = sum(1 for c in self._cards if c.done)
        games  = self._game_card.count if self._game_card else 0
        score  = finish - games

        self._score_val.setText(f"{score:+d}" if score != 0 else "0")
        self._score_val.setStyleSheet(
            f"color: {styles.GREEN};" if score >= 0 else f"color: {styles.RED};"
        )

    def _go_prev(self):
        self._date -= timedelta(days=1)
        self._load()

    def _go_next(self):
        if self._date < date.today():
            self._date += timedelta(days=1)
            self._load()

    def _on_toggled(self, habit_id: int, done: bool):
        db.set_record(habit_id, self._date.isoformat(), done)
        self._refresh_score()

    def _on_game_changed(self, value: int):
        db.set_game_count(self._date.isoformat(), value)
        self._refresh_score()

    def refresh(self):
        self._load()
