"""Minimal single-document editor with real PDF page preview."""
from __future__ import annotations
import queue
import json
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
from .import_text import COPY_EXTENSIONS,copy_document
from .profiles import Profile,load_profile,list_profiles
from dataclasses import replace
from .profile_editor import edit_profile,builtin_profile
from .workspace import Workspace,render_snapshot,export_bytes,write_pdf_bytes
from .ui_skin import Backdrop,RoundedPanel,round_window,configure_theme,toolbar_icon,SURFACE,INK
from .page_preview import PagePreview

BUILTINS={"Технический":"technical","Деловой":"business","Учебный":"academic","Granulex":"granulex","Фантом":"phantom"}
STYLES={"Текст":"normal","Заголовок 1":"h1","Заголовок 2":"h2","Заголовок 3":"h3",
        "Заголовок 4":"h4","Заголовок 5":"h5","Заголовок 6":"h6",
        "Цитата":"quote","Примечание":"note","Предупреждение":"warning","Блок кода":"code-block",
        "Версия":"meta-version","Последнее обновление":"meta-updated",
        "Полужирный":"bold","Курсив":"italic","Код":"code","Акцент":"accent"}

STRUCTURE_STYLES={"Маркированный список":"bullet","Нумерованный список":"numbered","Ячейка таблицы":"table-cell","Заголовок таблицы":"table-heading"}
PRESET_ACTIONS=("Настроить пресет…","Создать пресет…","Импорт пресета…")

def ask_save_changes(parent):
    """Return save, discard or cancel; Escape and the window close mean cancel."""
    result="cancel"
    dialog=tk.Toplevel(parent)
    round_window(dialog)
    dialog.title("MD to PDF")
    dialog.transient(parent)
    dialog.resizable(False,False)
    frame=ttk.Frame(dialog,padding=20)
    frame.pack(fill="both",expand=True)
    ttk.Label(frame,text="Сохранить изменения?",font=("TkDefaultFont",12,"bold")).pack(anchor="w",pady=(0,16))
    actions=ttk.Frame(frame)
    actions.pack(fill="x")
    def finish(value):
        nonlocal result
        result=value
        dialog.destroy()
    primary=ttk.Button(actions,text="Сохранить",style="Accent.TButton",command=lambda:finish("save"))
    primary.pack(side="left")
    ttk.Button(actions,text="Не сохранять",command=lambda:finish("discard")).pack(side="left",padx=8)
    ttk.Button(actions,text="Отмена",command=lambda:finish("cancel")).pack(side="left")
    dialog.protocol("WM_DELETE_WINDOW",lambda:finish("cancel"))
    dialog.bind("<Escape>",lambda e:finish("cancel"))
    dialog.bind("<Return>",lambda e:finish("save"))
    dialog.update_idletasks()
    x=parent.winfo_rootx()+(parent.winfo_width()-dialog.winfo_reqwidth())//2
    y=parent.winfo_rooty()+(parent.winfo_height()-dialog.winfo_reqheight())//2
    dialog.geometry(f"+{max(0,x)}+{max(0,y)}")
    previous=parent.grab_current()
    dialog.grab_set()
    primary.focus_set()
    parent.wait_window(dialog)
    if previous is not None and previous.winfo_exists():
        previous.grab_set()
    return result


def confirm_changes(parent, dirty, save_callback):
    if not dirty:
        return True
    answer=ask_save_changes(parent)
    if answer=="save":
        return bool(save_callback())
    return answer=="discard"


