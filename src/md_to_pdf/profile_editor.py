"""Desktop brand-profile editor with portable JSON and real PDF preview."""
from dataclasses import replace
from pathlib import Path
import tempfile
import uuid
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import tkinter.font as tkfont
from .profiles import Profile, granulex_profile, import_logo, load_profile, save_profile, library_dir, list_profiles
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
    win.title("Настройка стиля")
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
    tabs = [ttk.Frame(notebook, padding=14) for _ in range(4)]
    for tab, title in zip(tabs, ("Шрифты", "Цвета", "Страница", "Логотип и бренд")):
        notebook.add(tab, text=title)
        tab.columnconfigure(1, weight=1)
    page_numbers = tk.BooleanVar()
    base = tk.StringVar()
    logo_status = tk.StringVar()
    fonts = sorted(set(tkfont.families(win)) | {"Montserrat","Roboto Mono","Arial","DejaVu Sans","DejaVu Sans Mono","Times New Roman"},key=str.casefold)
    fonts = [f for f in fonts if not f.startswith("@")]
    def row(tab, i, key, color=False):
        ttk.Label(tab, text=LABELS[key]).grid(row=i,column=0,sticky="w",pady=5,padx=(0,12))
        var = vars[key] = tk.StringVar()
        if key in ("font","mono"):
            ttk.Combobox(tab,textvariable=var,values=fonts).grid(row=i,column=1,sticky="ew",pady=5)
        elif key in NUMBERS:
            lo,hi = {"body_pt":(7,24),"line_height":(1,2.5),"logo_mm":(5,35),"margin_bottom":(8,40)}.get(key,(5,40))
            step = .1 if key == "line_height" else .5
            ttk.Spinbox(tab,textvariable=var,from_=lo,to=hi,increment=step).grid(row=i,column=1,sticky="ew",pady=5)
        else:
            ttk.Entry(tab,textvariable=var).grid(row=i,column=1,sticky="ew",pady=5)
        if color:
            def choose():
                value = colorchooser.askcolor(color=var.get(),parent=win)[1]
                if value:
                    var.set(value)
            swatch = tk.Label(tab,width=3,relief="solid",borderwidth=1)
            swatch.grid(row=i,column=2,padx=(6,0))
            def update_color(*_):
                try:
                    swatch.configure(background=var.get())
                except tk.TclError:
                    pass
            var.trace_add("write",update_color)
            swatch.bind("<Button-1>",lambda e:choose())
            ttk.Button(tab,text="Выбрать…",command=choose).grid(row=i,column=3,padx=6)
    for i,key in enumerate(("font","mono","body_pt","line_height")):
        row(tabs[0],i,key)
    for i,key in enumerate(("name","product")):
        row(tabs[3],i,key)
    ttk.Label(tabs[3],text="Базовый макет").grid(row=2,column=0,sticky="w")
    ttk.Combobox(tabs[3],textvariable=base,values=("technical","business","academic","granulex"),state="readonly").grid(row=2,column=1,sticky="ew")
    def upload():
        nonlocal current
        path = filedialog.askopenfilename(parent=win,filetypes=[("Логотип","*.svg *.png *.jpg *.jpeg")])
        if path:
            try:
                kind,data = import_logo(Path(path))
                current = replace(current,logo_kind=kind,logo_data=data)
                logo_status.set("SVG · вектор" if kind=="svg" else "PNG в SVG · растр")
            except Exception as exc:
                messagebox.showerror("Логотип",str(exc),parent=win)
    def remove_logo():
        nonlocal current
        current = replace(current,logo_kind="",logo_data="")
        logo_status.set("Нет логотипа")
    ttk.Label(tabs[3],textvariable=logo_status).grid(row=6,column=0,columnspan=2,sticky="w",pady=12)
    ttk.Button(tabs[3],text="Загрузить логотип…",command=upload).grid(row=7,column=0,sticky="w")
    ttk.Button(tabs[3],text="Убрать логотип",command=remove_logo).grid(row=7,column=1,sticky="w")
    for i,key in enumerate(COLORS):
        row(tabs[1],i,key,True)
    for i,key in enumerate(("margin_top","margin_right","margin_bottom","margin_left","footer")):
        row(tabs[2],i,key)
    row(tabs[3],4,"logo_mm")
    ttk.Checkbutton(tabs[2],text="Номера страниц",variable=page_numbers).grid(row=8,column=0,columnspan=2,sticky="w",pady=8)

    def populate(profile):
        nonlocal current
        current = profile
        for key,var in vars.items():
            var.set(str(getattr(profile,key)))
        base.set(profile.base)
        page_numbers.set(profile.page_numbers)
        logo_status.set(profile.logo_kind.upper() if profile.logo_kind else "Нет логотипа")
    sample_font = tkfont.nametofont("TkDefaultFont").copy()
    sample = tk.Label(tabs[0],text="Заголовок документа\nПример текста · Aa Бб 123",font=sample_font,
                      anchor="w",justify="left",background="white",padx=12,pady=12)
    sample.grid(row=8,column=0,columnspan=2,sticky="ew",pady=(12,0))
    def refresh_sample(*_):
        try:
            sample_font.configure(family=vars["font"].get(),size=max(8,min(24,round(float(vars["body_pt"].get()))+3)))
            sample.configure(foreground=vars["heading"].get())
        except (tk.TclError,ValueError):
            pass
    for key in ("font","body_pt","heading"):
        vars[key].trace_add("write",refresh_sample)
    populate(initial)
    refresh_sample()
    def value():
        values = {key:(float(var.get()) if key in NUMBERS else var.get().strip()) for key,var in vars.items()}
        return replace(current,**values,base=base.get(),page_numbers=page_numbers.get()).validate()
    def guarded(action):
        try:
            action()
        except Exception as exc:
            messagebox.showerror("Настройка стиля",str(exc),parent=win)
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
    parent.wait_window(win)
    if parent.winfo_exists() and isinstance(parent,tk.Toplevel):
        parent.grab_set()


