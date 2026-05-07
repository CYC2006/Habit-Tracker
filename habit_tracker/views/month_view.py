import calendar
from datetime import date

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Patch

import qtawesome as qta
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QHeaderView, QLabel, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from habit_tracker import db, styles
from habit_tracker.icon_utils import icon_for


class _ScrollableCanvas(FigureCanvas):
    """FigureCanvas that forwards wheel events to the parent scroll area."""
    def wheelEvent(self, event):
        # Pass the event up so the QScrollArea can scroll
        if self.parent() is not None:
            self.parent().wheelEvent(event)
        else:
            super().wheelEvent(event)

_BAR_H  = 15   # Rate bar height
_BAR_R  = 7    # Rate bar border-radius
_HBAR_H = 11   # Per-habit bar height
_HBAR_R = 5    # Per-habit bar border-radius


def _rate_color(rate: float) -> str:
    if rate >= 0.8: return styles.GREEN
    if rate >= 0.5: return styles.ACCENT
    if rate >= 0.3: return styles.YELLOW
    return styles.RED


def _bar_style(color: str, h: int, r: int) -> str:
    return f"""
        QProgressBar {{
            background: {styles.BORDER};
            border-radius: {r}px;
            border: none;
        }}
        QProgressBar::chunk {{
            background: {color};
            border-radius: {r}px;
        }}
    """


