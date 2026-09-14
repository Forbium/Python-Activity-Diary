# 📅 Smart Activity Diary with Multi-Tagging (iCalendar Edition)

A lightweight, cross-platform desktop application built with Python and Tkinter, designed to track weekly activities, organize them via an interactive multi-tagging system, and analyze productivity over time. 

This version features a modern **Model-View-Controller (MVC)** split-architecture and natively utilizes the international **iCalendar (`.ics`)** standard for data storage.

---

## ✨ Key Features

- **📂 Universal iCalendar Standard:** Natively reads and writes data to `.ics` files. Your tasks, timestamps, and tags (stored in the official `CATEGORIES` field) seamlessly sync with Google Calendar, Outlook, and Apple Calendar.
- **🌐 Dynamic Multi-language UI:** Instantly switches between **English**, **Deutsch**, **Русский**, and **Українська** directly from the settings panel on the fly.
- **⚡ Flicker-Free Performance:** Advanced (targeted) widget rendering updates specific element colors instantly without jarring screen flashes.
- **📊 Interactive Chronology Chart:** Dynamic timeline visualization powered by Matplotlib. Toggle specific tag streams using checkbuttons and view day-by-day subtask tooltips on hover.
- **📥 One-Click Excel Export:** Download your entire diary archive or currently filtered search results into a clean, formatted `.xlsx` spreadsheet.
- **🔒 Non-intrusive Layout:** Clean UI with strict column proportions that seamlessly adapts to window resizing, featuring scrollable daily slots and hidden scrollbars.

---

## 🚀 Installation & Launch

### Option 1: Run from Source (Requires Python)

1. Clone this repository:
   ```bash
   git clone https://github.com
   cd smart-activity-diary
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the desktop application:
   ```bash
   python activity_diary.py
   ```

---

## 📂 Project Architecture

The codebase is strictly separated to support easy migration to mobile platforms (like Flet or Kivy) in the future:

- `completed_tasks.pyw` — **Frontend/GUI Layer**. Handles native Tkinter windows, events, widgets, and Matplotlib canvas.
- `tasks_backend.py` — **Backend/Core Logic Layer**. Pure Python module that manages disk I/O, `.json` configuration files, and parses `.ics` streams.
- `locale.json` — Translation dictionaries for all supported languages.
- `diary_config.json` — Local application settings (automatically created).
- `diary_tasks.ics` — The core universal database file (automatically created).
- `requirements.txt` — External Python package dependencies list.

---
