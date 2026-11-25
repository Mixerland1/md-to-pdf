"""Minimal single-document editor with real PDF page preview."""
from __future__ import annotations
import queue
import re
import sys
import threading
import tempfile
import webbrowser
from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk,filedialog,messagebox
from . import __version__
from .inputs import EXTENSIONS
from .profiles import load_profile,list_profiles
from .profile_editor import manage_profiles
from .workspace import Workspace,render_snapshot,export_bytes,write_pdf_bytes
from .ui_skin import Backdrop,configure_theme,SURFACE,INK
from .page_preview import PagePreview

BUILTINS={"Технический":"technical","Деловой":"business","Учебный":"academic","Granulex":"granulex"}
STYLES={"Текст":"normal","Заголовок 1":"h1","Заголовок 2":"h2","Заголовок 3":"h3",
        "Маркированный список":"bullet","Нумерованный список":"numbered","Заголовок 4":"h4","Заголовок 5":"h5","Заголовок 6":"h6",
        "Цитата":"quote","Примечание":"note","Предупреждение":"warning","Блок кода":"code-block",
        "Полужирный":"bold","Курсив":"italic","Код":"code","Акцент":"accent"}

def main():
    try:
        from tkinterdnd2 import TkinterDnD,DND_FILES
        root=TkinterDnD.Tk()
        drag=True
    except (ImportError,tk.TclError):
        root=tk.Tk()
        drag=False
    configure_theme(root)
    clipboard_dir=tempfile.TemporaryDirectory(prefix="md-to-pdf-clipboard-")
    root.title("MD to PDF • "+__version__)
    root.geometry("1200x820")
    root.minsize(1020,480)
    root.columnconfigure(0,weight=1)
    root.rowconfigure(1,weight=1)
    events=queue.Queue()
    state={"workspace":None,"result":None,"generation":0,"rendering":False,
           "dirty":False,"pasted":False,"paste_pdf":None,"selection":[],"brush":None,"restore_selection":[],"update":None,"updating":False}
    profiles=list_profiles()
    preset=tk.StringVar(value="Технический")
    role=tk.StringVar(value="Стиль фрагмента")
    font=tk.StringVar(value="Шрифт")
    size=tk.StringVar(value="pt")
    chrome=ttk.Frame(root,style="Toolbar.TFrame")
    banner=Backdrop(chrome,"toolbar.webp",banner=True,height=23)
    banner.pack(fill="x")
    bar=ttk.Frame(chrome,padding=(10,6),style="Toolbar.TFrame")
    bar.pack(fill="x")
    def options():
        key=preset.get()
        p=load_profile(profiles[key]) if key in profiles else None
        if key not in BUILTINS and p is None:
            return state["workspace"].options if state["workspace"] else dict(template="technical",profile=None)
        return dict(template=p.base if p else BUILTINS[key],profile=p)
    def discard_ok():
        return not state["dirty"] or messagebox.askyesno("MD to PDF","Открыть другой документ без сохранения изменений?",parent=root)
    def choose():
        name=filedialog.askopenfilename(parent=root,filetypes=[("Документы","*.md *.markdown *.mdown *.txt *.docx")])
        if name:
            load(name)
    open_button=ttk.Button(bar,text="Открыть",command=choose,style="Toolbar.TButton")
    editor_bar=ttk.Frame(bar,style="Toolbar.TFrame")
    combo=ttk.Combobox(editor_bar,textvariable=preset,values=(*BUILTINS,*profiles),state="readonly",width=17,style="Toolbar.TCombobox")
    combo.pack(side="left",padx=(8,2))
    def refresh_profiles(path=None):
        nonlocal profiles
        profiles=list_profiles()
        combo.configure(values=(*BUILTINS,*profiles))
        if path:
            label=next((k for k,v in profiles.items() if v==path),None)
            if label:
                preset.set(label)
                switch()
    ttk.Button(editor_bar,text="⚙",width=3,style="Toolbar.TButton",command=lambda:manage_profiles(root,selected=preset.get(),builtins=BUILTINS,on_change=refresh_profiles)).pack(side="left",padx=(0,6))
    styles=ttk.Combobox(editor_bar,textvariable=role,values=tuple(STYLES),state="readonly",width=19,style="Toolbar.TCombobox")
    styles.pack(side="left",padx=(0,4))
    fonts=sorted(set(tkfont.families(root))|{"Montserrat","Roboto Mono","Arial","Times New Roman","DejaVu Sans"},key=str.casefold)
    font_box=ttk.Combobox(editor_bar,textvariable=font,values=tuple(f for f in fonts if not f.startswith("@")),width=17,style="Toolbar.TCombobox")
    font_box.pack(side="left",padx=(0,3))
    size_box=ttk.Combobox(editor_bar,textvariable=size,values=("6","7","8","9","10","11","12","14","16","18","20","24","28","32","36","48","72"),width=5,style="Toolbar.TCombobox")
    size_box.pack(side="left",padx=(0,3))
    brush_icon=tk.PhotoImage(master=root,width=20,height=20)
    # Small original pixel icon: a diagonally oriented paintbrush.
    for y,x0,x1,color in ((2,13,16,"#314e71"),(3,12,17,"#314e71"),(4,11,17,"#314e71"),(5,10,16,"#314e71"),(6,9,15,"#314e71"),(7,8,14,"#314e71"),(8,7,13,"#314e71"),(9,6,12,"#e3a64b"),(10,5,11,"#e3a64b"),(11,4,10,"#e3a64b"),(12,3,9,"#e3a64b"),(13,3,8,"#e3a64b"),(14,2,7,"#bd7b35"),(15,2,6,"#bd7b35"),(16,1,4,"#314e71")):
        brush_icon.put(color,to=(x0,y,x1+1,y+1))
    brush_button=ttk.Button(editor_bar,image=brush_icon,text="Формат по образцу",style="Toolbar.TButton",command=lambda:brush())
    brush_button.image=brush_icon
    def tooltip(widget,label):
        tip=[None]
        pending=[None]
        def hide(_=None):
            if pending[0] is not None:
                widget.after_cancel(pending[0]);pending[0]=None
            if tip[0] is not None:
                tip[0].destroy();tip[0]=None
        def show():
            pending[0]=None
            tip[0]=tk.Toplevel(root)
            tip[0].wm_overrideredirect(True)
            tip[0].wm_geometry(f"+{widget.winfo_rootx()}+{widget.winfo_rooty()+widget.winfo_height()+5}")
            ttk.Label(tip[0],text=label,padding=6,relief="solid").pack()
        widget.bind("<Enter>",lambda e:pending.__setitem__(0,widget.after(600,show)))
        widget.bind("<Leave>",hide)
        widget.bind("<ButtonPress>",hide,add="+")
    tooltip(brush_button,"Формат по образцу")
    brush_button.pack(side="left",padx=(0,4))
    editor_paste=ttk.Button(bar,text="Вставить текст",command=lambda:paste(),style="Toolbar.TButton")
    save_button=ttk.Button(bar,text="Сохранить",command=lambda:save(),style="Toolbar.TButton")

    ttk.Button(editor_bar,text="↶",width=3,style="Toolbar.TButton",command=lambda:history(False)).pack(side="left")
    ttk.Button(editor_bar,text="↷",width=3,style="Toolbar.TButton",command=lambda:history(True)).pack(side="left",padx=(2,0))
    export_button=ttk.Button(bar,text="Экспорт PDF",command=lambda:export(),style="Accent.TButton")
    update_button=ttk.Button(bar,text="Обновить",command=lambda:update_action(),style="Toolbar.TButton")
    empty=Backdrop(root,"welcome.webp")
    empty.grid(row=1,sticky="nsew")
    welcome=ttk.Frame(empty,padding=(26,22),style="Welcome.TFrame")
    ttk.Label(welcome,text="MD to PDF",font=("TkDefaultFont",24,"bold"),style="Welcome.TLabel").pack()
    ttk.Label(welcome,text="Откройте или перетащите документ",style="Welcome.TLabel",padding=(0,8,0,0)).pack()
    ttk.Label(welcome,text="MD · TXT · DOCX",style="Welcome.TLabel",padding=(0,0,0,14)).pack()
    actions=ttk.Frame(welcome,style="Welcome.TFrame")
    actions.pack()
    drop=ttk.Button(actions,text="Открыть",command=choose,style="Accent.TButton")
    drop.pack(side="left",padx=(0,8))
    paste_button=ttk.Button(actions,text="Вставить текст",command=lambda:paste(),style="Toolbar.TButton")
    paste_button.pack(side="left")
    empty.center_widget(welcome)
    preview=PagePreview(root,lambda ranges:select(ranges),lambda e:context(e))
    status=tk.StringVar(value="")
    status_label=ttk.Label(root,textvariable=status,padding=(10,3))
    def message(value=""):
        status.set(value)
        if value:
            status_label.grid(row=2,sticky="ew")
        else:
            status_label.grid_remove()
    def load(name):
        if state["updating"] or not discard_ok():
            return
        try:
            path=Path(name).resolve()
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                raise ValueError("Выберите один файл MD, TXT или DOCX")
            ws=Workspace(path,**options())
            try:
                saved=ws.restore()
                if saved:
                    if saved not in (*BUILTINS,*profiles):
                        combo.configure(values=(*BUILTINS,*profiles,saved))
                    preset.set(saved)
            except Exception as exc:
                messagebox.showwarning("Сохранённые правки",str(exc),parent=root)
                ws=Workspace(path,**options())
        except Exception as exc:
            messagebox.showerror("Открытие документа",str(exc),parent=root)
            return
        show_workspace(ws,pasted=False)

    def paste(_=None, fresh=False):
        if state["updating"]:
            return
        previous=state["workspace"]
        current_text=None
        if state["pasted"] and previous:
            current_text=previous.source.read_text(encoding="utf-8")
        def clipboard():
            try:
                return root.clipboard_get()
            except tk.TclError:
                return ""
        initial=current_text if current_text is not None and not fresh else clipboard()
        dialog=tk.Toplevel(root)
        dialog.title("Вставить текст")
        dialog.transient(root)
        dialog.geometry("700x460")
        dialog.minsize(400,260)
        dialog.columnconfigure(0,weight=1)
        dialog.rowconfigure(0,weight=1)
        area=ttk.Frame(dialog,padding=10)
        area.grid(row=0,sticky="nsew")
        area.columnconfigure(0,weight=1)
        area.rowconfigure(0,weight=1)
        field=tk.Text(area,wrap="word",undo=True,exportselection=False,padx=10,pady=10)
        field.grid(row=0,column=0,sticky="nsew")
        scroll=ttk.Scrollbar(area,orient="vertical",command=field.yview)
        scroll.grid(row=0,column=1,sticky="ns")
        field.configure(yscrollcommand=scroll.set)
        field.insert("1.0",initial)
        field.edit_reset()
        actions=ttk.Frame(dialog,padding=(10,0,10,10))
        actions.grid(row=1,sticky="ew")
        def refill():
            value=clipboard()
            if value:
                field.delete("1.0","end")
                field.insert("1.0",value)
            field.focus_set()
        ttk.Button(actions,text="Из буфера",command=refill).pack(side="left")
        ttk.Button(actions,text="Очистить",command=lambda:field.delete("1.0","end")).pack(side="left",padx=5)
        def accept():
            value=field.get("1.0","end-1c")
            if not value.strip():
                messagebox.showinfo("Вставить текст","Введите или вставьте текст.",parent=dialog)
                return
            if current_text is not None and value==current_text:
                dialog.destroy()
                return
            if previous and (state["dirty"] or previous.actions):
                if not messagebox.askyesno("Заменить документ","Заменить текст? Правки оформления текущего документа не переносятся.",parent=dialog):
                    return
            try:
                ws=Workspace.from_clipboard(value,clipboard_dir.name,**options())
            except Exception as exc:
                messagebox.showerror("Вставить текст",str(exc),parent=dialog)
                return
            dialog.destroy()
            show_workspace(ws,pasted=True)
        ttk.Button(actions,text="Отмена",command=dialog.destroy).pack(side="right")
        ttk.Button(actions,text="Открыть в редакторе",style="Accent.TButton",command=accept).pack(side="right",padx=5)
        dialog.bind("<Escape>",lambda e:dialog.destroy())
        dialog.grab_set()
        field.focus_set()

    def paste_shortcut(event):
        # Native paste inside font/size/header entry fields must keep working.
        if event.widget.winfo_class() in ("Entry","TEntry","TCombobox","Text","Spinbox","TSpinbox"):
            return
        if event.widget.winfo_toplevel()!=root:
            return
        paste(fresh=True)
        return "break"

    def show_workspace(ws,pasted):
        state.update(workspace=ws,dirty=pasted,pasted=pasted,paste_pdf=None,result=None,
                     selection=[],brush=None,restore_selection=[])
        brush_button.configure(style="Toolbar.TButton")
        update_fields()
        empty.grid_remove()
        chrome.grid(row=0,sticky="ew")
        if not open_button.winfo_manager():
            open_button.pack(side="left",before=editor_bar) if editor_bar.winfo_manager() else open_button.pack(side="left")
        if not editor_paste.winfo_manager():
            editor_paste.pack(side="left",padx=(4,0))
        editor_paste.configure(text="Изменить текст" if pasted else "Вставить текст")
        editor_bar.pack(side="left")
        export_button.pack(side="right")
        save_button.pack(side="right",padx=4)
        preview.grid(row=1,sticky="nsew")
        render()
    def select(ranges):
        if state["rendering"]:
            return
        state["selection"]=ranges or []
        update_fields()
        if ranges is None:
            message("Этот фрагмент пока нельзя однозначно сопоставить с исходным текстом.")
        elif not state["rendering"]:
            message()
            if ranges and state["brush"]:
                copied=state["brush"]
                state["brush"]=None
                brush_button.configure(text="Кисть")
                apply_values(copied)

    def display_family(value):
        if value in ("","Разные"):
            return value
        key=re.sub(r"[^\w]","",value).casefold()
        return next((f for f in fonts if re.sub(r"[^\w]","",f).casefold()==key),value)

    def update_fields():
        ws=state["workspace"]
        ranges=state["selection"]
        if not ws or not ranges:
            role.set("Стиль фрагмента");font.set("Шрифт");size.set("pt")
            return
        current=ws.model.selection_role(ranges)
        labels={v:k for k,v in STYLES.items()}
        labels.update(mixed="Разные стили",li="Список",td="Ячейка",th="Шапка таблицы")
        role.set(labels.get(current,current))
        family,points=preview.selection_format()
        font.set(display_family(family) or "Шрифт")
        size.set(points or "pt")

    def render(preserve=False):
        state["generation"]+=1
        generation=state["generation"]
        state["result"]=None
        state["restore_selection"]=list(state["selection"]) if preserve else []
        state["selection"]=[]
        state["rendering"]=True
        if not preserve:
            update_fields()
        export_button.configure(state="disabled")
        for control in (styles,font_box,size_box,brush_button):
            control.configure(state="disabled")
        message("Вёрстка…")
        snapshot=state["workspace"].snapshot()
        def worker():
            try:
                events.put(("render",generation,render_snapshot(snapshot)))
            except Exception as exc:
                events.put(("render-error",generation,str(exc)))
        threading.Thread(target=worker,daemon=True).start()
    def switch(_=None):
        ws=state["workspace"]
        if not ws or state["updating"]:
            return
        try:
            ws.preset(**options())
            state["dirty"]=True
            render()
        except Exception as exc:
            messagebox.showerror("Стиль",str(exc),parent=root)
    combo.bind("<<ComboboxSelected>>",switch)
    def apply(_=None):
        style=STYLES.get(role.get())
        if not style or not state["workspace"] or state["rendering"]:
            return
        if not state["selection"]:
            update_fields()
            message("Выделите текст на странице.")
            return
        apply_values(style)
    def apply_values(style):
        if state["rendering"] or state["updating"] or not state["selection"]:
            update_fields()
            return
        try:
            state["workspace"].apply(style,state["selection"])
            state["dirty"]=True
            render(preserve=True)
        except (ValueError,TypeError) as exc:
            update_fields()
            message(str(exc))
    styles.bind("<<ComboboxSelected>>",apply)
    def font_change(_=None):
        value=font.get().strip()
        if value not in ("Шрифт","Разные"):
            apply_values("font:"+value)
    def size_change(_=None):
        value=size.get().strip().replace(",",".")
        if value not in ("pt","Разные"):
            apply_values("size:"+value)
    font_box.bind("<<ComboboxSelected>>",font_change)
    font_box.bind("<Return>",font_change)
    size_box.bind("<<ComboboxSelected>>",size_change)
    size_box.bind("<Return>",size_change)
    def cancel_brush(_=None):
        state["brush"]=None
        brush_button.configure(style="Toolbar.TButton")
        preview.canvas.configure(cursor="")
        if status.get().startswith("Формат по образцу"):
            message()
    def brush():
        if state["brush"]:
            cancel_brush()
            return
        if not state["selection"]:
            message("Выделите образец оформления.")
            return
        family,points=preview.selection_format()
        try:
            state["brush"]=state["workspace"].model.sample(state["selection"],display_family(family),points,preview.selection_color())
        except (ValueError,TypeError) as exc:
            message("Формат по образцу: "+str(exc))
            return
        brush_button.configure(style="Accent.TButton")
        preview.canvas.configure(cursor="crosshair")
        message("Формат по образцу: выберите другой фрагмент.")
    def save():
        if not state["workspace"] or state["updating"]:
            return
        try:
            ws=state["workspace"]
            if state["pasted"]:
                name=filedialog.asksaveasfilename(parent=root,defaultextension=".md",
                     initialfile="Документ.md",filetypes=[("Markdown","*.md")])
                if not name:
                    return
                ws.save_pasted(name,preset.get())
                state["pasted"]=False
                editor_paste.configure(text="Вставить текст")
                state["paste_pdf"]=None
                state["dirty"]=False
                render(preserve=True)
            else:
                ws.save(preset.get())
                state["dirty"]=False
            message("Правки сохранены")
            root.after(1800,lambda:message() if status.get()=="Правки сохранены" else None)
        except Exception as exc:
            messagebox.showerror("Сохранение",str(exc),parent=root)
    def history(redo):
        ws=state["workspace"]
        if ws and not state["updating"] and (ws.redo() if redo else ws.undo()):
            state["dirty"]=True
            render()
    def export():
        if not state["result"] or state["rendering"] or state["updating"]:
            return
        try:
            if state["pasted"]:
                name=state["paste_pdf"]
                if not name:
                    name=filedialog.asksaveasfilename(parent=root,defaultextension=".pdf",
                        initialfile="Документ.pdf",filetypes=[("PDF","*.pdf")])
                    if not name:
                        return
                write_pdf_bytes(name,state["result"][0])
                state["paste_pdf"]=name
            else:
                export_bytes(state["workspace"].source,state["result"][0])
            message("PDF сохранён")
            root.after(2200,lambda:message() if status.get()=="PDF сохранён" else None)
        except Exception as exc:
            messagebox.showerror("Экспорт PDF",str(exc),parent=root)
    def context(event):
        ws=state["workspace"]
        if not ws:
            return
        menu=tk.Menu(root,tearoff=False)
        if state["selection"]:
            for name in STYLES:
                menu.add_command(label=name,command=lambda n=name:(role.set(n),apply()))
        if ws.model.header_fields() is not None:
            menu.add_command(label="Изменить шапку…",command=edit_header)
        if menu.index("end") is not None:
            menu.tk_popup(event.x_root,event.y_root)
    def edit_header():
        ws=state["workspace"]
        fields=ws.model.header_fields()
        if fields is None:
            return
        dialog=tk.Toplevel(root)
        dialog.title("Шапка")
        dialog.transient(root)
        values=[]
        for i,(label,value) in enumerate(zip(("Название","Версия","Обновление"),fields)):
            ttk.Label(dialog,text=label,padding=6).grid(row=i,column=0,sticky="w")
            var=tk.StringVar(value=value)
            ttk.Entry(dialog,textvariable=var,width=40).grid(row=i,column=1,padx=6,pady=6)
            values.append(var)
        def save():
            ws.header([v.get() for v in values])
            state["dirty"]=True
            dialog.destroy()
            render()
        ttk.Button(dialog,text="Применить",command=save).grid(row=3,column=1,sticky="e",padx=6,pady=6)
        dialog.grab_set()
    if drag:
        for widget in (root,empty,welcome,drop,paste_button,editor_paste,preview.canvas):
            widget.drop_target_register(DND_FILES)
            def dropped(event):
                paths=root.tk.splitlist(event.data)
                if len(paths)==1:
                    load(paths[0])
                else:
                    messagebox.showinfo("MD to PDF","Откройте один документ.",parent=root)
            widget.dnd_bind("<<Drop>>",dropped)
    def check_update():
        try:
            from .updater import check
            events.put(("update",0,check()))
        except Exception:
            pass
    def update_action():
        release=state["update"]
        if not release or state["updating"]:
            return
        if sys.platform!="win32":
            webbrowser.open(release.url)
            return
        if not messagebox.askyesno("Обновление","Обновить программу и перезапустить?"+("\nНесохранённые изменения будут потеряны." if state["dirty"] else ""),parent=root):
            return
        state["updating"]=True
        message("Загрузка обновления…")
        def worker():
            try:
                from .updater import prepare_windows
                prepare_windows(release)
                events.put(("update-exit",0,None))
            except Exception as exc:
                events.put(("update-error",0,str(exc)))
        threading.Thread(target=worker,daemon=True).start()
    if getattr(sys,"frozen",False):
        root.after(400,lambda:threading.Thread(target=check_update,daemon=True).start())
    def poll():
        try:
            while True:
                kind,gen,value=events.get_nowait()
                if kind in ("render","render-error"):
                    if gen!=state["generation"]:
                        continue
                    state["rendering"]=False
                    styles.configure(state="readonly")
                    font_box.configure(state="normal")
                    size_box.configure(state="normal")
                    brush_button.configure(state="normal")
                    if kind=="render":
                        try:
                            preview.set_document(value)
                            state["result"]=value
                            preview.restore_selection(state["restore_selection"])
                            export_button.configure(state="normal")
                            message("Некоторые правки не применимы к этому пресету." if state["workspace"].skipped else "")
                        except Exception as exc:
                            message(str(exc))
                    else:
                        message(value)
                elif kind=="update" and value:
                    state["update"]=value
                    update_button.configure(text=("Обновить " if sys.platform=="win32" else "Скачать ")+"v"+value.version)
                    chrome.grid(row=0,sticky="ew")
                    update_button.pack(side="right",padx=6)
                elif kind=="update-exit":
                    preview.close()
                    root.destroy()
                    return
                elif kind=="update-error":
                    state["updating"]=False
                    message(value)
        except queue.Empty:
            pass
        root.after(80,poll)
    def close():
        if state["updating"]:
            return
        if state["dirty"] and not messagebox.askyesno("MD to PDF","Закрыть без сохранения изменений?",parent=root):
            return
        preview.close()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW",close)
    root.bind("<Escape>",cancel_brush)
    root.bind("<Control-o>",lambda e:choose())
    root.bind("<Control-v>",paste_shortcut)
    if sys.platform=="darwin":
        root.bind("<Command-v>",paste_shortcut)
    root.bind("<Control-s>",lambda e:save())
    root.bind("<Control-z>",lambda e:history(False))
    root.bind("<Control-y>",lambda e:history(True))
    root.after(80,poll)
    try:
        root.mainloop()
    finally:
        # In the production main loop this is reached on shutdown. A test may
        # substitute a nonblocking mainloop and keep the root alive.
        try:
            alive=root.winfo_exists()
        except tk.TclError:
            alive=False
        if not alive:
            clipboard_dir.cleanup()

if __name__=="__main__":
    main()
