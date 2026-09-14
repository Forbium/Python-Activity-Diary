import datetime
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

# ИМПОРТИРУЕМ ВСЮ НАШУ ВЫНЕСЕННУЮ ЛОГИКУ БЭКЭНДА
import tasks_backend as core

class TasksApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("1200x780")
        try:
            self.root.iconbitmap(core.resource_path("tasks.ico"))
        except Exception:
            pass

        self.search_descending = True
        self.chart_mode = "tags"
        self.exported_data_cache = []
        self.highlighted_task_key = None

        self.current_date = datetime.date.today()
        self.start_of_week = self.current_date - datetime.timedelta(days=self.current_date.weekday())

        self.root.pack_propagate(False)
        self.root.grid_propagate(False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close_app)

        # Загружаем настройки и файлы через модуль логики core
        self.config = core.load_config()
        self.data = core.load_data()
        self.locales = core.load_locale()

        self.lang = self.config.get("lang", "en")
        self.root.title(self.get_txt("title"))

        # --- ВЕРХНЯЯ ПАНЕЛЬ НАСТРОЕК (Язык + База Данных) ---
        top_settings_panel = tk.Frame(self.root, bg="#eceff1", pady=3)
        top_settings_panel.pack(fill=tk.X)

        tk.Label(top_settings_panel, text="Language:", bg="#eceff1", font=("Arial", 8)).pack(side=tk.LEFT, padx=(10, 2))

        self.lang_combo = ttk.Combobox(top_settings_panel, values=["ru", "en", "de", "ua"], width=5, state="readonly")
        self.lang_combo.set(self.lang)
        self.lang_combo.pack(side=tk.LEFT, padx=2)
        self.lang_combo.bind("<<ComboboxSelected>>", self.change_language)

        self.btn_calendar = tk.Button(
            top_settings_panel,
            text=self.get_txt("calender"),
            font=("Arial", 8, "bold"),
            bg="#cfd8dc",
            command=self.change_database_path,
        )
        self.btn_calendar.pack(side=tk.LEFT, padx=20)

        self.db_path_label = tk.Label(
            top_settings_panel,
            text=os.path.basename(self.config.get("db_path", "diary_tasks.ics")),
            bg="#eceff1", fg="gray", font=("Arial", 8, "italic"),
        )
        self.db_path_label.pack(side=tk.LEFT)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.pack_propagate(False)

        self.tab_main = tk.Frame(self.notebook)
        self.tab_chart = tk.Frame(self.notebook)
        self.tab_search = tk.Frame(self.notebook)

        self.notebook.add(self.tab_main, text=self.get_txt("tab_main"))
        self.notebook.add(self.tab_chart, text=self.get_txt("tab_chart"))
        self.notebook.add(self.tab_search, text=self.get_txt("tab_search"))

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.create_widgets()
        self.display_week()

    def get_txt(self, key):
        return self.locales.get(self.lang, {}).get(key, key)
    def change_database_path(self):
        initial_file = os.path.basename(self.config.get("db_path", "diary_tasks.ics"))
        initial_dir = os.path.dirname(self.config.get("db_path", "."))

        file_path = filedialog.asksaveasfilename(
            title="Выберите или создайте файл календаря iCalendar",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=".ics",
            filetypes=[("iCalendar files", "*.ics"), ("All files", "*.*")],
        )

        if file_path:
            self.config["db_path"] = file_path
            core.save_config(self.config)
            self.db_path_label.config(text=os.path.basename(file_path))
            self.data = core.load_data()
            self.display_week()
            self.do_search()
            messagebox.showinfo(
                self.get_txt("msg_success"), f"Календарь переключен на:\n{file_path}"
            )

    def change_language(self, event):
        self.lang = self.lang_combo.get()
        self.root.title(self.get_txt("title"))
        self.config["lang"] = self.lang
        core.save_config(self.config)

        new_text = self.get_txt("calender")
        self.btn_calendar.config(text=new_text)

        self.notebook.tab(0, text=self.get_txt("tab_main"))
        self.notebook.tab(1, text=self.get_txt("tab_chart"))
        self.notebook.tab(2, text=self.get_txt("tab_search"))

        self.create_widgets()
        self.display_week()
        self.do_search()

    def create_widgets(self):
        if hasattr(self, "nav_frame_container"):
            self.nav_frame_container.destroy()
        if hasattr(self, "weeks_frame"):
            self.weeks_frame.destroy()
        if hasattr(self, "search_top_frame"):
            self.search_top_frame.destroy()
        if hasattr(self, "search_scroll_frame"):
            self.search_scroll_frame.destroy()

        # --- ВКЛАДКА 1: ДНЕВНИК ---
        self.nav_frame_container = tk.Frame(self.tab_main, bg="#f5f5f5", pady=5)
        self.nav_frame_container.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(
            self.nav_frame_container,
            text=self.get_txt("btn_today"),
            command=self.go_to_today,
            bg="#e0f7fa",
        ).pack(side=tk.LEFT, padx=5)
        tk.Button(
            self.nav_frame_container,
            text=self.get_txt("btn_go_date"),
            command=self.go_to_specific_date,
        ).pack(side=tk.LEFT, padx=5)

        week_nav_container = tk.Frame(self.nav_frame_container, bg="#f5f5f5")
        week_nav_container.pack(side=tk.LEFT, expand=True)

        tk.Button(
            week_nav_container, text=self.get_txt("btn_prev_week"), command=self.prev_week
        ).pack(side=tk.LEFT, padx=2)
        self.week_label = tk.Label(
            week_nav_container, text="", font=("Arial", 12, "bold"), bg="#f5f5f5"
        )
        self.week_label.pack(side=tk.LEFT, padx=15)
        tk.Button(
            week_nav_container, text=self.get_txt("btn_next_week"), command=self.next_week
        ).pack(side=tk.LEFT, padx=2)

        self.weeks_frame = tk.Frame(self.tab_main)
        self.weeks_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.weeks_frame.grid_propagate(False)
        self.weeks_frame.pack_propagate(False)
        self.weeks_frame.rowconfigure(0, weight=1)

        for i in range(7):
            self.weeks_frame.columnconfigure(i, weight=1, uniform="group1")

        # --- ВКЛАДКА 3: ПОИСК ---
        self.search_top_frame = tk.Frame(self.tab_search, bg="#f5f5f5", pady=10)
        self.search_top_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(
            self.search_top_frame,
            text=self.get_txt("search_label"),
            font=("Arial", 10, "bold"),
            bg="#f5f5f5",
        ).pack(side=tk.LEFT, padx=5)
        
        self.search_entry = tk.Entry(self.search_top_frame, width=35, font=("Arial", 10))
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self.do_search())

        sort_text = (
            self.get_txt("btn_sort_new")
            if self.search_descending
            else self.get_txt("btn_sort_old")
        )
        self.btn_sort = tk.Button(
            self.search_top_frame,
            text=sort_text,
            command=self.toggle_search_sort,
            bg="#fff3e0",
            font=("Arial", 9, "bold"),
            padx=10,
        )
        self.btn_sort.pack(side=tk.LEFT, padx=10)

        tk.Button(
            self.search_top_frame,
            text=self.get_txt("btn_export"),
            command=self.export_to_excel,
            bg="#e8f5e9",
            font=("Arial", 9, "bold"),
            padx=10,
        ).pack(side=tk.RIGHT, padx=5)
        
        self.search_scroll_frame = tk.Frame(self.tab_search)
        self.search_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.search_text_container = tk.Text(
            self.search_scroll_frame, wrap=tk.NONE, bd=1, relief=tk.SUNKEN, bg="#fafafa"
        )
        search_scrollbar = tk.Scrollbar(
            self.search_scroll_frame,
            orient="vertical",
            command=self.search_text_container.yview,
        )
        self.search_text_container.configure(yscrollcommand=search_scrollbar.set)
        search_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.search_text_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def display_week(self):
        for widget in self.weeks_frame.winfo_children():
            widget.destroy()
        if hasattr(self, "task_widgets_cache"):
            self.task_widgets_cache.clear()

        end_of_week = self.start_of_week + datetime.timedelta(days=6)
        self.week_label.config(
            text=f"{self.start_of_week.strftime('%d.%m.%Y')} — {end_of_week.strftime('%d.%m.%Y')}"
        )

        days = self.locales.get(self.lang, {}).get(
            "days", ["Pn", "Vt", "Sr", "Ct", "Pt", "Sb", "Vs"]
        )

        for i in range(7):
            day_date = self.start_of_week + datetime.timedelta(days=i)
            date_str = day_date.strftime("%Y-%m-%d")

            is_today = day_date == datetime.date.today()
            bg_color = "#fffde7" if is_today else "#f9f9f9"
            hdr_color = "#fff59d" if is_today else "#eceff1"

            day_col = tk.Frame(self.weeks_frame, bd=1, relief=tk.SOLID, bg=bg_color)
            day_col.grid(row=0, column=i, sticky="nsew", padx=3)
            day_col.grid_propagate(False)

            tk.Label(
                day_col,
                text=f"{days[i]}\n{day_date.strftime('%d.%m')}",
                font=("Arial", 10, "bold"),
                bg=hdr_color,
            ).pack(fill=tk.X, pady=2)
            tk.Button(
                day_col,
                text=self.get_txt("btn_add_task"),
                command=lambda d=date_str: self.open_add_dialog(d),
                bg="#e8f5e9",
                font=("Arial", 9, "bold"),
            ).pack(fill=tk.X, padx=4, pady=4)

            tasks_container = tk.Frame(day_col, bg=bg_color)
            tasks_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

            def adjust_text_wrap(event, container=tasks_container):
                for child in container.winfo_children():
                    if isinstance(child, tk.Frame):
                        for sub_child in child.winfo_children():
                            if (
                                isinstance(sub_child, tk.Label)
                                and sub_child != child.winfo_children()
                            ):
                                sub_child.configure(wraplength=event.width - 42)

            tasks_container.bind("<Configure>", adjust_text_wrap)

            if date_str in self.data:
                for task in self.data[date_str]:
                    self.create_task_element(tasks_container, date_str, task)

    def create_task_element(self, parent, date_str, task_text):
        # Генерируем уникальный ключ для этой конкретной плашки на неделе
        task_key = f"{date_str}_{task_text}"
        
        # Если эта задача выбрана, красим её в оранжевый цвет, иначе в стандартный голубой
        is_active = (self.highlighted_task_key == task_key)
        bg_color = "#eeca94" if is_active else "#e0f2f1"
        
        task_frame = tk.Frame(parent, bg=bg_color, bd=1, relief=tk.RAISED, pady=4)
        task_frame.pack(fill=tk.X, padx=1, pady=2)

        btn_del = tk.Button(
            task_frame, text="❌", bd=0, bg=bg_color, fg="red", 
            font=("Arial", 8, "bold"), width=3, padx=0, pady=0,
            command=lambda: self.delete_task(date_str, task_text)
        )
        btn_del.pack(side=tk.RIGHT, padx=2)

        lbl = tk.Label(task_frame, text=task_text, bg=bg_color, anchor="w", 
                       justify=tk.LEFT, font=("Arial", 9), wraplength=100, padx=0, pady=0)
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        # Инициализируем кэш виджетов в конструкторе, если его там нет
        if not hasattr(self, "task_widgets_cache"):
            self.task_widgets_cache = {}
            
        # Сохраняем ссылки на элементы, чтобы красить их без перерисовки всего окна
        self.task_widgets_cache[task_key] = (task_frame, lbl, btn_del)

        # ИСПРАВЛЕНО: Функция точечной смены цвета БЕЗ вызова мигающего display_week()
        def on_single_click(event):
            # Сбрасываем цвет у старой выделенной плашки (если она была в кэше)
            if self.highlighted_task_key in self.task_widgets_cache:
                old_frame, old_lbl, old_btn = self.task_widgets_cache[self.highlighted_task_key]
                try:
                    old_frame.configure(bg="#e0f2f1")
                    old_lbl.configure(bg="#e0f2f1")
                    old_btn.configure(bg="#e0f2f1")
                except tk.TclError: pass # Защита, если задача была удалена

            # Мгновенно красим текущую плашку в оранжевый цвет
            self.highlighted_task_key = task_key
            task_frame.configure(bg="#eeca94")
            lbl.configure(bg="#eeca94")
            btn_del.configure(bg="#eeca94")

        # Навешиваем одиночный клик для плавной подсветки
        lbl.bind("<Button-1>", on_single_click)
        task_frame.bind("<Button-1>", on_single_click)
        
        # ИСПРАВЛЕНО: Навешиваем двойной клик. Теперь он работает идеально, 
        # так как виджеты больше не пересоздаются при первом клике!
        lbl.bind("<Double-Button-1>", lambda event: self.open_edit_dialog(date_str, task_text))
        task_frame.bind("<Double-Button-1>", lambda event: self.open_edit_dialog(date_str, task_text))

    def delete_task(self, date_str, task_text):
        if date_str in self.data and task_text in self.data[date_str]:
            self.data[date_str].remove(task_text)
            if not self.data[date_str]:
                del self.data[date_str]
            core.save_data(self.data)
            self.display_week()

    def prev_week(self):
        self.start_of_week -= datetime.timedelta(days=7)
        self.display_week()

    def next_week(self):
        self.start_of_week += datetime.timedelta(days=7)
        self.display_week()

    def go_to_today(self):
        self.start_of_week = datetime.date.today() - datetime.timedelta(
            days=datetime.date.today().weekday()
        )
        self.display_week()

    def go_to_specific_date(self):
        date_str = simpledialog.askstring(
            self.get_txt("btn_go_date"), f"{self.get_txt('btn_go_date')} (DD.MM.YYYY):"
        )
        if date_str:
            try:
                target_date = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
                self.start_of_week = target_date - datetime.timedelta(
                    days=target_date.weekday()
                )
                self.display_week()
            except ValueError:
                messagebox.showerror(
                    self.get_txt("msg_error"), self.get_txt("err_date_format")
                )

    def get_all_unique_history(self):
        tasks = set()
        for day_tasks in self.data.values():
            for t in day_tasks:
                clean_text = re.sub(r"\[#[^\]]+\]", "", t).strip()
                if clean_text:
                    tasks.add(clean_text)
        return list(tasks)

    def get_all_unique_tags(self):
        tags = set()
        for day_tasks in self.data.values():
            for t in day_tasks:
                found_tags = re.findall(r"\[#([^\]]+)\]", t)
                for tag in found_tags:
                    tags.add(tag.lower().strip())
        return sorted(list(tags))

    def open_add_dialog(self, date_str):
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{self.get_txt('dialog_add_title')} {date_str}")
        dialog.geometry("440x380")
        dialog.transient(self.root)
        dialog.grab_set()

        self.root.update_idletasks()
        pos_x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (440 // 2)
        pos_y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (380 // 2)
        dialog.geometry(f"+{pos_x}+{pos_y}")

        inputs_frame = tk.Frame(dialog)
        inputs_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        all_tasks = self.get_all_unique_history()
        unique_tags_list = self.get_all_unique_tags()

        tk.Label(inputs_frame, text=self.get_txt("lbl_description"), font=("Arial", 9, "bold")).pack(anchor="w", pady=2)
        task_combo = ttk.Combobox(inputs_frame, values=all_tasks, width=45)
        task_combo.pack(fill=tk.X, pady=4)
        task_combo.focus()

        tk.Label(inputs_frame, text=self.get_txt("lbl_tags_add"), font=("Arial", 9, "bold")).pack(anchor="w", pady=2)
        tags_entry = tk.Entry(inputs_frame, width=48, font=("Arial", 10))
        tags_entry.pack(fill=tk.X, pady=4)

        tk.Label(inputs_frame, text=self.get_txt("lbl_tags_available"), font=("Arial", 9, "bold")).pack(anchor="w", pady=4)
        checkboxes_frame = tk.Frame(inputs_frame)
        checkboxes_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        tags_text_panel = tk.Text(checkboxes_frame, wrap=tk.NONE, bd=1, relief=tk.SUNKEN, bg="#fafafa", height=5)
        tags_scrollbar = tk.Scrollbar(checkboxes_frame, orient="vertical", command=tags_text_panel.yview)
        tags_text_panel.configure(yscrollcommand=tags_scrollbar.set)
        tags_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tags_text_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        checkbox_vars = {}

        def sync_checkboxes_from_text():
            current_input_tags = [t.lower().strip() for t in tags_entry.get().replace(",", " ").split() if t.strip()]
            for tag, var in checkbox_vars.items():
                var.set(tag in current_input_tags)

        def refresh_checkboxes():
            tags_text_panel.configure(state=tk.NORMAL)
            tags_text_panel.delete("1.0", tk.END)
            sync_checkboxes_from_text()

            raw_text = tags_entry.get().replace(",", " ")
            words = raw_text.split()
            last_word = words[-1].lower().strip() if words else ""
            if tags_entry.get() and tags_entry.get()[-1] in [" ", ","]:
                last_word = ""

            visible_tags = [t for t in unique_tags_list if not last_word or last_word in t]
            if not visible_tags:
                tags_text_panel.insert(tk.END, self.get_txt("no_tags_yet"))
                tags_text_panel.configure(state=tk.DISABLED)
                return

            for tag in visible_tags:
                if tag not in checkbox_vars:
                    checkbox_vars[tag] = tk.BooleanVar(value=False)

                def on_cb_click(t=tag, v=checkbox_vars[tag]):
                    current_text = tags_entry.get().replace(",", " ").split()
                    if current_text and not tags_entry.get()[-1] in [" ", ","]:
                        current_text.pop()
                    if v.get():
                        if t not in current_text: current_text.append(t)
                    else:
                        if t in current_text: current_text.remove(t)
                    tags_entry.delete(0, tk.END)
                    tags_entry.insert(0, ", ".join(current_text) + (", " if current_text else ""))
                    tags_entry.icursor(tk.END)

                cb = tk.Checkbutton(tags_text_panel, text=f"#{tag}", variable=checkbox_vars[tag],
                                    bg="#fafafa", activebackground="#fafafa", font=("Arial", 9), command=on_cb_click)
                tags_text_panel.window_create(tk.END, window=cb)
                tags_text_panel.insert(tk.END, "\n")
            tags_text_panel.configure(state=tk.DISABLED)

        tags_entry.bind("<KeyRelease>", lambda e: refresh_checkboxes())

        def on_task_select(event):
            selected = task_combo.get().strip()
            tags_entry.delete(0, tk.END)
            for day_tasks in self.data.values():
                for t in day_tasks:
                    if re.sub(r"\[#[^\]]+\]", "", t).strip() == selected:
                        current_task_tags = re.findall(r"\[#([^\]]+)\]", t)
                        tags_entry.insert(0, ", ".join(current_task_tags) + ", ")
                        refresh_checkboxes()
                        return

        task_combo.bind("<<ComboboxSelected>>", on_task_select)

        for tag in unique_tags_list:
            checkbox_vars[tag] = tk.BooleanVar(value=False)
        refresh_checkboxes()

        btn_frame = tk.Frame(dialog, bg="#f5f5f5", height=50)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        def save_entry():
            tsk = task_combo.get().strip()
            all_tags = tags_entry.get().replace(",", " ").split()
            clean_tags = list(set([t.lower().strip() for t in all_tags if t.strip()]))
            if tsk:
                formatted_tags = " ".join([f"[#{tag}]" for tag in clean_tags])
                full_text = f"{tsk} {formatted_tags}".strip()
                if date_str not in self.data:
                    self.data[date_str] = []
                if full_text not in self.data[date_str]:
                    self.data[date_str].append(full_text)
                core.save_data(self.data)
                self.display_week()
                dialog.destroy()
            else:
                messagebox.showwarning(self.get_txt("msg_warning"), self.get_txt("warn_empty_task"))

        tk.Button(btn_frame, text=self.get_txt("btn_save_task"), command=save_entry, bg="#a5d6a7", font=("Arial", 9, "bold"), padx=15, pady=3).pack(pady=10)

    def open_edit_dialog(self, date_str, old_task_text):
        dialog = tk.Toplevel(self.root)
        dialog.title(self.get_txt("dialog_edit_title"))
        dialog.geometry("440x380")
        dialog.transient(self.root)
        dialog.grab_set()

        self.root.update_idletasks()
        pos_x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (440 // 2)
        pos_y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (380 // 2)
        dialog.geometry(f"+{pos_x}+{pos_y}")

        inputs_frame = tk.Frame(dialog)
        inputs_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        clean_task = re.sub(r"\[#[^\]]+\]", "", old_task_text).strip()
        current_task_tags = [t.lower().strip() for t in re.findall(r"\[#([^\]]+)\]", old_task_text)]

        all_tasks = self.get_all_unique_history()
        unique_tags_list = self.get_all_unique_tags()

        tk.Label(inputs_frame, text=self.get_txt("lbl_description"), font=("Arial", 9, "bold")).pack(anchor="w", pady=2)
        task_combo = ttk.Combobox(inputs_frame, values=all_tasks, width=45)
        task_combo.pack(fill=tk.X, pady=4)
        task_combo.set(clean_task)
        task_combo.focus()

        tk.Label(inputs_frame, text=self.get_txt("lbl_tags_edit"), font=("Arial", 9, "bold")).pack(anchor="w", pady=2)
        tags_entry = tk.Entry(inputs_frame, width=48, font=("Arial", 10))
        tags_entry.pack(fill=tk.X, pady=4)
        tags_entry.insert(0, ", ".join(current_task_tags) + (", " if current_task_tags else ""))

        tk.Label(inputs_frame, text=self.get_txt("lbl_tags_available"), font=("Arial", 9, "bold")).pack(anchor="w", pady=4)
        checkboxes_frame = tk.Frame(inputs_frame)
        checkboxes_frame.pack(fill=tk.BOTH, expand=True, pady=4)

        tags_text_panel = tk.Text(checkboxes_frame, wrap=tk.NONE, bd=1, relief=tk.SUNKEN, bg="#fafafa", height=5)
        tags_scrollbar = tk.Scrollbar(checkboxes_frame, orient="vertical", command=tags_text_panel.yview)
        tags_text_panel.configure(yscrollcommand=tags_scrollbar.set)
        tags_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tags_text_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        checkbox_vars = {}
        for tag in unique_tags_list:
            checkbox_vars[tag] = tk.BooleanVar(value=tag in current_task_tags)

        def sync_checkboxes_from_text():
            current_input_tags = [t.lower().strip() for t in tags_entry.get().replace(",", " ").split() if t.strip()]
            for tag, var in checkbox_vars.items():
                var.set(tag in current_input_tags)

        def refresh_checkboxes():
            tags_text_panel.configure(state=tk.NORMAL)
            tags_text_panel.delete("1.0", tk.END)
            sync_checkboxes_from_text()

            raw_text = tags_entry.get().replace(",", " ")
            words = raw_text.split()
            last_word = words[-1].lower().strip() if words else ""
            if tags_entry.get() and tags_entry.get()[-1] in [" ", ","]:
                last_word = ""

            visible_tags = [t for t in unique_tags_list if not last_word or last_word in t]
            if not visible_tags:
                tags_text_panel.insert(tk.END, self.get_txt("no_tags_yet"))
                tags_text_panel.configure(state=tk.DISABLED)
                return
            for tag in visible_tags:
                def on_cb_click(t=tag, v=checkbox_vars[tag]):
                    current_text = tags_entry.get().replace(",", " ").split()
                    if current_text and not tags_entry.get()[-1] in [" ", ","]:
                        current_text.pop()
                    if v.get():
                        if t not in current_text: 
                            current_text.append(t)
                    else:
                        if t in current_text: 
                            current_text.remove(t)
                    tags_entry.delete(0, tk.END)
                    tags_entry.insert(0, ", ".join(current_text) + (", " if current_text else ""))
                    tags_entry.icursor(tk.END)
                
                cb = tk.Checkbutton(
                    tags_text_panel,
                    text=f"#{tag}",
                    variable=checkbox_vars[tag],
                    bg="#fafafa",
                    activebackground="#fafafa",
                    font=("Arial", 9),
                    command=on_cb_click,
                )
                tags_text_panel.window_create(tk.END, window=cb)
                tags_text_panel.insert(tk.END, "\n")
            tags_text_panel.configure(state=tk.DISABLED)

        tags_entry.bind("<KeyRelease>", lambda e: refresh_checkboxes())
        refresh_checkboxes()

        btn_frame = tk.Frame(dialog, bg="#f5f5f5", height=50)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        def save_changes():
            new_tsk = task_combo.get().strip()
            manual_tags = tags_entry.get().replace(",", " ").split()
            selected_tags = [tag for tag, var in checkbox_vars.items() if var.get()]
            all_tags = list(set([t.lower().strip() for t in (manual_tags + selected_tags) if t.strip()]))
            
            if new_tsk:
                formatted_tags = " ".join([f"[#{tag}]" for tag in all_tags])
                new_full_text = f"{new_tsk} {formatted_tags}".strip()
                if date_str in self.data and old_task_text in self.data[date_str]:
                    idx = self.data[date_str].index(old_task_text)
                    self.data[date_str][idx] = new_full_text
                    core.save_data(self.data)
                self.display_week()
                dialog.destroy()
            else:
                messagebox.showwarning(self.get_txt("msg_warning"), self.get_txt("warn_empty_task"))

        tk.Button(
            btn_frame,
            text=self.get_txt("btn_save_changes"),
            command=save_changes,
            bg="#a5d6a7",
            font=("Arial", 9, "bold"),
            padx=15,
            pady=3,
        ).pack(pady=10)

    def toggle_search_sort(self):
        self.search_descending = not self.search_descending
        sort_text = (
            self.get_txt("btn_sort_new")
            if self.search_descending
            else self.get_txt("btn_sort_old")
        )
        self.btn_sort.config(text=sort_text)
        self.do_search()

    def do_search(self):
        self.search_text_container.configure(state=tk.NORMAL)
        self.search_text_container.delete("1.0", tk.END)
        query = self.search_entry.get().lower().strip() if hasattr(self, "search_entry") else ""

        self.data = core.load_data()
        sorted_dates = sorted(self.data.keys(), reverse=self.search_descending)
        self.exported_data_cache = []

        def jump_to_date(d_str, full_text):
            target_date = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
            self.start_of_week = target_date - datetime.timedelta(days=target_date.weekday())
            self.highlighted_task_key = f"{d_str}_{full_text}"
            self.display_week()
            self.notebook.select(0)

        found = False
        for date_str in sorted_dates:
            for task in self.data[date_str]:
                if not query or query in task.lower():
                    found = True
                    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                    self.exported_data_cache.append({"date": date_str, "task_text": task})
                    
                    btn = tk.Button(
                        self.search_text_container, 
                        text=f" 📅 {dt.strftime('%d.%m.%Y')}  👉  {task} ", 
                        anchor="w", justify=tk.LEFT, bg="#f0f4c3", relief=tk.GROOVE, padx=5, pady=1, 
                        font=("Arial", 9), 
                        command=lambda d=date_str, t=task: jump_to_date(d, t)
                    )
                    self.search_text_container.window_create(tk.END, window=btn)
                    self.search_text_container.insert(tk.END, "\n")

    def export_to_excel(self):
        items_to_export = list(self.exported_data_cache)
        if not items_to_export:
            for d_str in sorted(self.data.keys()):
                for t in self.data[d_str]:
                    items_to_export.append({"date": d_str, "task_text": t})
        if not items_to_export:
            messagebox.showwarning(
                self.get_txt("msg_warning"), self.get_txt("warn_empty_task")
            )
            return

        days = self.locales.get(self.lang, {}).get("days", ["Pn", "Vt", "Sr", "Ct", "Pt", "Sb", "Vs"])
        rows = []
        for item in items_to_export:
            dt = datetime.datetime.strptime(item["date"], "%Y-%m-%d")
            clean_task = re.sub(r"\[#[^\]]+\]", "", item["task_text"]).strip()
            tags = ", ".join(re.findall(r"\[#([^\]]+)\]", item["task_text"]))
            rows.append(
                {
                    self.get_txt("excel_date"): dt.strftime("%d.%m.%Y"),
                    self.get_txt("excel_weekday"): days[dt.weekday()],
                    self.get_txt("excel_task"): clean_task,
                    self.get_txt("excel_tags"): tags if tags else "-",
                }
            )

        try:
            df = pd.DataFrame(rows)
            filename = f"diary_export_{datetime.date.today().strftime('%Y%m%d')}.xlsx"
            df.to_excel(filename, index=False)
            messagebox.showinfo(
                self.get_txt("msg_success"),
                f"{self.get_txt('success_export')}\n{os.path.abspath(filename)}",
            )
        except Exception as e:
            messagebox.showerror(self.get_txt("msg_error"), f"Excel Error:\n{str(e)}")
    def on_tab_changed(self, event):
        idx = self.notebook.index(self.notebook.select())
        if idx == 1:
            self.show_activity_chart()
        elif idx == 2:
            self.do_search()

    def toggle_chart_mode(self):
        self.chart_mode = "tasks" if self.chart_mode == "tags" else "tags"
        self.show_activity_chart()

    def show_activity_chart(self):
        for w in self.tab_chart.winfo_children():
            w.destroy()
        mode_frame = tk.Frame(self.tab_chart, bg="#f5f5f5", pady=8, padx=15)
        mode_frame.pack(fill=tk.X)

        view_date = self.start_of_week + datetime.timedelta(days=3)
        year, month = view_date.year, view_date.month
        num_days = 31 if month == 12 else (datetime.date(year, month + 1, 1) - datetime.date(year, month, 1)).days
        months = self.locales.get(self.lang, {}).get(
            "months",
            ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        )

        tk.Label(
            mode_frame,
            text=f"📊 {self.get_txt('chart_title')} {months[month-1]} {year}",
            font=("Arial", 11, "bold"),
            bg="#f5f5f5",
        ).pack(side=tk.LEFT)
        
        tk.Button(
            mode_frame,
            text=(self.get_txt("mode_tags") if self.chart_mode == "tags" else self.get_txt("mode_tasks")),
            command=self.toggle_chart_mode,
            bg="#e1f5fe",
            font=("Arial", 9, "bold"),
        ).pack(side=tk.RIGHT)

        main_content = tk.Frame(self.tab_chart)
        main_content.pack(fill=tk.BOTH, expand=True, pady=5)

        left_panel = tk.Frame(main_content, width=260, bd=1, relief=tk.SUNKEN)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_panel.pack_propagate(False)

        tk.Label(left_panel, text=self.get_txt("filter_streams"), font=("Arial", 9, "bold")).pack(anchor="w", padx=5, pady=5)
        list_scroll_frame = tk.Frame(left_panel)
        list_scroll_frame.pack(fill=tk.BOTH, expand=True)

        self.list_text_container = tk.Text(list_scroll_frame, wrap=tk.NONE, bd=0, bg="#fafafa", highlightthickness=0)
        list_scrollbar = tk.Scrollbar(list_scroll_frame, orient="vertical", command=self.list_text_container.yview)
        self.list_text_container.configure(yscrollcommand=list_scrollbar.set)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.list_text_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        month_items = set()
        for day in range(1, num_days + 1):
            date_str = datetime.date(year, month, day).strftime("%Y-%m-%d")
            if date_str in self.data:
                for t in self.data[date_str]:
                    if self.chart_mode == "tags":
                        for tag in re.findall(r"\[#([^\]]+)\]", t):
                            month_items.add(tag.lower().strip())
                    else:
                        clean_task = re.sub(r"\[#[^\]]+\]", "", t).strip()
                        if clean_task:
                            month_items.add(clean_task)

        items_list = sorted(list(month_items))
        if not items_list:
            self.list_text_container.configure(state=tk.NORMAL)
            self.list_text_container.insert(tk.END, f" {self.get_txt('no_data')} {months[month-1]}.")
            self.list_text_container.configure(state=tk.DISABLED)
            tk.Label(main_content, text=f"{self.get_txt('no_data')} {months[month-1]} {year}.", font=("Arial", 12)).pack(pady=50)
            return

        cmap = plt.get_cmap("tab10", len(items_list))
        colors_map = {item: cmap(i) for i, item in enumerate(items_list)}

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.set_xlim(0.5, num_days + 0.5)
        ax.set_xticks(range(1, num_days + 1))
        ax.set_xlabel(f"{self.get_txt('tooltip_day')}s", fontsize=10, labelpad=10)
        ax.set_ylim(-0.2, len(items_list) * 0.18)
        ax.set_yticks([])

        for day in range(1, num_days + 1):
            if datetime.date(year, month, day).weekday() in [5,6]:
                ax.axvspan(day - 0.5, day + 0.5, facecolor="#96d2ee", alpha=0.15, zorder=0)

        self.chart_bars = {item: [] for item in items_list}
        all_drawn_bars = []

        for day in range(1, num_days + 1):
            date_str = datetime.date(year, month, day).strftime("%Y-%m-%d")
            if date_str in self.data:
                if self.chart_mode == "tags":
                    for t_name in items_list:
                        matching = [
                            re.sub(r"\[#[^\]]+\]", "", t).strip()
                            for t in self.data[date_str]
                            if f"[#{t_name}]" in t.lower()
                        ]
                        if matching:
                            idx = items_list.index(t_name)
                            tooltip = f"{day} {self.get_txt('tooltip_day')} | {self.get_txt('tooltip_tag')} [#{t_name}]:\n• " + "\n• ".join(matching)
                            bar, = ax.plot(
                                [day - 0.45, day + 0.45], [idx * 0.15, idx * 0.15],
                                color=colors_map[t_name], linewidth=7, solid_capstyle="round", gid=tooltip
                            )
                            self.chart_bars[t_name].append(bar)
                            all_drawn_bars.append(bar)
                else:
                    for t_name in items_list:
                        tags_found = []
                        has_task = False
                        for t in self.data[date_str]:
                            if re.sub(r"\[#[^\]]+\]", "", t).strip() == t_name:
                                has_task = True
                                raw = re.findall(r"\[#([^\]]+)\]", t)
                                if raw:
                                    tags_found.extend(raw)
                        if has_task:
                            idx = items_list.index(t_name)
                            lbl_tags = " (" + ", ".join(tags_found) + ")" if tags_found else f" ({self.get_txt('tooltip_no_labels')})"
                            tooltip = f"{day} {self.get_txt('tooltip_day')} | {self.get_txt('tooltip_task')}: {t_name}\n{self.get_txt('tooltip_labels')}:{lbl_tags}"
                            (bar,) = ax.plot(
                                [day - 0.45, day + 0.45], [idx * 0.15, idx * 0.15],
                                color=colors_map[t_name], linewidth=7, solid_capstyle="round", gid=tooltip
                            )
                            self.chart_bars[t_name].append(bar)
                            all_drawn_bars.append(bar)

        plt.subplots_adjust(top=0.92, bottom=0.15, left=0.05, right=0.95)

        def toggle_line_visibility(name, cb_var):
            for line_obj in self.chart_bars[name]:
                line_obj.set_visible(cb_var.get())
            fig.canvas.draw()

        self.list_text_container.configure(state=tk.NORMAL)
        for item_name in items_list:
            item_frame = tk.Frame(self.list_text_container, bg="#fafafa")
            rgb = [int(x * 255) for x in colors_map[item_name][:3]]
            tk.Frame(item_frame, width=12, height=12, bg=f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}").pack(side=tk.LEFT, padx=4)
            cb_var = tk.BooleanVar(value=True)
            tk.Checkbutton(
                item_frame, text=f"#{item_name}" if self.chart_mode == "tags" else item_name,
                variable=cb_var, font=("Arial", 9), bg="#fafafa", activebackground="#fafafa",
                command=lambda n=item_name, v=cb_var: toggle_line_visibility(n, v)
            ).pack(side=tk.LEFT, anchor="w")
            self.list_text_container.window_create(tk.END, window=item_frame)
            self.list_text_container.insert(tk.END, "\n")
        self.list_text_container.configure(state=tk.DISABLED)

        annot = ax.annotate(
            "", xy=(0, 0), xytext=(10, 10), textcoords="offset points", color="white",
            bbox=dict(boxstyle="round,pad=0.5", fc="black", ec="black", alpha=0.8)
        )
        annot.set_visible(False)

        def hover(event):
            if event.inaxes == ax:
                for line in all_drawn_bars:
                    if line.get_visible():
                        cont, ind = line.contains(event)
                        if cont:
                            annot.xy = (event.xdata, event.ydata)
                            annot.set_text(line.get_gid())
                            annot.set_visible(True)
                            fig.canvas.draw_idle()
                            return
            if annot.get_visible():
                annot.set_visible(False)
                fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", hover)
        ax.grid(True, axis="x", linestyle=":", alpha=0.6)
        for spine in ["top", "left", "right"]:
            ax.spines[spine].set_visible(False)

        canvas = FigureCanvasTkAgg(fig, master=main_content)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    def on_close_app(self):
        plt.close("all")
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TasksApp(root)
    root.mainloop()