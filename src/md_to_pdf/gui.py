"""Desktop file queue, templates and batch PDF conversion."""
from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .batch import collect_sources, plan_outputs
from .cli import convert, TEMPLATES


def main():
    try:
        from tkinterdnd2 import TkinterDnD, DND_FILES
        root = TkinterDnD.Tk()
        drag = True
    except (ImportError, tk.TclError):
        root = tk.Tk()
        drag = False
    root.title("MD to PDF • 0.2.0")
    root.geometry("820x570")
    root.minsize(650, 460)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    panel = ttk.Frame(root, padding=24)
    panel.grid(sticky="nsew")
    panel.columnconfigure(0, weight=1)
    panel.rowconfigure(3, weight=1)
    ttk.Label(panel, text="MD to PDF", font=("Segoe UI", 24, "bold")).grid(sticky="w")
    ttk.Label(panel, text="Local Markdown conversion / Локальная конвертация Markdown").grid(sticky="w", pady=(0, 12))
    queuebox = tk.Listbox(panel, selectmode="extended", height=8, font=("Segoe UI", 10))
    queuebox.grid(row=3, column=0, sticky="nsew", pady=8)
    sources = []
    busy = False
    events = queue.Queue()
    recursive = tk.BooleanVar(value=False)
    overwrite = tk.BooleanVar(value=False)
    template = tk.StringVar(value="technical")
    directory = tk.StringVar()
    css = tk.StringVar()
    status = tk.StringVar(value="Ready / Готово")
    controls = []
    def add(paths):
        if busy or not paths:
            return
        for path in paths:
            try:
                for source in collect_sources([path], recursive=recursive.get()):
                    if source not in sources:
                        sources.append(source)
                        queuebox.insert("end", str(source))
            except (ValueError, OSError) as exc:
                messagebox.showwarning("MD to PDF", str(exc), parent=root)
        status.set(f"{len(sources)} files / файлов")
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
            status.set("Ready / Готово")
    drop = ttk.Label(panel, text=("Drop Markdown files or folders here / Перетащите файлы или папки"
                                if drag else "Add files using the buttons / Добавьте файлы кнопками"),
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
    button(tools, "Add files / Файлы", lambda: add(filedialog.askopenfilenames(
        filetypes=[("Markdown", "*.md *.markdown *.mdown"), ("All files", "*.*")]))).pack(side="left")
    button(tools, "Folder / Папка", lambda: add([p] if (p := filedialog.askdirectory()) else [])).pack(side="left", padx=4)
    button(tools, "Remove / Удалить", remove).pack(side="left", padx=4)
    button(tools, "Clear / Очистить", clear).pack(side="left")
    cb = ttk.Checkbutton(tools, text="Subfolders / Подпапки", variable=recursive)
    cb.pack(side="right"); controls.append(cb)
    settings = ttk.Frame(panel)
    settings.grid(row=5, sticky="ew")
    settings.columnconfigure(1, weight=1)
    ttk.Label(settings, text="Template / Шаблон").grid(row=0, column=0, sticky="w", padx=(0, 12))
    combo = ttk.Combobox(settings, textvariable=template, values=TEMPLATES, state="readonly")
    combo.grid(row=0, column=1, sticky="ew", pady=3); controls.append(combo)
    def pathrow(row, label, variable, browse):
        ttk.Label(settings, text=label).grid(row=row, column=0, sticky="w")
        entry = ttk.Entry(settings, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=3); controls.append(entry)
        button(settings, "Browse…", browse).grid(row=row, column=2, padx=(6, 0))
    def choose_dir():
        if p := filedialog.askdirectory():
            directory.set(p)
    def choose_css():
        if p := filedialog.askopenfilename(filetypes=[("CSS", "*.css")]):
            css.set(p)
    pathrow(1, "Output / Куда (optional)", directory, choose_dir)
    pathrow(2, "Custom CSS (optional)", css, choose_css)
    ov = ttk.Checkbutton(settings, text="Overwrite / Перезаписывать PDF", variable=overwrite)
    ov.grid(row=3, column=1, sticky="w"); controls.append(ov)
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
                raise ValueError("Add at least one Markdown file")
            jobs = plan_outputs(sources, output_dir=directory.get().strip() or None, overwrite=overwrite.get())
            custom = Path(css.get().strip()) if css.get().strip() else None
            if custom and not custom.is_file():
                raise ValueError("CSS file not found")
            preset = template.get()
        except (ValueError, OSError) as exc:
            messagebox.showerror("MD to PDF", str(exc), parent=root)
            return
        progress.configure(maximum=len(jobs), value=0)
        set_busy(True)
        status.set("Converting… / Конвертация…")
        def worker():
            errors = []
            for i, (source, target) in enumerate(jobs, 1):
                try:
                    convert(source, target, css=custom, template=preset)
                except Exception as exc:
                    errors.append(f"{source.name}: {exc}")
                events.put(("progress", i, len(jobs)))
            events.put(("done", errors, len(jobs)))
        threading.Thread(target=worker, daemon=True).start()
    def poll():
        try:
            while True:
                kind, value, total = events.get_nowait()
                if kind == "progress":
                    progress.configure(value=value)
                    status.set(f"{value}/{total} processed / обработано")
                else:
                    set_busy(False)
                    status.set(f"{total-len(value)}/{total} converted / успешно")
                    if value:
                        messagebox.showerror("Conversion errors", "\n".join(value), parent=root)
        except queue.Empty:
            pass
        root.after(100, poll)
    button(panel, "Convert to PDF / Конвертировать", start).grid(row=8, sticky="e", pady=(10, 0))
    def close():
        if not busy or messagebox.askyesno("MD to PDF", "Conversion in progress. Exit?", parent=root):
            root.destroy()
    root.protocol("WM_DELETE_WINDOW", close)
    root.after(100, poll)
    root.mainloop()


if __name__ == "__main__":
    main()