def main(ready_file=None):
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
           "dirty":False,"home":True,"importing":False,"configuring":False,"pasted":False,"paste_pdf":None,"selection":[],"brush":None,"restore_selection":[],"update":None,"updating":False}
    profiles=list_profiles()
    preset=tk.StringVar(value="Технический")
    role=tk.StringVar(value="Стиль фрагмента")
    font=tk.StringVar(value="Шрифт")
    size=tk.StringVar(value="pt")
    chrome=ttk.Frame(root,style="Toolbar.TFrame")
    banner=Backdrop(chrome,"toolbar.svg",banner=True,height=23)
    banner.pack(fill="x")
    bar=ttk.Frame(chrome,padding=(10,6),style="Toolbar.TFrame")
    bar.pack(fill="x")
    bar.columnconfigure(1,weight=1)
    left_tools=ttk.Frame(bar,style="Toolbar.TFrame")
    right_tools=ttk.Frame(bar,style="Toolbar.TFrame")
    left_tools.grid(row=0,column=0,sticky="w")
    right_tools.grid(row=0,column=2,sticky="e")
    def options():
        key=preset.get()
        p=load_profile(profiles[key]) if key in profiles else None
        if key not in BUILTINS and p is None:
            return state["workspace"].options if state["workspace"] else dict(template="technical",profile=None)
        return dict(template=p.base if p else BUILTINS[key],profile=p)
    def discard_ok(parent=None):
        owner=parent or root
        return confirm_changes(owner,state["dirty"],lambda:save(parent=owner,reflow=False))
    def choose():
        name=filedialog.askopenfilename(parent=root,filetypes=[("Документы","*.md *.markdown *.mdown *.txt *.docx *.pdf *.xlsx *.xls *.csv"),("Все файлы","*.*")])
        if name:
            load(name)
    open_button=ttk.Button(left_tools,text="Открыть",command=lambda:go_home(),style="Toolbar.TButton")
    editor_bar=ttk.Frame(bar,style="Toolbar.TFrame")
    combo=ttk.Combobox(editor_bar,textvariable=preset,values=(*BUILTINS,*profiles,*PRESET_ACTIONS),state="readonly",width=17,style="Toolbar.TCombobox")
    combo.pack(side="left",padx=(8,2))
    def refresh_profiles(path=None):
        nonlocal profiles
        profiles=list_profiles()
        combo.configure(values=(*BUILTINS,*profiles,*PRESET_ACTIONS))
        if path:
            label=next((k for k,v in profiles.items() if v==path),None)
            if label:
                preset.set(label)
                switch()

    styles=ttk.Combobox(editor_bar,textvariable=role,values=tuple(STYLES),state="readonly",width=19,style="Toolbar.TCombobox")
    styles.pack(side="left",padx=(0,4))
    fonts=sorted(set(tkfont.families(root))|{"Montserrat","Roboto Mono","Arial","Times New Roman","DejaVu Sans"},key=str.casefold)
    font_box=ttk.Combobox(editor_bar,textvariable=font,values=tuple(f for f in fonts if not f.startswith("@")),width=17,style="Toolbar.TCombobox")
    font_box.pack(side="left",padx=(0,3))
    size_box=ttk.Combobox(editor_bar,textvariable=size,values=("6","7","8","9","10","11","12","14","16","18","20","24","28","32","36","48","72"),width=5,style="Toolbar.TCombobox")
    size_box.pack(side="left",padx=(0,3))
    brush_icon=toolbar_icon(root,"format")
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
            ttk.Label(tip[0],text=label() if callable(label) else label,padding=6,relief="solid").pack()
        def enter(_=None):
            hide()
            pending[0]=widget.after(600,show)
        widget.bind("<Enter>",enter)
        widget.bind("<Unmap>",hide,add="+")
        widget.bind("<Leave>",hide)
        widget.bind("<ButtonPress>",hide,add="+")
    def iconify(widget,name):
        icon=toolbar_icon(root,name)
        widget.configure(image=icon,compound="none")
        widget.image=icon
        tooltip(widget,lambda:widget.cget("text"))
        return widget
    iconify(open_button,"open")
    tooltip(brush_button,"Формат по образцу")
    brush_button.pack(side="left",padx=(0,4))
    def structure_button(name,label,command):
        icon=toolbar_icon(root,name)
        widget=ttk.Button(editor_bar,image=icon,text=label,style="Toolbar.TButton",command=command)
        widget.image=icon
        widget.pack(side="left",padx=1)
        tooltip(widget,label)
        return widget
    bullet_button=structure_button("bullet","Маркированный список",lambda:toggle_list("bullet"))
    numbered_button=structure_button("numbered","Нумерованный список",lambda:toggle_list("numbered"))
    table_button=structure_button("table","Таблица",lambda:table_menu())
    editor_paste=ttk.Button(left_tools,text="Вставить текст",command=lambda:paste(),style="Toolbar.TButton")
    save_button=ttk.Button(right_tools,text="Сохранить",command=lambda:save(),style="Toolbar.TButton")

    iconify(ttk.Button(editor_bar,text="Отменить (Ctrl+Z)",style="Toolbar.TButton",command=lambda:history(False)),"undo").pack(side="left")
    iconify(ttk.Button(editor_bar,text="Повторить (Ctrl+Y)",style="Toolbar.TButton",command=lambda:history(True)),"redo").pack(side="left",padx=(2,0))
    export_button=ttk.Button(right_tools,text="Экспорт PDF",command=lambda:export(),style="Accent.TButton")
    update_button=ttk.Button(right_tools,text="Обновить",command=lambda:update_action(),style="Toolbar.TButton")
    for widget,name in ((editor_paste,"paste"),(save_button,"save"),(export_button,"pdf"),(update_button,"update")):
        iconify(widget,name)
    for widget,label in ((combo,"Пресет документа"),(styles,"Стиль фрагмента"),(font_box,"Шрифт"),(size_box,"Размер шрифта, пт")):
        tooltip(widget,label)
    empty=Backdrop(root,"welcome.svg")
    empty.grid(row=1,sticky="nsew")
    welcome=ttk.Frame(empty,padding=(18,12),style="Welcome.TFrame")
    ttk.Label(welcome,text="MD to PDF",font=("TkDefaultFont",24,"bold"),style="Welcome.TLabel").pack()
    ttk.Label(welcome,text="Откройте или перетащите документ",style="Welcome.TLabel",padding=(0,8,0,0)).pack()
    ttk.Label(welcome,text="MD · TXT · PDF · DOCX · XLSX · XLS · CSV",style="Welcome.TLabel",padding=(0,0,0,14)).pack()
    actions=ttk.Frame(welcome,style="Welcome.TFrame")
    actions.pack()
    drop=ttk.Button(actions,text="Открыть",command=choose,style="Accent.TButton")
    tooltip(drop,"Выбрать файл")
    drop.pack(side="left",padx=(0,8))
    paste_button=ttk.Button(actions,text="Вставить текст",command=lambda:paste(),style="Toolbar.TButton")
    paste_button.pack(side="left")
    tooltip(paste_button,"Вставить текст из буфера (Ctrl+V)")
    back_button=iconify(ttk.Button(actions,text="Вернуться к документу",command=lambda:back_to_document(),style="Toolbar.TButton"),"back")
    empty.center_widget(welcome)
    empty.bind("<Button-1>",lambda e:empty.focus_set())
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
        if state["updating"] or state["configuring"] or not confirm_input_discard():
            return
        try:
            path=Path(name).resolve()
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS|COPY_EXTENSIONS:
                raise ValueError("Выберите MD, TXT, PDF, DOCX, XLSX, XLS или CSV")
            if path.suffix.lower() in COPY_EXTENSIONS:
                value=copy_document(path)
                show_input(value)
                return
            if not discard_ok():
                return
            ws=Workspace(path,**options())
            try:
                saved=ws.restore()
                if saved:
                    if saved not in (*BUILTINS,*profiles):
                        combo.configure(values=(*BUILTINS,*profiles,saved,*PRESET_ACTIONS))
                    preset.set(saved)
            except Exception as exc:
                messagebox.showwarning("Сохранённые правки",str(exc),parent=root)
                ws=Workspace(path,**options())
        except Exception as exc:
            messagebox.showerror("Открытие документа",str(exc),parent=root)
            return
        show_workspace(ws,pasted=False)

    # Importing text is a view in the same window, never a Toplevel.
    input_view=RoundedPanel(root,padding=24,radius=18)
    input_content=input_view.content
    input_content.columnconfigure(0,weight=1)
    input_content.rowconfigure(1,weight=1)
    top=ttk.Frame(input_content,style="Welcome.TFrame")
    top.grid(row=0,sticky="ew",pady=(0,12))
    ttk.Label(top,text="Текст документа",font=("TkDefaultFont",16,"bold"),style="Welcome.TLabel").pack(side="left")
    iconify(ttk.Button(top,text="Открыть файл…",style="Toolbar.TButton",command=choose),"open").pack(side="right")
    text_surface=RoundedPanel(input_content,radius=14,shadow=False,padding=14,background="#ffffff")
    text_surface.grid(row=1,sticky="nsew")
    area=text_surface.content
    area.columnconfigure(0,weight=1)
    area.rowconfigure(0,weight=1)
    field=tk.Text(area,wrap="word",undo=True,exportselection=False,padx=16,pady=16,
                  font=("TkDefaultFont",12),foreground=INK,background="#ffffff",
                  relief="flat",highlightthickness=0,insertbackground=INK)
    field.grid(row=0,column=0,sticky="nsew")
    scroll=ttk.Scrollbar(area,orient="vertical",command=field.yview)
    scroll.grid(row=0,column=1,sticky="ns")
    field.configure(yscrollcommand=scroll.set)
    input_actions=ttk.Frame(input_content,style="Welcome.TFrame")
    input_actions.grid(row=2,sticky="ew",pady=(12,0))
    def clipboard():
        try:
            return root.clipboard_get()
        except tk.TclError:
            return ""
    def input_value():
        return field.get("1.0","end-1c")
    def confirm_input_discard():
        if not state["importing"] or not input_value().strip():
            return True
        return messagebox.askyesno("MD to PDF","Заменить введённый текст?",parent=root)
    def refill():
        value=clipboard()
        if value:
            field.delete("1.0","end")
            field.insert("1.0",value)
        field.focus_set()
    def go_home():
        if state["updating"] or state["configuring"]:
            return
        state["home"]=True
        state["importing"]=False
        cancel_brush()
        input_view.grid_remove()
        preview.grid_remove()
        left_tools.grid_remove()
        editor_bar.grid_remove()
        save_button.pack_forget()
        export_button.pack_forget()
        chrome.grid_remove()
        if state["update"]:
            chrome.grid(row=0,sticky="ew")
        if state["workspace"] is not None:
            back_button.pack(side="left",padx=(8,0))
        else:
            back_button.pack_forget()
        empty.grid(row=1,sticky="nsew")
        message()
        empty.focus_set()

    def back_to_document():
        if state["workspace"] is None:
            return
        state["home"]=False
        state["importing"]=False
        empty.grid_remove()
        input_view.grid_remove()
        left_tools.grid()
        chrome.grid(row=0,sticky="ew")
        export_button.pack(side="right")
        save_button.pack(side="right",padx=4)
        preview.grid(row=1,sticky="nsew")
        arrange_toolbar()
        message()

    def cancel_input():
        if state["home"] or state["workspace"] is None:
            go_home()
        else:
            back_to_document()
        message()
    def accept_input():
        if state["updating"] or not state["importing"]:
            return
        value=input_value()
        if not value.strip():
            message("Введите или вставьте текст.")
            field.focus_set()
            return
        previous=state["workspace"]
        if state["pasted"] and previous and value==previous.source.read_text(encoding="utf-8"):
            cancel_input()
            return
        try:
            ws=Workspace.from_clipboard(value,clipboard_dir.name,**options())
        except Exception as exc:
            message(str(exc))
            return
        if previous and not discard_ok():
            return
        show_workspace(ws,pasted=True)
    iconify(ttk.Button(input_actions,text="Из буфера",command=refill,style="Toolbar.TButton"),"paste").pack(side="left")
    iconify(ttk.Button(input_actions,text="Очистить",command=lambda:field.delete("1.0","end"),style="Toolbar.TButton"),"clear").pack(side="left",padx=6)
    ttk.Button(input_actions,text="Открыть в редакторе",style="Accent.TButton",command=accept_input).pack(side="right")
    ttk.Button(input_actions,text="Отмена",command=cancel_input,style="Toolbar.TButton").pack(side="right",padx=6)
    def paste(_=None,fresh=False):
        if state["updating"] or state["configuring"]:
            return
        if state["importing"]:
            field.focus_set()
            return
        previous=state["workspace"]
        initial=previous.source.read_text(encoding="utf-8") if state["pasted"] and previous and not fresh and not state["home"] else clipboard()
        show_input(initial)
    def show_input(initial):
        field.delete("1.0","end")
        field.insert("1.0",initial)
        field.edit_reset()
        state["importing"]=True
        cancel_brush()
        empty.grid_remove()
        preview.grid_remove()
        chrome.grid_remove()
        input_view.grid(row=1,sticky="nsew",padx=14,pady=12)
        message()
        field.focus_set()
    field.bind("<Control-Return>",lambda e:(accept_input(),"break")[1])
    field.bind("<Escape>",lambda e:(cancel_input(),"break")[1])

    def paste_shortcut(event):
        # Native paste inside font/size/header entry fields must keep working.
        if event.widget.winfo_class() in ("Entry","TEntry","TCombobox","Text","Spinbox","TSpinbox"):
            return
        if event.widget.winfo_toplevel()!=root:
            return
        paste(fresh=True)
        return "break"

    def arrange_toolbar(_=None):
        if state["workspace"] is None or state["home"] or state["importing"] or state["configuring"]:
            return
        need=left_tools.winfo_reqwidth()+editor_bar.winfo_reqwidth()+right_tools.winfo_reqwidth()+30
        if root.winfo_width()>=need:
            editor_bar.grid(row=0,column=1,columnspan=1,sticky="w")
        else:
            editor_bar.grid(row=1,column=0,columnspan=3,sticky="w",pady=(5,0))

    bar.bind("<Configure>",arrange_toolbar)

    def show_workspace(ws,pasted):
        nonlocal active_label
        active_label=preset.get()
        state.update(workspace=ws,dirty=pasted,home=False,importing=False,pasted=pasted,paste_pdf=None,result=None,
                     selection=[],brush=None,restore_selection=[])
        cancel_brush()
        update_fields()
        input_view.grid_remove()
        empty.grid_remove()
        chrome.grid(row=0,sticky="ew")
        left_tools.grid()
        if not open_button.winfo_manager():
            open_button.pack(side="left")
        if not editor_paste.winfo_manager():
            editor_paste.pack(side="left",padx=(4,0))
        editor_paste.configure(text="Вставить текст")
        export_button.pack(side="right")
        save_button.pack(side="right",padx=4)
        arrange_toolbar()
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
                cancel_brush()
                apply_values(copied)

    def display_family(value):
        if value in ("","Разные"):
            return value
        key=re.sub(r"[^\w]","",value).casefold()
        return next((f for f in fonts if re.sub(r"[^\w]","",f).casefold()==key),value)

    profile_view=ttk.Frame(root,style="Welcome.TFrame")
    profile_view.columnconfigure(0,weight=1)
    profile_view.rowconfigure(0,weight=1)
    active_label="Технический"
    profile_cancel=None
    def configure_preset(action):
        nonlocal profile_cancel
        ws=state["workspace"]
        if not ws or state["rendering"]:
            return
        existing=None
        try:
            if action==PRESET_ACTIONS[2]:
                name=filedialog.askopenfilename(parent=root,filetypes=[("Профиль","*.json")])
                if not name:
                    return
                initial=load_profile(Path(name))
            elif action==PRESET_ACTIONS[1]:
                initial=Profile(name="Мой стиль")
            else:
                existing=profiles.get(active_label)
                initial=ws.options.get("profile") or builtin_profile(ws.options["template"],active_label)
                if existing is None:
                    initial=replace(initial,name=initial.name+" — мой стиль")
        except Exception as exc:
            message(str(exc))
            return
        state["configuring"]=True
        chrome.grid_remove()
        preview.grid_remove()
        profile_view.grid(row=1,sticky="nsew")
        def back():
            nonlocal profile_cancel
            profile_cancel=None
            state["configuring"]=False
            profile_view.grid_remove()
            chrome.grid(row=0,sticky="ew")
            preview.grid(row=1,sticky="nsew")
        profile_cancel=edit_profile(profile_view,initial=initial,existing=existing,on_save=refresh_profiles,embedded=True,on_close=back)

    def update_fields():
        ws=state["workspace"]
        ranges=state["selection"]
        styles.configure(values=tuple(STYLES))
        for button in (bullet_button,numbered_button,table_button):
            button.configure(state="disabled",style="Toolbar.TButton")
        if not ws or not ranges:
            role.set("Стиль фрагмента");font.set("Шрифт");size.set("pt")
            return
        current=ws.model.selection_role(ranges)
        if not any(ws.model.blocks()[i].locked for i,_,_ in ranges):
            bullet_button.configure(state="normal",style="Accent.TButton" if current=="bullet" else "Toolbar.TButton")
            numbered_button.configure(state="normal",style="Accent.TButton" if current=="numbered" else "Toolbar.TButton")
        try:
            ws.model.table_settings(ranges)
            table_button.configure(state="normal",style="Accent.TButton")
        except ValueError:
            pass
        labels={v:k for k,v in {**STYLES,**STRUCTURE_STYLES}.items()}
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
        for control in (styles,font_box,size_box,brush_button,bullet_button,numbered_button,table_button):
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
        nonlocal active_label
        choice=preset.get()
        if choice in PRESET_ACTIONS:
            preset.set(active_label)
            configure_preset(choice)
            return
        ws=state["workspace"]
        if not ws or state["updating"]:
            return
        try:
            ws.preset(**options())
            active_label=preset.get()
            state["dirty"]=True
            render()
        except Exception as exc:
            messagebox.showerror("Стиль",str(exc),parent=root)
    combo.bind("<<ComboboxSelected>>",switch)
    def apply(_=None):
        if role.get()=="Параметры таблицы…":
            update_fields()
            table_dialog()
            return
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
            state["selection"]=state["workspace"].apply(style,state["selection"])
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
    def save(parent=None,reflow=True):
        if not state["workspace"] or state["updating"]:
            return False
        owner=parent or root
        try:
            ws=state["workspace"]
            if state["pasted"]:
                name=filedialog.asksaveasfilename(parent=owner,defaultextension=".md",
                     initialfile="Документ.md",filetypes=[("Markdown","*.md")])
                if not name:
                    return False
                ws.save_pasted(name,preset.get())
                state["pasted"]=False
                editor_paste.configure(text="Вставить текст")
                arrange_toolbar()
                state["paste_pdf"]=None
                state["dirty"]=False
                if reflow:
                    render(preserve=True)
            else:
                ws.save(preset.get())
                state["dirty"]=False
            message("Правки сохранены")
            root.after(1800,lambda:message() if status.get()=="Правки сохранены" else None)
            return True
        except Exception as exc:
            messagebox.showerror("Сохранение",str(exc),parent=owner)
            return False
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
    def toggle_list(kind):
        if not state["selection"]:
            return
        current=state["workspace"].model.selection_role(state["selection"])
        apply_values("normal" if current==kind else kind)

    def table_menu():
        if not state["selection"] or state["rendering"]:
            return
        menu=tk.Menu(root,tearoff=False)
        for label,kind in (("Заголовок таблицы","table-heading"),("Ячейка таблицы","table-cell"),("Строка заголовков","table-row-heading"),("Обычная строка","table-row-cell")):
            menu.add_command(label=label,command=lambda k=kind:apply_values(k))
        menu.add_separator()
        menu.add_command(label="Параметры таблицы…",command=table_dialog)
        menu.tk_popup(table_button.winfo_rootx(),table_button.winfo_rooty()+table_button.winfo_height())

    def table_dialog():
        ws=state["workspace"]
        ranges=list(state["selection"])
        if not ws or state["rendering"] or not ranges:
            return
        try:
            settings=ws.model.table_settings(ranges)
        except ValueError as exc:
            message(str(exc))
            return
        dialog=tk.Toplevel(root)
        round_window(dialog)
        dialog.title("Параметры таблицы")
        dialog.transient(root)
        dialog.columnconfigure(1,weight=1)
        width=tk.StringVar(value=str(settings["width"]))
        aligns={"Слева":"left","По центру":"center","Справа":"right"}
        grids={"Как в пресете":"preset","Показать":"show","Скрыть":"hide"}
        alignment=tk.StringVar(value=next(k for k,v in aligns.items() if v==settings["align"]))
        grid=tk.StringVar(value=next(k for k,v in grids.items() if v==settings["grid"]))
        for i,label in enumerate(("Ширина, %","Положение таблицы","Границы ячеек")):
            ttk.Label(dialog,text=label,padding=8).grid(row=i,column=0,sticky="w")
        ttk.Spinbox(dialog,from_=20,to=100,increment=5,textvariable=width,width=8).grid(row=0,column=1,sticky="ew",padx=8,pady=6)
        ttk.Combobox(dialog,textvariable=alignment,values=tuple(aligns),state="readonly").grid(row=1,column=1,sticky="ew",padx=8,pady=6)
        ttk.Combobox(dialog,textvariable=grid,values=tuple(grids),state="readonly").grid(row=2,column=1,sticky="ew",padx=8,pady=6)
        def accept():
            try:
                value=int(width.get())
                if not 20<=value<=100:
                    raise ValueError()
            except ValueError:
                messagebox.showinfo("Параметры таблицы","Ширина от 20 до 100 %.",parent=dialog)
                return
            dialog.destroy()
            state["selection"]=ranges
            apply_values("table-settings:"+json.dumps({"width":value,"align":aligns[alignment.get()],"grid":grids[grid.get()]}))
        ttk.Button(dialog,text="Применить",style="Accent.TButton",command=accept).grid(row=3,column=1,sticky="e",padx=8,pady=8)
        dialog.bind("<Escape>",lambda e:dialog.destroy())
        dialog.grab_set()

    def context(event):
        ws=state["workspace"]
        if not ws:
            return
        menu=tk.Menu(root,tearoff=False)
        if state["selection"]:
            for name,kind in {**STYLES,**STRUCTURE_STYLES}.items():
                menu.add_command(label=name,command=lambda k=kind:apply_values(k))
        if state["selection"]:
            try:
                ws.model.table_settings(state["selection"])
                menu.add_command(label="Параметры таблицы…",command=table_dialog)
            except ValueError:
                pass
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
        round_window(dialog)
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
        for widget in (root,empty,welcome,drop,paste_button,editor_paste,back_button,preview.canvas,input_view,input_content,text_surface,area,field):
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
        from .updater import WINDOWS_SETUP
        prompt="Запустить установщик обновления? Программа закроется; завершите установку в мастере." if release.asset==WINDOWS_SETUP else "Обновить программу и перезапустить?"
        if not messagebox.askyesno("Обновление",prompt,parent=root):
            return
        if not confirm_input_discard() or not discard_ok():
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
                            if not state["home"] and not state["importing"]:
                                message("Некоторые правки не применимы к этому пресету." if state["workspace"].skipped else "")
                        except Exception as exc:
                            message(str(exc))
                    else:
                        message(value)
                elif kind=="update" and value:
                    state["update"]=value
                    update_button.configure(text=("Обновить " if sys.platform=="win32" else "Скачать ")+"v"+value.version)
                    if not state["importing"] and not state["configuring"]:
                        chrome.grid(row=0,sticky="ew")
                    if state["home"]:
                        left_tools.grid_remove()
                        editor_bar.grid_remove()
                        save_button.pack_forget()
                        export_button.pack_forget()
                    update_button.pack(side="right",padx=6)
                    arrange_toolbar()
                elif kind=="update-exit":
                    preview.close()
                    root.destroy()
                    return
                elif kind=="update-error":
                    state["updating"]=False
                    messagebox.showerror("Обновление",value,parent=root)
                    message(value)
        except queue.Empty:
            pass
        root.after(80,poll)
    def close():
        if state["updating"]:
            return
        if state["configuring"]:
            if profile_cancel:
                profile_cancel()
            return
        if state["importing"] and not confirm_input_discard():
            return
        if not discard_ok():
            return
        preview.close()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW",close)
    root.bind("<Escape>",lambda e:profile_cancel() if state["configuring"] and profile_cancel else cancel_input() if state["importing"] else back_to_document() if state["home"] else cancel_brush())
    root.bind("<Control-o>",lambda e:choose() if state["home"] or state["importing"] else go_home())
    root.bind("<Control-v>",paste_shortcut)
    if sys.platform=="darwin":
        root.bind("<Command-v>",paste_shortcut)
    root.bind("<Control-s>",lambda e:None if state["importing"] or state["configuring"] or state["home"] else save())
    root.bind("<Control-z>",lambda e:None if state["importing"] or state["configuring"] or state["home"] else history(False))
    root.bind("<Control-y>",lambda e:None if state["importing"] or state["configuring"] or state["home"] else history(True))
    root.after(80,poll)
    if ready_file is not None:
        def signal_ready():
            if root.winfo_ismapped() and empty.winfo_ismapped():
                path=Path(ready_file)
                tmp=path.with_suffix('.tmp')
                tmp.write_text(__version__,encoding='ascii')
                tmp.replace(path)
            else:
                root.after(250,signal_ready)
        root.after(300,signal_ready)
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
