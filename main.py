import sys

import qtawesome as qta
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

from habit_tracker import db, styles
from habit_tracker.views.month_view import MonthView
from habit_tracker.views.settings_view import SettingsView
from habit_tracker.views.today_view import TodayView

_NAV_ITEMS = [
    ("fa5s.calendar-day", "Today"),
    ("fa5s.calendar-alt", "Month"),
    ("fa5s.cog",          "Settings"),
]


class NavButton(QToolButton):
    def __init__(self, icon_name: str, label: str):
        super().__init__()
        self._icon_name = icon_name
        self.setObjectName("nav_btn")
        self.setCheckable(True)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setIconSize(QSize(32, 32))
        self.setText(label)
        self.setFixedSize(QSize(82, 84))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("", 14))
        self.toggled.connect(self._on_toggle)
        self._on_toggle(False)

    def _on_toggle(self, checked: bool):
        color = styles.ACCENT if checked else styles.TEXT_DIM
        self.setIcon(qta.icon(self._icon_name, color=color))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Habit Tracker")
        self.setMinimumSize(1100, 740)
        db.init_db()
        saved_theme = db.get_setting("theme", "dark")
        QApplication.instance().setStyleSheet(styles.apply_theme(saved_theme))
        self._current_idx = 0
        self._build_ui()
        self._switch(0)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        self._today    = TodayView()
        self._month    = MonthView()
        self._settings = SettingsView()
        self._settings.theme_changed.connect(self._on_theme_changed)

        for view in (self._today, self._month, self._settings):
            self.stack.addWidget(view)

        layout.addWidget(self.stack)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(90)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(4, 20, 4, 20)
        layout.setSpacing(6)

        self._logo = QLabel("HT")
        self._logo.setFont(QFont("", 22, QFont.Weight.Black))
        self._logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._logo.setStyleSheet(f"color: {styles.ACCENT}; letter-spacing: 2px;")
        layout.addWidget(self._logo)
        layout.addSpacing(18)

        self._nav_btns: list[NavButton] = []
        for i, (icon_name, label) in enumerate(_NAV_ITEMS):
            btn = NavButton(icon_name, label)
            btn.clicked.connect(lambda _, idx=i: self._switch(idx))
            self._nav_btns.append(btn)
            layout.addWidget(btn)

        layout.addStretch()
        return sidebar

    def _switch(self, index: int):
        self._current_idx = index
        for i, btn in enumerate(self._nav_btns):
            btn.setChecked(i == index)
        self.stack.setCurrentIndex(index)
        views = [self._today, self._month, self._settings]
        views[index].refresh()

    def _on_theme_changed(self):
        theme = db.get_setting("theme", "dark")
        QApplication.instance().setStyleSheet(styles.apply_theme(theme))
        self._logo.setStyleSheet(f"color: {styles.ACCENT}; letter-spacing: 2px;")
        for btn in self._nav_btns:
            btn._on_toggle(btn.isChecked())
        for view in (self._today, self._month, self._settings):
            view.refresh()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(styles.STYLESHEET)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
