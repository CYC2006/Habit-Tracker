import calendar
import functools
from datetime import date

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import Patch
from matplotlib.transforms import blended_transform_factory
import numpy as np

import qtawesome as qta
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QImage
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from habit_tracker import db, styles
from habit_tracker.icon_utils import icon_for as _icon_for


@functools.lru_cache(maxsize=128)
def _icon_rgba(icon_name: str, color: str, size: int = 20) -> np.ndarray:
    px = qta.icon(icon_name, color=color).pixmap(QSize(size, size))
    img = px.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    ptr = img.bits()
    ptr.setsize(img.height() * img.width() * 4)
    return np.frombuffer(ptr, dtype=np.uint8).reshape((img.height(), img.width(), 4)).copy()


class ChartView(QWidget):
    def __init__(self):
        super().__init__()
        self._year = date.today().year
        self._month = date.today().month
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 16)
        root.setSpacing(14)

        hdr = QWidget()
        h = QHBoxLayout(hdr)
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

        root.addWidget(hdr)

        self.fig = Figure(figsize=(13, 8), tight_layout=False)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet("background-color: transparent;")
        root.addWidget(self.canvas, 1)

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

    def _load(self):
        # Sync matplotlib colours with current theme
        _bg   = styles.BG
        _card = styles.BG_CARD
        _grid = styles.BORDER
        _text = styles.TEXT
        _dim  = styles.TEXT_DIM

        plt.rcParams.update({
            "text.color":        _text,
            "axes.labelcolor":   _text,
            "xtick.color":       _dim,
            "ytick.color":       _dim,
            "axes.edgecolor":    _grid,
            "figure.facecolor":  _bg,
            "axes.facecolor":    _card,
            "axes.grid":         True,
            "grid.color":        _grid,
            "grid.linewidth":    0.6,
            "axes.spines.top":   False,
            "axes.spines.right": False,
            "font.family":       "sans-serif",
        })

        self._lbl.setText(date(self._year, self._month, 1).strftime("%B %Y"))

        habits   = db.get_habits(self._year, self._month)
        n_days   = calendar.monthrange(self._year, self._month)[1]
        today    = date.today()
        records  = db.get_monthly_records(self._year, self._month)
        game_map = db.get_monthly_game_counts(self._year, self._month)
        n_habits = len(habits)

        days = list(range(1, n_days + 1))
        daily_finish: list[int] = []
        daily_games:  list[int] = []
        daily_score:  list[int] = []
        cumulative:   list[int] = []
        cum = 0

        for day in days:
            d  = date(self._year, self._month, day)
            ds = d.isoformat()
            if d <= today:
                f = sum(1 for h in habits if records.get(h["id"], {}).get(ds, False))
                g = game_map.get(ds, 0)
            else:
                f = g = 0
            s = f - g
            cum += s
            daily_finish.append(f)
            daily_games.append(g)
            daily_score.append(s)
            cumulative.append(cum)

        days_so_far = sum(1 for day in days if date(self._year, self._month, day) <= today)
        habit_names = [h["name"] for h in habits]
        habit_rates = []
        for h in habits:
            total = sum(
                1 for day in days
                if records.get(h["id"], {}).get(
                    date(self._year, self._month, day).isoformat(), False
                )
            )
            habit_rates.append(total / days_so_far if days_so_far > 0 else 0.0)

        # ── Draw ──────────────────────────────────────────────────────────────
        self.fig.clear()
        self.fig.patch.set_facecolor(_bg)
        self.fig.subplots_adjust(
            left=0.06, right=0.98, top=0.93, bottom=0.09,
            hspace=0.5, wspace=0.4,
        )

        gs  = self.fig.add_gridspec(2, 2, height_ratios=[1, 1.5])
        ax1 = self.fig.add_subplot(gs[0, :])
        ax2 = self.fig.add_subplot(gs[1, 0])
        ax3 = self.fig.add_subplot(gs[1, 1])

        for ax in (ax1, ax2, ax3):
            ax.set_facecolor(_card)
            ax.tick_params(colors=_dim, labelsize=8)
            for sp in ax.spines.values():
                sp.set_edgecolor(_grid)

        # ── Chart 1: Daily completion ──────────────────────────────────────────
        future_bar = "#21262d" if styles._is_dark else "#e0e0e0"
        empty_bar  = "#2d3748" if styles._is_dark else "#d0d0d0"

        bar_colors = []
        for i, day in enumerate(days):
            d = date(self._year, self._month, day)
            if d > today:
                bar_colors.append(future_bar)
            elif n_habits and daily_finish[i] == n_habits:
                bar_colors.append(styles.GREEN)
            elif daily_finish[i] > 0:
                bar_colors.append(styles.ACCENT)
            else:
                bar_colors.append(empty_bar)

        ax1.bar(days, daily_finish, color=bar_colors, width=0.65, zorder=3)

        if any(g > 0 for g in daily_games):
            ax1.bar(days, [-g for g in daily_games],
                    color=styles.RED, alpha=0.65, width=0.65, zorder=4)

        score_days = [d for d in days if date(self._year, self._month, d) <= today]
        score_vals = daily_score[:len(score_days)]
        if score_days:
            ax1.plot(score_days, score_vals, color=styles.YELLOW, linewidth=1.8, zorder=5)

        if n_habits:
            ref_color = "#ffffff" if styles._is_dark else "#000000"
            ax1.axhline(n_habits, color=ref_color, linestyle="--", linewidth=0.8, alpha=0.25)

        if today.year == self._year and today.month == self._month:
            ax1.axvline(today.day, color=styles.YELLOW, linewidth=1.5, alpha=0.5)

        ax1.set_title("Daily Habit Completion", color=_text, fontsize=11, fontweight="bold", pad=8)
        ax1.set_xlabel("Day", fontsize=9)
        ax1.set_ylabel("Count", fontsize=9)
        ax1.set_xlim(0.5, n_days + 0.5)
        ax1.set_xticks(days[::2] if n_days > 15 else days)

        legend_patches = [
            Patch(facecolor=styles.ACCENT, label="Habits done"),
            Patch(facecolor=styles.RED, alpha=0.65, label="Games"),
            Patch(facecolor=styles.YELLOW, label="Score"),
        ]
        ax1.legend(handles=legend_patches, loc="upper right",
                   facecolor=_card, edgecolor=_grid, labelcolor=_text, fontsize=8)

        # ── Chart 2: Cumulative score ──────────────────────────────────────────
        if today.year == self._year and today.month == self._month:
            show_days = [d for d in days if d <= today.day]
            show_cum  = cumulative[:len(show_days)]
        else:
            show_days = days
            show_cum  = cumulative

        if show_cum:
            ax2.fill_between(show_days, show_cum, 0,
                             where=[s >= 0 for s in show_cum],
                             color=styles.GREEN, alpha=0.25, interpolate=True)
            ax2.fill_between(show_days, show_cum, 0,
                             where=[s < 0 for s in show_cum],
                             color=styles.RED, alpha=0.25, interpolate=True)
            ax2.plot(show_days, show_cum, color=styles.ACCENT, linewidth=2, zorder=5)
            ax2.axhline(0, color=_grid, linewidth=1)

            last = show_cum[-1]
            clr = styles.GREEN if last >= 0 else styles.RED
            ax2.annotate(f"{last:+d}",
                         xy=(show_days[-1], last),
                         xytext=(4, 4), textcoords="offset points",
                         color=clr, fontweight="bold", fontsize=10)

        ax2.set_title("Cumulative Score", color=_text, fontsize=11, fontweight="bold", pad=8)
        ax2.set_xlabel("Day", fontsize=9)
        ax2.set_ylabel("Score", fontsize=9)
        ax2.xaxis.set_major_locator(mticker.MaxNLocator(integer=True, min_n_ticks=1))
        ax2.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

        # ── Chart 3: Habit completion rates ───────────────────────────────────
        if habit_names:
            ypos = list(range(len(habit_names)))
            bars = ax3.barh(ypos, habit_rates, color=styles.ACCENT, height=0.55, zorder=3)
            ax3.set_yticks(ypos)
            ax3.set_yticklabels([""] * len(ypos))
            ax3.tick_params(axis="y", length=0)
            ax3.set_xlim(0, 1.12)
            ax3.axvline(0.8, color=_grid, linestyle="--", linewidth=0.8, alpha=0.6)
            ax3.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0%}"))

            for bar, rate in zip(bars, habit_rates):
                ax3.text(
                    min(rate + 0.03, 1.0), bar.get_y() + bar.get_height() / 2,
                    f"{rate:.0%}", va="center", fontsize=8, color=_text,
                )

            trans = blended_transform_factory(ax3.transAxes, ax3.transData)
            for i, h in enumerate(habits):
                arr = _icon_rgba(_icon_for(h["name"], h.get("icon", "")), _dim, size=16)
                dpr = self.canvas.devicePixelRatio() or 1.0
                im = OffsetImage(arr, zoom=0.6 / dpr)
                ab = AnnotationBbox(
                    im, xy=(-0.04, i),
                    xycoords=trans,
                    box_alignment=(0.5, 0.5),
                    frameon=False,
                    pad=0,
                )
                ab.set_clip_on(False)
                ax3.add_artist(ab)

            ax3.invert_yaxis()
            ax3.set_title("Habit Completion Rate", color=_text, fontsize=11, fontweight="bold", pad=8)
            ax3.set_xlabel("Rate", fontsize=9)
        else:
            ax3.text(0.5, 0.5, "No habits yet", ha="center", va="center",
                     color=_dim, fontsize=11, transform=ax3.transAxes)

        self.canvas.draw()

    def refresh(self):
        self._load()
