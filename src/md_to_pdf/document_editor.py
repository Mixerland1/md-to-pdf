"""Native selection-based document style editor (text view, actual PDF export)."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont
import webbrowser
from .cli import render_html, write_rendered_pdf
from .editor_model import DocumentEditor

PARAGRAPH = {
    "Обычный текст": "normal", "Заголовок 1": "h1", "Заголовок 2": "h2",
    "Заголовок 3": "h3", "Цитата": "quote", "Примечание": "note",
    "Предупреждение": "warning", "Блок кода": "code-block",
}
INLINE = {"Полужирный": "bold", "Курсив": "italic", "Код": "code", "Акцент": "accent"}


def open_editor(parent, source: Path, **options):
    model = DocumentEditor(render_html(source, **options))
    win = tk.Toplevel(parent)
    win.title("Редактор стилей · " + source.name)
    win.geometry("940x720")
    win.minsize(680, 480)
    win.columnconfigure(0, weight=1)
    win.rowconfigure(2, weight=1)
    win.transient(parent)
    bar = ttk.Frame(win, padding=(12, 10))
    bar.grid(sticky="ew")
    ttk.Label(bar, text="Выделите текст и выберите стиль", font=("TkDefaultFont", 12, "bold")).pack(side="left")
    status = tk.StringVar(value="Исходный файл не изменяется")
    toolbar = ttk.Frame(win, padding=(12, 0, 12, 8))
    toolbar.grid(sticky="ew")
    area = ttk.Frame(win, padding=(12, 0))
    area.grid(sticky="nsew")
    area.columnconfigure(0, weight=1)
    area.rowconfigure(0, weight=1)
    text = tk.Text(area, wrap="word", background="white", foreground="#1F2937",
                   padx=30, pady=24, relief="flat", exportselection=False,
                   selectbackground="#b7d5ff", selectforeground="#111827")
    text.grid(sticky="nsew")
    scroll = ttk.Scrollbar(area, orient="vertical", command=text.yview)
    scroll.grid(row=0, column=1, sticky="ns")
    text.configure(yscrollcommand=scroll.set)
    profile = options.get("profile")
    base = profile.base if profile else options.get("template", "technical")
    family = profile.font if profile else ("Montserrat" if base == "granulex" else "TkDefaultFont")
    accent = profile.accent if profile else ("#E2112E" if base == "granulex" else "#23578C")
    body_color = profile.text if profile else "#1F2937"
    heading_color = profile.heading if profile else "#1F2937"
    font_cache = {}
    bounds = []
    saved_selection = []
    selected_style = tk.StringVar(value="Стиль абзаца…")

    def font(size, bold=False, italic=False, mono=False):
        key = (size, bold, italic, mono)
        if key not in font_cache:
            f = tkfont.nametofont("TkDefaultFont").copy()
            f.configure(size=size, weight="bold" if bold else "normal",
                        slant="italic" if italic else "roman")
            if mono:
                f.configure(family=profile.mono if profile else "Courier")
            elif family != "TkDefaultFont":
                f.configure(family=family)
            font_cache[key] = f
        return font_cache[key]

    def refresh():
        nonlocal bounds
        y = text.yview()[0]
        text.configure(state="normal")
        text.delete("1.0", "end")
        bounds = []
        for i, block in enumerate(model.blocks()):
            role = block.role
            heading = role in ("h1","h2","h3","h4","h5","h6")
            size = {"h1":22,"h2":17,"h3":14,"h4":12,"h5":11,"h6":11}.get(role, 11)
            start = text.index("end-1c")
            for value, bold, italic, mono, colored in model.runs(i):
                tag = f"r{i}_{int(bold)}{int(italic)}{int(mono)}{int(colored)}"
                color = accent if colored else heading_color if heading else body_color
                bg = "#fff1f2" if role == "warning" else "#f3f4f6" if role in ("note","blockquote","pre") else "white"
                text.tag_configure(tag, font=font(size,bold or heading,italic,mono),
                                   foreground=color, background=bg,
                                   spacing1=3, spacing3=5)
                text.insert("end-1c", value, tag)
            end = text.index("end-1c")
            bounds.append((start, end))
            text.insert("end-1c", "\n\n")
        text.configure(state="disabled")
        text.yview_moveto(y)

    def ranges_from_selection():
        try:
            first,last = text.index("sel.first"),text.index("sel.last")
        except tk.TclError:
            return []
        ranges = []
        for i,(a,b) in enumerate(bounds):
            left = first if text.compare(first,">",a) else a
            right = last if text.compare(last,"<",b) else b
            if text.compare(left,"<",right):
                ranges.append((i,len(text.get(a,left)),len(text.get(a,right))))
        return ranges

    def capture(_event=None):
        nonlocal saved_selection
        values = ranges_from_selection()
        if values:
            saved_selection = values
        else:
            saved_selection = []

    def restore(ranges):
        text.tag_remove("sel","1.0","end")
        for i,a,b in ranges:
            if i < len(bounds):
                start,_ = bounds[i]
                # Tcl's character indices can differ from Python's for some
                # Unicode characters. Use the actual rendered prefix length.
                block = model.blocks()[i].text
                def offset(n):
                    return len(block[:n].encode("utf-16-le"))//2 if win.tk.call("string","length","😀")==2 else n
                text.tag_add("sel",f"{start}+{offset(a)}c",f"{start}+{offset(b)}c")
        text.tag_raise("sel")

    def apply(style):
        nonlocal saved_selection
        values = ranges_from_selection() or saved_selection
        try:
            model.apply(style, values)
            refresh()
            saved_selection = values
            restore(values)
            status.set("Стиль применён. Можно отменить действие.")
        except ValueError as exc:
            status.set("Выделите текст." if not values else str(exc))

    def paragraph(_event=None):
        style = PARAGRAPH.get(selected_style.get())
        if style:
            apply(style)
        selected_style.set("Стиль абзаца…")

    def history(redo=False):
        nonlocal saved_selection
        changed = model.redo() if redo else model.undo()
        if changed:
            saved_selection = []
            refresh()
            status.set("Действие восстановлено" if redo else "Действие отменено")

    def export():
        path = filedialog.asksaveasfilename(parent=win, defaultextension=".pdf",
                    initialfile=source.stem+"-styled.pdf", filetypes=[("PDF","*.pdf")])
        if not path:
            return
        try:
            write_rendered_pdf(model.html(),source,Path(path),css=options.get("css"))
            status.set("PDF сохранён: "+path)
            webbrowser.open(Path(path).resolve().as_uri())
        except Exception as exc:
            messagebox.showerror("PDF",str(exc),parent=win)

    combo = ttk.Combobox(toolbar,textvariable=selected_style,values=tuple(PARAGRAPH),state="readonly",width=20)
    combo.pack(side="left",padx=(0,8))
    combo.bind("<<ComboboxSelected>>",paragraph)
    for label,style in INLINE.items():
        ttk.Button(toolbar,text=label,command=lambda s=style:apply(s)).pack(side="left",padx=2)
    ttk.Button(toolbar,text="↶",command=history,width=3).pack(side="left",padx=(8,2))
    ttk.Button(toolbar,text="↷",command=lambda:history(True),width=3).pack(side="left",padx=2)
    bottom = ttk.Frame(win,padding=12)
    bottom.grid(sticky="ew")
    ttk.Label(bottom,textvariable=status,wraplength=470).pack(side="left")
    ttk.Button(bottom,text="Экспорт PDF",command=export).pack(side="right")
    ttk.Label(win,text="Текстовый предпросмотр. Изображения и таблицы сохраняются в PDF; точная вёрстка — в экспортированном файле.",
              padding=(12,0,12,8),wraplength=800).grid(sticky="w")
    text.bind("<ButtonRelease-1>",capture)
    text.bind("<KeyRelease>",capture)
    win.bind("<Control-z>",lambda e:history())
    win.bind("<Control-y>",lambda e:history(True))
    refresh()
    win.grab_set()
