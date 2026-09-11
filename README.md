# 📅 Smart Activity Diary with Tags

A lightweight, cross-platform desktop application built with Python and Tkinter designed to track your weekly activities, organize them via interactive multi-tagging system, and analyze your productivity over time.

---

## ✨ Key Features

- **🌐 Multi-language Support:** Instantly switches between **English**, **Deutsch**, **Русский**, and **Українська** directly from the UI without restarting.
- **🏷️ Advanced Multi-Tagging:** Attach multiple contexts (e.g., `#server`, `#database`, `#work`) to a single task using an interactive checkbox panel with live autocomplete filter.
- **📊 Interactive Chronology Chart:** Dynamic timeline visualization powered by Matplotlib. Toggle visibility of specific tag streams using checkbuttons and view day-by-day subtask tooltips on hover.
- **📥 One-Click Excel Export:** Download your entire diary archive or currently filtered search results into a clean, formatted `.xlsx` spreadsheet.
- **🔒 Non-intrusive Layout:** Clean UI with strict column proportions that seamlessly adapters to any window resizing, featuring scrollable daily slots and hidden scrollbars.

---

## 🚀 Installation & Launch

### Option 1: Run from Source (Requires Python)

1. Clone this repository:
   ```bash
   git clone https://github.com
   cd completed-tasks
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python activity_diary.py
   ```

### Option 2: Pre-compiled Portable Binary (No Python required)
Go to the [Releases](https://github.com) page, download the latest zipped version for Windows, extract it, and run the `activity_diary.exe` file.

---

## 📂 Project Structure

- `activity_diary.pyw` — Main Python application source code.
- `locale.json` — Translation files containing dictionaries for all supported languages.
- `diary_data.json` — Local database file storing your tasks in JSON format (created automatically).
- `requirements.txt` — List of external Python package dependencies.