class MonthView(QWidget):
    def __init__(self):
        super().__init__()
        self._year  = date.today().year
        self._month = date.today().month
        self._setup_ui()

    # ── UI skeleton ────────────────────────────────────────────────────────────

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(0)

        root.addWidget(self._mk_header())
        root.addSpacing(14)

        # Everything scrolls together
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(0)

        # ① Table (rebuilt on every _load)
        self._tbl_container = QWidget()
        self._tbl_layout = QVBoxLayout(self._tbl_container)
        self._tbl_layout.setContentsMargins(0, 0, 0, 0)
        self._tbl_layout.setSpacing(0)
        cv.addWidget(self._tbl_container)
        cv.addSpacing(28)

        # ② Daily Habit Completion bar chart — wrapped in a panel container
        self._daily_frame = QFrame()
        self._daily_frame.setObjectName("panel")
        _dfl = QVBoxLayout(self._daily_frame)
        _dfl.setContentsMargins(12, 12, 12, 12)
        _dfl.setSpacing(0)
        self._daily_fig    = Figure()
        self._daily_canvas = _ScrollableCanvas(self._daily_fig)
        self._daily_canvas.setStyleSheet("background-color: transparent; border: none;")
        self._daily_canvas.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._daily_canvas.setFixedHeight(230)
        _dfl.addWidget(self._daily_canvas)
        cv.addWidget(self._daily_frame)
        cv.addSpacing(28)

        # ③ Bottom: left panel (Completions + Rate) | right panel (habit bars)
        bottom = QWidget()
        bh = QHBoxLayout(bottom)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.setSpacing(16)

        # ── Left panel: Completions + Rate ─────────────────────────────────────
        left_frame = QFrame()
        left_frame.setObjectName("panel")
        lv = QVBoxLayout(left_frame)
        lv.setContentsMargins(20, 18, 20, 18)
        lv.setSpacing(16)
        lv.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Completions row
        comp_row = QWidget()
        ch = QHBoxLayout(comp_row)
        ch.setContentsMargins(0, 0, 0, 0)
        ch.setSpacing(16)
        ch.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lbl_comp = QLabel("Completions")
        lbl_comp.setFont(QFont("", 22))
        lbl_comp.setStyleSheet(f"color: {styles.TEXT_DIM};")
        self._sum_count = QLabel("—")
        self._sum_count.setFont(QFont("", 28, QFont.Weight.Bold))
        self._sum_count.setStyleSheet(f"color: {styles.ACCENT};")
        ch.addWidget(lbl_comp)
        ch.addWidget(self._sum_count)
        ch.addStretch()
        lv.addWidget(comp_row)

        # Rate row + bar (bar fills container width)
        rate_block = QWidget()
        rb = QVBoxLayout(rate_block)
        rb.setContentsMargins(0, 0, 0, 0)
        rb.setSpacing(8)
        rate_row = QWidget()
        rh2 = QHBoxLayout(rate_row)
        rh2.setContentsMargins(0, 0, 0, 0)
        rh2.setSpacing(16)
        rh2.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        lbl_rate = QLabel("Rate")
        lbl_rate.setFont(QFont("", 22))
        lbl_rate.setStyleSheet(f"color: {styles.TEXT_DIM};")
        self._sum_pct = QLabel("—")
        self._sum_pct.setFont(QFont("", 28, QFont.Weight.Bold))
        self._sum_pct.setStyleSheet(f"color: {styles.ACCENT};")
        rh2.addWidget(lbl_rate)
        rh2.addWidget(self._sum_pct)
        rh2.addStretch()
        rb.addWidget(rate_row)
        self._sum_bar = QProgressBar()
        self._sum_bar.setRange(0, 100)
        self._sum_bar.setValue(0)
        self._sum_bar.setTextVisible(False)
        self._sum_bar.setFixedHeight(_BAR_H)
        self._sum_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._sum_bar.setStyleSheet(_bar_style(styles.ACCENT, _BAR_H, _BAR_R))
        rb.addWidget(self._sum_bar)
        lv.addWidget(rate_block)

        bh.addWidget(left_frame, 1)

        # ── Right panel: per-habit bars ────────────────────────────────────────
        self._bars_container = QFrame()
        self._bars_container.setObjectName("panel")
        self._bars_layout = QVBoxLayout(self._bars_container)
        self._bars_layout.setContentsMargins(20, 18, 20, 18)
        self._bars_layout.setSpacing(10)
        self._bars_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        bh.addWidget(self._bars_container, 1)

        cv.addWidget(bottom)
        cv.addSpacing(16)
        cv.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

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

        self._lbl = QLabel()
        self._lbl.setFont(QFont("", 24, QFont.Weight.Bold))
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(self._lbl, 1)

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
            self._year -= 1; self._month = 12
        else:
            self._month -= 1
        self._load()

    def _next(self):
        if self._month == 12:
            self._year += 1; self._month = 1
        else:
            self._month += 1
        self._load()

    # ── Data loading ───────────────────────────────────────────────────────────

    def _load(self):
        self._lbl.setText(date(self._year, self._month, 1).strftime("%B %Y"))

        # Clear old table
        while self._tbl_layout.count():
            item = self._tbl_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        habits   = db.get_habits(self._year, self._month)
        days     = calendar.monthrange(self._year, self._month)[1]
        today    = date.today()
        records  = db.get_monthly_records(self._year, self._month)
        game_map = db.get_monthly_game_counts(self._year, self._month)
        n_habits = len(habits)
        days_arr = list(range(1, days + 1))

        # ── Update matplotlib theme colours ────────────────────────────────────
        plt.rcParams.update({
            "text.color":        styles.TEXT,
            "axes.labelcolor":   styles.TEXT,
            "xtick.color":       styles.TEXT_DIM,
            "ytick.color":       styles.TEXT_DIM,
            "axes.edgecolor":    styles.BORDER,
            "figure.facecolor":  styles.BG,
            "axes.facecolor":    styles.BG_CARD,
            "axes.grid":         True,
            "grid.color":        styles.BORDER,
            "grid.linewidth":    0.6,
            "axes.spines.top":   False,
            "axes.spines.right": False,
            "font.family":       "sans-serif",
        })

        # ── Build table ────────────────────────────────────────────────────────
        n_rows = n_habits + 3
        n_cols = 1 + days + 1

        tbl = QTableWidget(n_rows, n_cols)
        tbl.setFont(QFont("", 11))
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        tbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        tbl.setHorizontalHeaderLabels([""] + [str(i) for i in days_arr] + ["∑"])
        tbl.setIconSize(QSize(18, 18))
        tbl.setColumnWidth(0, 36)
        tbl.setColumnWidth(days + 1, 38)

        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(days + 1, QHeaderView.ResizeMode.Fixed)
        for c in range(1, days + 1):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeMode.Stretch)

        tbl.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for r in range(n_rows):
            tbl.setRowHeight(r, 28)

        today_bg  = "#1f2d3d" if styles._is_dark else "#ddf4ff"
        future_fg = "#2d3748" if styles._is_dark else "#c8c8c8"
        daily_finish = [0] * (days + 1)

        for row, habit in enumerate(habits):
            ic = QTableWidgetItem()
            ic.setIcon(qta.icon(icon_for(habit["name"], habit.get("icon", "")), color=styles.TEXT_DIM))
            ic.setToolTip(habit["name"])
            ic.setFlags(ic.flags() & ~Qt.ItemFlag.ItemIsEditable)
            tbl.setItem(row, 0, ic)
            total = 0
            for day in days_arr:
                d      = date(self._year, self._month, day)
                ds     = d.isoformat()
                done   = records.get(habit["id"], {}).get(ds, False)
                future = d > today
                text = "✓" if done else ("" if not future else "·")
                fg   = styles.GREEN if done else (styles.TEXT_DIM if future else styles.BORDER)
                bg   = today_bg if d == today else None
                self._cell(tbl, row, day, text, fg, bg, disabled=future, future_fg=future_fg)
                if done:
                    total += 1
                    daily_finish[day] += 1
            self._cell(tbl, row, days + 1, str(total), styles.ACCENT)

        def _icon_cell(row, col, fa_name, color, tooltip=""):
            ic = QTableWidgetItem()
            ic.setIcon(qta.icon(fa_name, color=color))
            ic.setToolTip(tooltip)
            ic.setFlags(ic.flags() & ~Qt.ItemFlag.ItemIsEditable)
            tbl.setItem(row, col, ic)

        fr = n_habits
        _icon_cell(fr, 0, "fa5s.check-double", styles.GREEN, "Finish")
        total_finish = 0
        for day in days_arr:
            d = date(self._year, self._month, day)
            f = daily_finish[day]; total_finish += f
            bg = today_bg if d == today else None
            self._cell(tbl, fr, day, str(f) if f else "", styles.GREEN, bg)
        self._cell(tbl, fr, days + 1, str(total_finish), styles.GREEN, bold=True)

        gr = n_habits + 1
        _icon_cell(gr, 0, "fa5s.gamepad", styles.YELLOW, "Game Count")
        total_games = 0
        for day in days_arr:
            d  = date(self._year, self._month, day)
            ds = d.isoformat()
            g  = game_map.get(ds, 0); total_games += g
            bg = today_bg if d == today else None
            self._cell(tbl, gr, day, str(g) if g else "", styles.YELLOW, bg)
        self._cell(tbl, gr, days + 1, str(total_games), styles.YELLOW, bold=True)

        sr = n_habits + 2
        _icon_cell(sr, 0, "fa5s.star", styles.TEXT, "Score")
        total_score = 0
        for day in days_arr:
            d  = date(self._year, self._month, day)
            ds = d.isoformat()
            g  = game_map.get(ds, 0)
            s  = daily_finish[day] - g; total_score += s
            color = styles.GREEN if s >= 0 else styles.RED
            bg    = today_bg if d == today else None
            self._cell(tbl, sr, day, str(s) if daily_finish[day] or g else "", color, bg)
        sc = styles.GREEN if total_score >= 0 else styles.RED
        self._cell(tbl, sr, days + 1, f"{total_score:+d}" if total_score != 0 else "0", sc, bold=True)

        if today.year == self._year and today.month == self._month:
            item = tbl.horizontalHeaderItem(today.day)
            if item:
                item.setForeground(QBrush(QColor(styles.ACCENT)))

        tbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        header_h = tbl.horizontalHeader().sizeHint().height()
        rows_h   = sum(tbl.rowHeight(r) for r in range(n_rows))
        tbl.setFixedHeight(header_h + rows_h + 2)
        tbl.cellClicked.connect(lambda r, c: self._on_click(r, c, habits, days))
        self._tbl_layout.addWidget(tbl)

        # ── Compute time info & chart data ─────────────────────────────────────
        if date(self._year, self._month, 1) > today:
            days_so_far = 0
        elif today.year == self._year and today.month == self._month:
            days_so_far = today.day
        else:
            days_so_far = days

        daily_games_list = [game_map.get(date(self._year, self._month, d).isoformat(), 0) for d in days_arr]
        daily_score = []
        for i, day in enumerate(days_arr):
            d = date(self._year, self._month, day)
            if d <= today:
                f = daily_finish[day]
                g = daily_games_list[i]
            else:
                f = g = 0
            daily_score.append(f - g)

        # ── Draw chart ─────────────────────────────────────────────────────────
        self._draw_daily_chart(days_arr, days, daily_finish, daily_games_list, daily_score, n_habits, today)

        # ── Stats + habit bars ─────────────────────────────────────────────────
        self._update_stats(total_finish, n_habits, days_so_far)
        self._update_habit_bars(habits, days, days_so_far, records)

    # ── Chart drawing ──────────────────────────────────────────────────────────

    def _draw_daily_chart(self, days_arr, n_days, daily_finish, daily_games_list, daily_score, n_habits, today):
        _bg   = styles.BG
        _card = styles.BG_CARD
        _grid = styles.BORDER
        _text = styles.TEXT
        _dim  = styles.TEXT_DIM

        self._daily_fig.clear()
        self._daily_fig.patch.set_facecolor(_card)   # matches the panel container
        self._daily_fig.subplots_adjust(left=0.07, right=0.97, top=0.88, bottom=0.19)
        ax = self._daily_fig.add_subplot(111)
        ax.set_facecolor(_card)
        ax.tick_params(colors=_dim, labelsize=8)
        ax.grid(False)
        for sp in ax.spines.values():
            sp.set_visible(True)
            sp.set_edgecolor(_grid)

        future_bar = "#21262d" if styles._is_dark else "#e0e0e0"
        empty_bar  = "#2d3748" if styles._is_dark else "#d0d0d0"
        bar_colors = []
        for i, day in enumerate(days_arr):
            d = date(self._year, self._month, day)
            if d > today:
                bar_colors.append(future_bar)
            elif n_habits and daily_finish[day] == n_habits:
                bar_colors.append(styles.GREEN)
            elif daily_finish[day] > 0:
                bar_colors.append(styles.ACCENT)
            else:
                bar_colors.append(empty_bar)

        ax.bar(days_arr, [daily_finish[d] for d in days_arr], color=bar_colors, width=0.65, zorder=3)

        if any(g > 0 for g in daily_games_list):
            ax.bar(days_arr, [-g for g in daily_games_list],
                   color=styles.RED, alpha=0.65, width=0.65, zorder=4)

        score_days = [d for d in days_arr if date(self._year, self._month, d) <= today]
        score_vals = daily_score[:len(score_days)]
        if score_days:
            ax.plot(score_days, score_vals, color=styles.YELLOW, linewidth=1.8, zorder=5)

        if n_habits:
            ref_color = "#ffffff" if styles._is_dark else "#000000"
            ax.axhline(n_habits, color=ref_color, linestyle="--", linewidth=0.8, alpha=0.25)

        if today.year == self._year and today.month == self._month:
            ax.axvline(today.day, color=styles.YELLOW, linewidth=1.5, alpha=0.5)

        ax.set_title("Daily Habit Completion", color=_text, fontsize=11, fontweight="bold", pad=6)
        ax.set_xlabel("Day", fontsize=9)
        ax.set_ylabel("Count", fontsize=9)
        ax.set_xlim(0.5, n_days + 0.5)
        ax.set_xticks(days_arr[::2] if n_days > 15 else days_arr)
        ax.set_yticks([-10, -5, 0, 5, 10])
        ax.set_ylim(-11, 11)

        legend_patches = [
            Patch(facecolor=styles.ACCENT, label="Habits done"),
            Patch(facecolor=styles.RED, alpha=0.65, label="Games"),
            Patch(facecolor=styles.YELLOW, label="Score"),
        ]
        ax.legend(handles=legend_patches, loc="upper right",
                  facecolor=_card, edgecolor=_grid, labelcolor=_text, fontsize=8)

        self._daily_canvas.draw()

    # ── Stats + habit bars ─────────────────────────────────────────────────────

    def _update_stats(self, total_finish: int, n_habits: int, days_so_far: int):
        max_possible = n_habits * days_so_far
        rate  = total_finish / max_possible if max_possible > 0 else 0.0
        color = _rate_color(rate)
        self._sum_count.setText(str(total_finish))
        self._sum_pct.setText(f"{rate:.0%}")
        self._sum_pct.setStyleSheet(f"color: {color};")
        self._sum_bar.setValue(int(rate * 100))
        self._sum_bar.setStyleSheet(_bar_style(color, _BAR_H, _BAR_R))

    def _update_habit_bars(self, habits: list, days: int, days_so_far: int, records: dict):
        while self._bars_layout.count():
            item = self._bars_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not habits or days_so_far == 0:
            return

        for h in habits:
            total = sum(
                1 for day in range(1, days + 1)
                if records.get(h["id"], {}).get(
                    f"{self._year:04d}-{self._month:02d}-{day:02d}", False
                )
            )
            rate  = total / days_so_far
            color = _rate_color(rate)

            row_w = QWidget()
            rh    = QHBoxLayout(row_w)
            rh.setContentsMargins(0, 0, 0, 0)
            rh.setSpacing(10)
            rh.setAlignment(Qt.AlignmentFlag.AlignVCenter)

            icon_lbl = QLabel()
            px = qta.icon(
                icon_for(h["name"], h.get("icon", "")), color=styles.TEXT_DIM
            ).pixmap(QSize(18, 18))
            icon_lbl.setPixmap(px)
            icon_lbl.setFixedSize(22, 22)
            rh.addWidget(icon_lbl)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(rate * 100))
            bar.setTextVisible(False)
            bar.setFixedHeight(_HBAR_H)
            bar.setStyleSheet(_bar_style(color, _HBAR_H, _HBAR_R))
            rh.addWidget(bar)

            self._bars_layout.addWidget(row_w)

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _cell(tbl, row, col, text, color=None, bg=None,
              bold=False, disabled=False, future_fg="#2d3748"):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if color:
            item.setForeground(QBrush(QColor(color)))
        if bg:
            item.setBackground(QBrush(QColor(bg)))
        if bold:
            f = item.font(); f.setBold(True); item.setFont(f)
        if disabled:
            item.setForeground(QBrush(QColor(future_fg)))
        tbl.setItem(row, col, item)

    def _on_click(self, row, col, habits, days):
        if col == 0 or col == days + 1:
            return
        if row >= len(habits):
            return
        d = date(self._year, self._month, col)
        if d > date.today():
            return
        db.toggle_record(habits[row]["id"], d.isoformat())
        self._load()

    def refresh(self):
        self._load()
