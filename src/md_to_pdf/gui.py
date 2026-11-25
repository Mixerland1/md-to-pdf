"""Desktop file queue, templates and batch PDF conversion."""
from __future__ import annotations

import queue
import sys
import webbrowser
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from . import __version__
from .batch import collect_sources, plan_outputs
from .cli import convert
from .profiles import load_profile, list_profiles
from .profile_editor import manage_profiles


def main():
    try:
        from tkinterdnd2 import TkinterDnD, DND_FILES
        root = TkinterDnD.Tk()
        drag = True
    except (ImportError, tk.TclError):
        root = tk.Tk()
        drag = False
    root.title("MD to PDF • " + __version__)
    root.geometry("740x510")
    root.minsize(660, 440)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    panel = ttk.Frame(root, padding=24)
    panel.grid(sticky="nsew")
    panel.columnconfigure(0, weight=1)
    panel.rowconfigure(3, weight=1)
    header = ttk.Frame(panel)
    header.grid(sticky="ew")
    ttk.Label(header, text="MD to PDF", font=("TkDefaultFont", 24, "bold")).pack(side="left")
    ttk.Label(panel, text="MD · TXT · DOCX → PDF").grid(sticky="w", pady=(0, 12))
    queuebox = tk.Listbox(panel, selectmode="extended", exportselection=False, height=8, font=("TkDefaultFont", 10))
    queuebox.grid(row=3, column=0, sticky="nsew", pady=8)
    sources = []
    busy = False
    events = queue.Queue()
    template = tk.StringVar(value="Технический")
    status = tk.StringVar(value="Готово")
    controls = []
    available_update = None
    checking = False
    update_button = None
    def add(paths):
        if busy or not paths:
            return
        for path in paths:
            try:
                for source in collect_sources([path], recursive=True):
                    if source not in sources:
                        sources.append(source)
                        queuebox.insert("end", source.name + "  ·  " + str(source.parent))
            except (ValueError, OSError) as exc:
                messagebox.showwarning("MD to PDF", str(exc), parent=root)
        status.set(f"{len(sources)} файлов")
    def remove():
        if busy:
            return
        for index in reversed(queuebox.curselection()):
            sources.pop(index)
            queuebox.delete(index)
    def clear():
        if not busy:
            sources.clear()
            queuebox.delete(0, "end")
            status.set("Готово")
    drop = ttk.Label(panel, text=("Перетащите файлы или папки сюда"
                                if drag else "Добавьте файлы кнопкой ниже"),
                     anchor="center", padding=18, relief="groove")
    drop.grid(row=2, sticky="ew")
    if drag:
        for widget in (drop, queuebox):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", lambda event: add(root.tk.splitlist(event.data)))
    tools = ttk.Frame(panel)
    tools.grid(row=4, sticky="ew", pady=(0, 10))
    def button(parent, text, action):
        w = ttk.Button(parent, text=text, command=action)
        controls.append(w)
        return w
    def choose_files():
        add(filedialog.askopenfilenames(parent=root, filetypes=[("Документы", "*.md *.markdown *.mdown *.txt *.docx")]))
    button(tools, "+ Файлы", choose_files).pack(side="left")
    button(tools, "+ Папка", lambda: add([p] if (p := filedialog.askdirectory(parent=root)) else [])).pack(side="left", padx=4)
    button(tools, "Удалить", remove).pack(side="left", padx=4)
    queuebox.bind("<Delete>", lambda e: remove())
    drop.bind("<Button-1>", lambda e: choose_files() if not busy else None)
    settings = ttk.Frame(panel)
    settings.grid(row=5, sticky="ew", pady=(4,0))
    settings.columnconfigure(1, weight=1)
    builtins = {"Технический":"technical","Деловой":"business","Учебный":"academic","Granulex":"granulex"}
    profiles = list_profiles()
    ttk.Label(settings, text="Стиль документа").grid(row=0,column=0,sticky="w",padx=(0,12))
    combo = ttk.Combobox(settings,textvariable=template,values=(*builtins,*profiles),state="readonly")
    combo.grid(row=0,column=1,sticky="ew"); controls.append(combo)
    def refreshed(path=None):
        nonlocal profiles
        profiles = list_profiles()
        combo.configure(values=(*builtins,*profiles))
        if path:
            for label, item in profiles.items():
                if item == path:
                    template.set(label)
                    break
        if template.get() not in (*builtins,*profiles):
            template.set("Технический")
    button(settings,"Настроить стили…",lambda:manage_profiles(root,selected=template.get(),builtins=builtins,on_change=refreshed)).grid(row=0,column=2,padx=(8,0))
    def selected_options():
        label = template.get()
        profile = load_profile(profiles[label]) if label in profiles else None
        return dict(template=profile.base if profile else builtins[label],profile=profile)
    def open_document_editor():
        if busy:
            return
        chosen = queuebox.curselection()
        if not chosen and len(sources)==1:
            chosen = (0,)
        if len(chosen)!=1:
            messagebox.showinfo("Редактор","Выберите один документ в списке.",parent=root)
            return
        try:
            from .document_editor import open_editor
            open_editor(root,sources[chosen[0]],**selected_options())
        except Exception as exc:
            messagebox.showerror("Редактор",str(exc),parent=root)
    queuebox.bind("<Double-Button-1>",lambda e:open_document_editor())
    ttk.Label(settings,text="PDF сохраняется рядом с исходным файлом. Существующий PDF заменяется.",
              wraplength=650).grid(row=1,column=0,columnspan=3,sticky="w",pady=(8,0))
    progress = ttk.Progressbar(panel, mode="determinate")
    progress.grid(row=6, sticky="ew", pady=(12, 4))
    ttk.Label(panel, textvariable=status, wraplength=700).grid(row=7, sticky="w")
    def set_busy(value):
        nonlocal busy
        busy = value
        for widget in controls:
            widget.configure(state="disabled" if value else "readonly" if widget is combo else "normal")
    def start():
        if busy:
            return
        try:
            if not sources:
                raise ValueError("Добавьте хотя бы один документ")
            jobs = plan_outputs(sources, overwrite=True)
            options = selected_options()
        except (ValueError, OSError) as exc:
            messagebox.showerror("MD to PDF", str(exc), parent=root)
            return
        progress.configure(maximum=len(jobs), value=0)
        set_busy(True)
        status.set("Конвертация…")
        def worker():
            errors = []
            for i, (source, target) in enumerate(jobs, 1):
                try:
                    convert(source, target, **options)
                except Exception as exc:
                    errors.append(f"{source.name}: {exc}")
                events.put(("progress", i, len(jobs)))
            events.put(("done", errors, len(jobs)))
        threading.Thread(target=worker, daemon=True).start()
    def check_update(manual=False):
        nonlocal checking
        if checking or busy:
            return
        checking = True
        def worker():
            try:
                from .updater import check
                events.put(("update-check", check(), manual))
            except Exception as exc:
                events.put(("update-error", str(exc), manual))
        threading.Thread(target=worker,daemon=True).start()

    def update_action():
        if busy:
            return
        if available_update is None:
            check_update(True)
            return
        from .updater import WINDOWS
        if available_update.asset != WINDOWS:
            # macOS replacement is not yet enabled; direct release download.
            webbrowser.open(available_update.url)
            return
        if not messagebox.askyesno("Обновление", "Скачать новую версию и перезапустить программу?\nИсходные документы и сохранённые стили не изменятся.",parent=root):
            return
        set_busy(True)
        status.set("Загрузка и проверка обновления…")
        def worker():
            try:
                from .updater import prepare_windows
                prepare_windows(available_update)
                events.put(("update-exit",None,0))
            except Exception as exc:
                events.put(("update-failed",str(exc),0))
        threading.Thread(target=worker,daemon=True).start()

    if getattr(sys,"frozen",False):
        from .updater import platform_asset
        if platform_asset():
            update_button = button(header,"Проверить обновления",update_action)
            update_button.pack(side="right")
            root.after(400,check_update)

    def poll():
        nonlocal checking, available_update
        try:
            while True:
                kind, value, total = events.get_nowait()
                if kind == "update-check":
                    checking = False
                    available_update = value
                    if value and update_button:
                        update_button.configure(text=("Обновить " if sys.platform=="win32" else "Скачать ")+"v"+value.version)
                    elif total:
                        messagebox.showinfo("Обновление","Установлена актуальная версия.",parent=root)
                elif kind == "update-error":
                    checking = False
                    if total:
                        messagebox.showwarning("Обновление","Не удалось проверить обновления: "+value,parent=root)
                elif kind == "update-failed":
                    set_busy(False)
                    status.set("Обновление не выполнено")
                    messagebox.showerror("Обновление",value,parent=root)
                elif kind == "update-exit":
                    root.destroy()
                    return
                elif kind == "progress":
                    progress.configure(value=value)
                    status.set(f"{value}/{total} обработано")
                else:
                    set_busy(False)
                    status.set(f"{total-len(value)}/{total} успешно")
                    if value:
                        messagebox.showerror("Ошибки конвертации", "\n".join(value), parent=root)
        except queue.Empty:
            pass
        root.after(100, poll)
    actions = ttk.Frame(panel)
    actions.grid(row=8,sticky="ew",pady=(10,0))
    button(actions,"Редактировать документ",open_document_editor).pack(side="left")
    button(actions,"Создать PDF",start).pack(side="right")
    button(actions,"Очистить список",clear).pack(side="left",padx=8)
    def close():
        if not busy or messagebox.askyesno("MD to PDF", "Конвертация выполняется. Выйти?", parent=root):
            root.destroy()
    root.protocol("WM_DELETE_WINDOW", close)
    root.after(100, poll)
    root.mainloop()


if __name__ == "__main__":
    main()
