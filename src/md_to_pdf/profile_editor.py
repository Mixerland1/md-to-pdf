"""Desktop brand-profile editor with portable JSON and real PDF preview."""
from dataclasses import replace
from pathlib import Path
import tempfile
import uuid
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from .profiles import Profile, granulex_profile, import_logo, load_profile, save_profile, library_dir
from .cli import convert

COLORS = ("accent", "text", "heading", "table", "table_text", "link", "muted")
NUMBERS = ("body_pt", "line_height", "margin_top", "margin_right", "margin_bottom", "margin_left", "logo_mm")
LABELS = {
    "name":"Название профиля", "product":"Компания / продукт", "font":"Основной шрифт",
    "mono":"Моноширинный шрифт", "footer":"Текст нижнего колонтитула",
    "accent":"Акцент", "text":"Текст", "heading":"Заголовки", "table":"Шапка таблицы",
    "table_text":"Текст шапки таблицы", "link":"Ссылки", "muted":"Вторичный текст",
    "body_pt":"Размер текста, pt", "line_height":"Межстрочный интервал",
    "margin_top":"Верхнее поле, мм", "margin_right":"Правое поле, мм",
    "margin_bottom":"Нижнее поле, мм", "margin_left":"Левое поле, мм", "logo_mm":"Высота логотипа, мм",
}


def edit_profile(parent, *, initial=None, existing=None, on_save):
    win = tk.Toplevel(parent)
    win.title("Brand Style Studio / Конструктор стилей")
    win.transient(parent)
    win.geometry("720x620")
    win.minsize(620, 530)
    win.columnconfigure(0, weight=1)
    win.rowconfigure(0, weight=1)
    initial = initial or Profile()
    current = initial
    vars = {}
    notebook = ttk.Notebook(win)
    notebook.grid(sticky="nsew", padx=14, pady=12)
    tabs = [ttk.Frame(notebook, padding=14) for _ in range(3)]
    for tab, title in zip(tabs, ("Бренд и шрифты", "Цвета", "Страница")):
        notebook.add(tab, text=title)
        tab.columnconfigure(1, weight=1)
    page_numbers = tk.BooleanVar()
    base = tk.StringVar()
    logo_status = tk.StringVar()
    def row(tab, i, key, color=False):
        ttk.Label(tab, text=LABELS[key]).grid(row=i,column=0,sticky="w",pady=5,padx=(0,12))
        var = vars[key] = tk.StringVar()
        ttk.Entry(tab,textvariable=var).grid(row=i,column=1,sticky="ew",pady=5)
        if color:
            def choose():
                value = colorchooser.askcolor(color=var.get(),parent=win)[1]
                if value:
                    var.set(value)
            ttk.Button(tab,text="Цвет…",command=choose).grid(row=i,column=2,padx=6)
    for i,key in enumerate(("name","product","font","mono","footer")):
        row(tabs[0],i,key)
    ttk.Label(tabs[0],text="Базовый макет").grid(row=5,column=0,sticky="w")
    ttk.Combobox(tabs[0],textvariable=base,values=("technical","business","academic","granulex"),state="readonly").grid(row=5,column=1,sticky="ew")
    def upload():
        nonlocal current
        path = filedialog.askopenfilename(parent=win,filetypes=[("Logo","*.svg *.png *.jpg *.jpeg")])
        if path:
            try:
                kind,data = import_logo(Path(path))
                current = replace(current,logo_kind=kind,logo_data=data)
                logo_status.set("SVG (vector)" if kind=="svg" else "PNG inside SVG (raster)")
            except Exception as exc:
                messagebox.showerror("Logo",str(exc),parent=win)
    def remove_logo():
        nonlocal current
        current = replace(current,logo_kind="",logo_data="")
        logo_status.set("Нет логотипа")
    ttk.Label(tabs[0],textvariable=logo_status).grid(row=6,column=0,columnspan=2,sticky="w",pady=12)
    ttk.Button(tabs[0],text="Загрузить логотип…",command=upload).grid(row=7,column=0,sticky="w")
    ttk.Button(tabs[0],text="Убрать логотип",command=remove_logo).grid(row=7,column=1,sticky="w")
    for i,key in enumerate(COLORS):
        row(tabs[1],i,key,True)
    for i,key in enumerate(NUMBERS):
        row(tabs[2],i,key)
    ttk.Checkbutton(tabs[2],text="Номера страниц",variable=page_numbers).grid(row=8,column=0,columnspan=2,sticky="w",pady=8)

    def populate(profile):
        nonlocal current
        current = profile
        for key,var in vars.items():
            var.set(str(getattr(profile,key)))
        base.set(profile.base)
        page_numbers.set(profile.page_numbers)
        logo_status.set(profile.logo_kind.upper() if profile.logo_kind else "Нет логотипа")
    populate(initial)
    def value():
        values = {key:(float(var.get()) if key in NUMBERS else var.get().strip()) for key,var in vars.items()}
        return replace(current,**values,base=base.get(),page_numbers=page_numbers.get()).validate()
    def guarded(action):
        try:
            action()
        except Exception as exc:
            messagebox.showerror("Brand Style Studio",str(exc),parent=win)
    def save():
        p = value()
        target = existing or library_dir() / (uuid.uuid4().hex+".json")
        save_profile(p,target)
        on_save(target)
        win.destroy()
    def export():
        p = value()
        name = filedialog.asksaveasfilename(parent=win,defaultextension=".json",filetypes=[("Brand profile","*.json")])
        if name:
            save_profile(p,Path(name))
    def preview():
        p = value()
        target = filedialog.asksaveasfilename(parent=win,initialfile="brand-preview.pdf",defaultextension=".pdf",filetypes=[("PDF","*.pdf")])
        if not target:
            return
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/"preview.md"
            source.write_text("# Руководство / User guide\n\nПример текста. **Bold** · *Italic* · [Link](https://example.com).\n\n## Таблица\n\n| Параметр | Значение |\n|---|---|\n| A | Example |\n\n> Цитата / Quote\n\n- Первый пункт\n- Второй пункт\n\n\`sample code\`",encoding="utf-8")
            convert(source,Path(target),profile=p,brand_version="1.0",brand_updated="2026")
        webbrowser.open(Path(target).resolve().as_uri())
    actions = ttk.Frame(win,padding=(14,0,14,14))
    actions.grid(sticky="ew")
    for title, action in (("Предпросмотр PDF",preview),("Экспорт JSON",export),("Сохранить в библиотеку",save)):
        ttk.Button(actions,text=title,command=lambda a=action:guarded(a)).pack(side="left",padx=4)
    ttk.Button(actions,text="Отмена",command=win.destroy).pack(side="right")
    win.grab_set()
