import datetime
import json
import os
import re
from icalendar import Calendar, Event

CONFIG_FILE = "diary_config.json"
LOCALE_FILE = "locale.json"

def resource_path(relative_path):
    """Возвращает абсолютный путь к ресурсу, учитывая сборку PyInstaller"""
    import sys
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"lang": "en", "db_path": "diary_tasks.ics"}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def load_locale():
    path = resource_path(LOCALE_FILE)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def load_data():
    """Считывает задачи из универсального файла iCalendar (.ics) с очисткой от слэшей"""
    config = load_config()
    db_path = config.get("db_path", "diary_tasks.ics")
    tasks_data = {}

    if not os.path.exists(db_path):
        return tasks_data

    try:
        with open(db_path, "rb") as f:
            cal = Calendar.from_ical(f.read())
            for component in cal.walk():
                if component.name == "VEVENT":
                    dt_start = component.get("dtstart").dt
                    if isinstance(dt_start, datetime.datetime):
                        dt_start = dt_start.date()
                    date_str = dt_start.strftime("%Y-%m-%d")

                    summary = str(component.get("summary", ""))
                    categories = component.get("categories")
                    tags_str = ""

                    if categories:
                        if not isinstance(categories, list):
                            categories = [categories]
                        cat_list = []
                        for c in categories:
                            if hasattr(c, "to_ical"):
                                raw_tag = c.to_ical().decode("utf-8")
                            else:
                                raw_tag = str(c)
                            
                            # ИСПРАВЛЕНО: Очищаем тег от системных экранирующих слэшей iCalendar
                            clean_tag = raw_tag.replace("\\\\", "").replace("\\", "").strip()
                            if clean_tag:
                                cat_list.append(clean_tag)
                                
                        tags_str = " " + " ".join(
                            [f"[#{c.lower().strip()}]" for c in cat_list if c.strip()]
                        )

                    full_task_text = f"{summary}{tags_str}".strip()

                    if date_str not in tasks_data:
                        tasks_data[date_str] = []
                    tasks_data[date_str].append(full_task_text)
    except Exception:
        pass

    return tasks_data


def save_data(tasks_data):
    """Сохраняет задачи в формат iCalendar (.ics), очищая текст перед записью"""
    config = load_config()
    db_path = config.get("db_path", "diary_tasks.ics")

    cal = Calendar()
    cal.add("prodid", "-//Smart Activity Diary//MX//EN")
    cal.add("version", "2.0")

    for date_str, tasks_list in tasks_data.items():
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        for task in tasks_list:
            event = Event()
            clean_task = re.sub(r"\[#[^\]]+\]", "", task).strip()
            tags = re.findall(r"\[#([^\]]+)\]", task)

            # Дополнительно очищаем само описание задачи от случайных слэшей
            clean_task = clean_task.replace("\\\\", "").replace("\\", "")

            event.add("summary", clean_task)
            event.add("dtstart", dt)
            event.add("dtend", dt + datetime.timedelta(days=1))

            if tags:
                clean_tags_list = []
                for t in tags:
                    # ИСПРАВЛЕНО: Убираем любые слэши из тегов перед их упаковкой в файл .ics
                    t_clean = t.replace("\\\\", "").replace("\\", "").strip()
                    if t_clean:
                        clean_tags_list.append(t_clean)
                        
                if clean_tags_list:
                    event.add("categories", clean_tags_list)

            cal.add_component(event)

    try:
        with open(db_path, "wb") as f:
            f.write(cal.to_ical())
    except Exception:
        pass