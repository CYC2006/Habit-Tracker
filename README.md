# Habit Tracker

A minimal macOS habit tracking app built with PyQt6.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![PyQt6](https://img.shields.io/badge/PyQt6-6.5%2B-green)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)

## Features

- **Today** — Check off daily habits and track your progress with a completion bar
- **Month** — Visualize habit streaks with a daily completion chart and per-habit breakdown
- **Settings** — Add, edit, reorder (drag & drop), and assign icons to habits
- Light / Dark / System theme support
- SQLite-backed persistence — data stays local on your machine

## Project Structure

```
Habit_Tracker/
├── main.py               # App entry point
├── requirements.txt
├── assets/
│   └── icon.icns         # App icon
└── habit_tracker/        # Core package
    ├── db.py             # SQLite database layer
    ├── styles.py         # Theme & stylesheet
    ├── icon_utils.py     # Icon keyword mapping
    └── views/
        ├── today_view.py
        ├── month_view.py
        ├── settings_view.py
        └── chart_view.py
```

## Getting Started

### Prerequisites

- Python 3.9+
- macOS (tested on macOS Ventura / Sonoma)

### Installation

```bash
git clone https://github.com/your-username/habit-tracker.git
cd habit-tracker

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### Run

```bash
.venv/bin/python main.py
```

## Build as a macOS App

To package as a standalone `.app` that can be launched by double-clicking:

```bash
.venv/bin/python -m PyInstaller \
  --windowed \
  --name "Habit Tracker" \
  --noconfirm \
  --icon=assets/icon.icns \
  --collect-all qtawesome \
  --collect-all matplotlib \
  --hidden-import=matplotlib.backends.backend_qtagg \
  main.py
```

The output will be in `dist/Habit Tracker.app`. You can drag it to your `/Applications` folder or Dock.

## Tech Stack

| Library | Purpose |
|---|---|
| PyQt6 | UI framework |
| matplotlib | Charts (daily completion, habit bars) |
| qtawesome | Icon fonts (Font Awesome 5) |
| SQLite | Local data storage |
| PyInstaller | macOS app packaging |