def builtin_profile(key, label):
    if key == "granulex":
        return granulex_profile()
    settings = {
        "technical": dict(heading="#17344A",accent="#2B7186",table="#E8EFF4",table_text="#17344A",link="#145E88",body_pt=10.5,margin_top=18,margin_right=15,margin_bottom=20,margin_left=15),
        "business": dict(heading="#172B47",accent="#BC9659",table="#172B47",link="#254B83",body_pt=11,line_height=1.5,margin_top=22,margin_right=20,margin_bottom=23,margin_left=20),
        "academic": dict(font="Times New Roman",heading="#111111",accent="#666666",table="#EEEEEE",table_text="#111111",link="#222222",body_pt=12,line_height=1.5,margin_top=23,margin_right=24,margin_bottom=23,margin_left=24),
    }
    return Profile(name=label,base=key,**settings[key])


def manage_profiles(parent, *, selected, builtins, on_change):
    win = tk.Toplevel(parent)
    win.title("Стили документов")
    win.transient(parent)
    win.geometry("620x440")
    win.minsize(500,380)
    win.columnconfigure(0,weight=1)
    win.rowconfigure(1,weight=1)
    ttk.Label(win,text="Выберите стиль для настройки",font=("TkDefaultFont",14,"bold"),padding=14).grid(sticky="w")
    box = tk.Listbox(win,exportselection=False,activestyle="none",height=8,font=("TkDefaultFont",11))
    box.grid(sticky="nsew",padx=14)
    profiles = {}
    labels = []
    detail = tk.StringVar()
    ttk.Label(win,textvariable=detail,padding=14,wraplength=560).grid(sticky="ew")
    def refresh(path=None):
        nonlocal profiles,labels
        profiles = list_profiles()
        labels = [*builtins,*profiles]
        box.delete(0,"end")
        for label in labels:
            box.insert("end",label)
        target = next((label for label,p in profiles.items() if p==path),selected)
        i = labels.index(target) if target in labels else 0
        box.selection_set(i); box.see(i)
        update_detail()
        on_change(path)
    def current():
        i = box.curselection()
        if not i:
            return None,None
        label = labels[i[0]]
        path = profiles.get(label)
        return (load_profile(path) if path else builtin_profile(builtins[label],label)),path
    def update_detail(_=None):
        try:
            p,path = current()
            detail.set(("Пользовательский стиль" if path else "Встроенный стиль · изменения сохраняются отдельной копией")+
                       "\n"+p.font+" · "+str(p.body_pt)+" pt" if p else "")
        except Exception as exc:
            detail.set(str(exc))
    def edit():
        try:
            p,path=current()
            if p:
                if path is None:
                    p=replace(p,name=p.name+" — мой стиль")
                edit_profile(win,initial=p,existing=path,on_save=refresh)
        except Exception as exc:
            messagebox.showerror("Стили",str(exc),parent=win)
    def new():
        edit_profile(win,initial=Profile(name="Мой стиль"),on_save=refresh)
    def import_file():
        path=filedialog.askopenfilename(parent=win,filetypes=[("Профиль стиля","*.json")])
        if path:
            try:
                edit_profile(win,initial=load_profile(Path(path)),on_save=refresh)
            except Exception as exc:
                messagebox.showerror("Стили",str(exc),parent=win)
    actions=ttk.Frame(win,padding=14)
    actions.grid(sticky="ew")
    ttk.Button(actions,text="Настроить…",command=edit).pack(side="left")
    ttk.Button(actions,text="Создать стиль…",command=new).pack(side="left",padx=4)
    ttk.Button(actions,text="Импорт…",command=import_file).pack(side="left")
    ttk.Button(actions,text="Готово",command=win.destroy).pack(side="right")
    box.bind("<<ListboxSelect>>",update_detail)
    box.bind("<Double-Button-1>",lambda e:edit())
    refresh()
    win.grab_set()
