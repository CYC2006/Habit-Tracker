from datetime import date

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize, QEvent, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QLineEdit, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from habit_tracker import db, styles
from habit_tracker.icon_utils import CURATED_ICONS, icon_for

N_HABITS = 10


# ── Icon picker dialog ──────────────────────────────────────────────────────────

class IconPickerDialog(QDialog):
    def __init__(self, current: str, parent=None):
        super().__init__(parent)
        self.selected = current
        self.setWindowTitle("Choose Icon")
        self.setFixedWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setSpacing(4)
        grid.setContentsMargins(0, 0, 0, 0)

        COLS = 8
        for i, name in enumerate(CURATED_ICONS):
            is_cur = name == current
            btn = QPushButton()
            btn.setIcon(qta.icon(name, color=styles.ACCENT if is_cur else styles.TEXT_DIM))
            btn.setIconSize(QSize(22, 22))
            btn.setFixedSize(42, 42)
            btn.setToolTip(name.replace("fa5s.", "").replace("-", " "))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if is_cur:
                btn.setStyleSheet(
                    f"background-color: {styles.BG_SUCCESS}; border: 1px solid {styles.ACCENT}; border-radius: 6px;"
                )
            btn.clicked.connect(lambda _, n=name: self._pick(n))
            grid.addWidget(btn, i // COLS, i % COLS)

        scroll.setWidget(grid_w)
        layout.addWidget(scroll)

        rows = (len(CURATED_ICONS) + COLS - 1) // COLS
        self.setFixedHeight(rows * 46 + 28)

    def _pick(self, name: str):
        self.selected = name
        self.accept()


# ── Per-habit row widget ────────────────────────────────────────────────────────

class HabitRowWidget(QWidget):
    def __init__(self, habit_id: int, name: str, icon: str):
        super().__init__()
        self.habit_id = habit_id
        # Empty name → no auto-detected icon (show blank until user sets one)
        if name.strip():
            self._icon_name = icon or icon_for(name)
        else:
            self._icon_name = icon  # keep explicit icon if stored, else ""
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        h = QHBoxLayout(self)
        h.setContentsMargins(8, 0, 8, 0)
        h.setSpacing(10)

        # ── Drag handle (transparent to mouse so list drag works) ──────────────
        grip = QLabel()
        grip.setPixmap(
            qta.icon("fa5s.grip-vertical", color=styles.TEXT_DIM)
            .pixmap(QSize(10, 18))
        )
        grip.setFixedWidth(18)
        grip.setCursor(Qt.CursorShape.SizeVerCursor)
        grip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        h.addWidget(grip, 0, Qt.AlignmentFlag.AlignVCenter)

        # ── Icon button ────────────────────────────────────────────────────────
        self._icon_btn = QPushButton()
        if self._icon_name:
            self._icon_btn.setIcon(qta.icon(self._icon_name, color=styles.ACCENT))
        self._icon_btn.setIconSize(QSize(18, 18))
        self._icon_btn.setFixedSize(32, 32)
        self._icon_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._icon_btn.setToolTip("Click to change icon")
        self._icon_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; border: 1px solid {styles.BORDER}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {styles.BG_CARD}; border: 1px solid {styles.ACCENT}; border-radius: 6px; }}"
        )
        self._icon_btn.clicked.connect(self._pick_icon)
        h.addWidget(self._icon_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        self._edit = QLineEdit(name)
        self._edit.setFont(QFont("", 13))
        self._edit.setReadOnly(True)
        self._edit.setStyleSheet("background: transparent; border: none; padding: 0;")
        self._edit.editingFinished.connect(self._save_name)
        self._edit.installEventFilter(self)
        h.addWidget(self._edit, 1, Qt.AlignmentFlag.AlignVCenter)

    def eventFilter(self, obj, event):
        if obj is self._edit and event.type() == QEvent.Type.MouseButtonDblClick:
            self._edit.setReadOnly(False)
            self._edit.setFocus()
            self._edit.selectAll()
            return True
        return super().eventFilter(obj, event)

    def _pick_icon(self):
        dlg = IconPickerDialog(self._icon_name or "fa5s.check-circle", self.window())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._icon_name = dlg.selected
            db.set_habit_icon(self.habit_id, self._icon_name)
            self._icon_btn.setIcon(qta.icon(self._icon_name, color=styles.ACCENT))

    def _save_name(self):
        self._edit.setReadOnly(True)
        db.rename_habit(self.habit_id, self._edit.text().strip())


# ── Settings view ───────────────────────────────────────────────────────────────

_THEME_ICONS = {"light": "fa5s.sun", "dark": "fa5s.moon", "system": "fa5s.cog"}


class SettingsView(QWidget):
    theme_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        today = date.today()
        self._year = today.year
        self._month = today.month
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(0)

        root.addWidget(self._mk_header())
        root.addSpacing(20)

        # Horizontal split: left (habits) | divider | right (preferences)
        split = QWidget()
        split_h = QHBoxLayout(split)
        split_h.setContentsMargins(0, 0, 0, 0)
        split_h.setSpacing(0)

        split_h.addWidget(self._mk_left_panel(), 44)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setFrameShadow(QFrame.Shadow.Plain)
        div.setFixedWidth(1)
        div.setStyleSheet(f"background: {styles.BORDER};")
        split_h.addWidget(div)

        split_h.addWidget(self._mk_right_panel(), 56)

        root.addWidget(split, 1)

    # ── Left panel (habits) ────────────────────────────────────────────────────

    def _mk_left_panel(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 16, 0)
        v.setSpacing(0)

        # Title row: "Edit Habits" left  +  "Copy Previous Month" right
        title_row = QWidget()
        tr = QHBoxLayout(title_row)
        tr.setContentsMargins(0, 0, 0, 0)
        tr.setSpacing(10)
        title = QLabel("Edit Habits")
        title.setFont(QFont("", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {styles.TEXT_DIM};")
        tr.addWidget(title)
        tr.addStretch()
        copy_btn = QPushButton("Copy Previous Month")
        copy_btn.clicked.connect(self._copy_prev)
        tr.addWidget(copy_btn)
        v.addWidget(title_row)
        v.addSpacing(10)

        self._list = QListWidget()
        self._list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._list.setEditTriggers(QListWidget.EditTrigger.NoEditTriggers)
        self._list.setFont(QFont("", 13))
        self._list.setSpacing(2)
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._list.model().rowsMoved.connect(self._on_reorder)
        v.addWidget(self._list, 1)

        return w

    # ── Right panel (preferences) ──────────────────────────────────────────────

    def _mk_right_panel(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(24, 0, 0, 0)
        v.setSpacing(0)
        v.setAlignment(Qt.AlignmentFlag.AlignTop)

        pref_title = QLabel("Preferences")
        pref_title.setFont(QFont("",20, QFont.Weight.Bold))
        pref_title.setStyleSheet(f"color: {styles.TEXT_DIM};")
        v.addWidget(pref_title)
        v.addSpacing(28)

        # Theme row
        v.addWidget(self._mk_pref_row_theme())
        v.addSpacing(20)

        # Show habit text row
        v.addWidget(self._mk_pref_row_show_text())

        v.addStretch()
        return w

    def _mk_pref_row_theme(self) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        lbl = QLabel("Theme")
        lbl.setFont(QFont("", 16))
        h.addWidget(lbl)
        h.addStretch()

        current = db.get_setting("theme", "dark")
        self._theme_btns: dict = {}
        for key in ("light", "dark", "system"):
            active = current == key
            btn = QPushButton()
            btn.setIcon(qta.icon(_THEME_ICONS[key], color=styles.ACCENT if active else styles.TEXT_DIM))
            btn.setIconSize(QSize(16, 16))
            btn.setFixedSize(34, 34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._theme_btn_style(active))
            btn.clicked.connect(lambda _, k=key: self._set_theme(k))
            self._theme_btns[key] = btn
            h.addWidget(btn)

        return row

    def _mk_pref_row_show_text(self) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)

        main_lbl = QLabel("Today Page - Show Habit Text")
        main_lbl.setFont(QFont("", 16))
        h.addWidget(main_lbl)
        h.addStretch()

        checked = db.get_setting("show_habit_text", "1") == "1"
        self._show_text_btn = QPushButton()
        self._show_text_btn.setIcon(qta.icon("fa5s.check", color=styles.GREEN if checked else styles.TEXT_DIM))
        self._show_text_btn.setIconSize(QSize(16, 16))
        self._show_text_btn.setFixedSize(34, 34)
        self._show_text_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._show_text_btn.setStyleSheet(self._check_btn_style(checked))
        self._show_text_btn.clicked.connect(self._toggle_show_text)
        h.addWidget(self._show_text_btn)

        return row

    @staticmethod
    def _theme_btn_style(active: bool) -> str:
        bg = styles.BG_SUCCESS if active else "transparent"
        border = styles.ACCENT if active else styles.BORDER
        return (
            f"QPushButton {{ background: {bg}; border: 1px solid {border}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {styles.BG_CARD}; }}"
        )

    @staticmethod
    def _check_btn_style(checked: bool) -> str:
        bg = styles.BG_SUCCESS if checked else "transparent"
        border = styles.GREEN if checked else styles.BORDER
        return (
            f"QPushButton {{ background: {bg}; border: 1px solid {border}; border-radius: 6px; }}"
            f"QPushButton:hover {{ background: {styles.BG_CARD}; }}"
        )

    def _set_theme(self, key: str):
        db.set_setting("theme", key)
        for k, btn in self._theme_btns.items():
            active = k == key
            btn.setIcon(qta.icon(_THEME_ICONS[k], color=styles.ACCENT if active else styles.TEXT_DIM))
            btn.setStyleSheet(self._theme_btn_style(active))
        self.theme_changed.emit()

    def _toggle_show_text(self):
        checked = db.get_setting("show_habit_text", "1") == "1"
        new_val = not checked
        db.set_setting("show_habit_text", "1" if new_val else "0")
        self._show_text_btn.setIcon(qta.icon("fa5s.check", color=styles.GREEN if new_val else styles.TEXT_DIM))
        self._show_text_btn.setStyleSheet(self._check_btn_style(new_val))

    # ── Shared header ──────────────────────────────────────────────────────────

    def _mk_header(self) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)

        pb = QPushButton()
        pb.setIcon(qta.icon("fa5s.chevron-left", color=styles.TEXT))
        pb.setIconSize(QSize(16, 16))
        pb.setFixedSize(36, 36)
        pb.clicked.connect(self._prev)
        h.addWidget(pb)

        self._month_lbl = QLabel()
        self._month_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._month_lbl.setFont(QFont("", 24, QFont.Weight.Bold))
        h.addWidget(self._month_lbl, 1)

        nb = QPushButton()
        nb.setIcon(qta.icon("fa5s.chevron-right", color=styles.TEXT))
        nb.setIconSize(QSize(16, 16))
        nb.setFixedSize(36, 36)
        nb.clicked.connect(self._next)
        h.addWidget(nb)

        return w

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _prev(self):
        if self._month == 1:
            self._year -= 1
            self._month = 12
        else:
            self._month -= 1
        self._load()

    def _next(self):
        if self._month == 12:
            self._year += 1
            self._month = 1
        else:
            self._month += 1
        self._load()

    # ── Data ───────────────────────────────────────────────────────────────────

    def _ensure_ten(self) -> list:
        habits = db.get_habits(self._year, self._month)
        for h in habits[N_HABITS:]:
            db.remove_habit(h["id"])
        habits = habits[:N_HABITS]
        needed = N_HABITS - len(habits)
        if needed > 0:
            db.add_habits_batch(self._year, self._month, [""] * needed)
            habits = db.get_habits(self._year, self._month)
        return habits[:N_HABITS]

    def _load(self):
        self._month_lbl.setText(date(self._year, self._month, 1).strftime("%B %Y"))
        self._list.clear()
        for h in self._ensure_ten():
            row_w = HabitRowWidget(h["id"], h["name"], h.get("icon", ""))
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, h["id"])
            item.setSizeHint(QSize(0, 50))
            self._list.addItem(item)
            self._list.setItemWidget(item, row_w)

    def _on_reorder(self):
        ids = [
            self._list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._list.count())
        ]
        db.reorder_habits(ids)

    def _copy_prev(self):
        py, pm = (self._year - 1, 12) if self._month == 1 else (self._year, self._month - 1)
        src = db.get_habits(py, pm)
        if not src:
            QMessageBox.information(self, "Nothing to copy", "No habits found in previous month.")
            return
        if QMessageBox.question(
            self, "Overwrite?",
            "Replace this month's habits with previous month's?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        db.copy_habits_from_month(py, pm, self._year, self._month)
        self._load()

    def _refresh_prefs(self):
        current = db.get_setting("theme", "dark")
        for key, btn in self._theme_btns.items():
            active = current == key
            btn.setIcon(qta.icon(_THEME_ICONS[key], color=styles.ACCENT if active else styles.TEXT_DIM))
            btn.setStyleSheet(self._theme_btn_style(active))
        checked = db.get_setting("show_habit_text", "1") == "1"
        self._show_text_btn.setIcon(qta.icon("fa5s.check", color=styles.GREEN if checked else styles.TEXT_DIM))
        self._show_text_btn.setStyleSheet(self._check_btn_style(checked))

    def refresh(self):
        self._refresh_prefs()
        self._load()
