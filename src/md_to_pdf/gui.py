"""Minimal single-document editor with real PDF page preview."""
from __future__ import annotations
import queue
import sys
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from . import __version__
from .inputs import EXTENSIONS
from .profiles import load_profile,list_profiles
from .profile_editor import manage_profiles
from .workspace import Workspace,render_snapshot,export_bytes
from .page_preview import PagePreview

BUILTINS={"Технический":"technical","Деловой":"business","Учебный":"academic","Granulex":"granulex"}
STYLES={"Текст":"normal","Заголовок 1":"h1","Заголовок 2":"h2","Заголовок 3":"h3",
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
    root.title("MD to PDF • "+__version__)
    root.geometry("1000x780")
    root.minsize(660,480)
    root.columnconfigure(0,weight=1)
    root.rowconfigure(1,weight=1)
    events=queue.Queue()
    state={"workspace":None,"result":None,"generation":0,"rendering":False,
           "dirty":False,"selection":[],"update":None,"updating":False}
    profiles=list_profiles()
    preset=tk.StringVar(value="Технический")
    role=tk.StringVar(value="Стиль фрагмента")
    bar=ttk.Frame(root,padding=(10,8))
    bar.grid(row=0,sticky="ew")
    def options():
        key=preset.get()
        p=load_profile(profiles[key]) if key in profiles else None
        return dict(template=p.base if p else BUILTINS[key],profile=p)
    def discard_ok():
        return not state["dirty"] or messagebox.askyesno("MD to PDF","Открыть другой документ без экспорта изменений?",parent=root)
    def choose():
        name=filedialog.askopenfilename(parent=root,filetypes=[("Документы","*.md *.markdown *.mdown *.txt *.docx")])
        if name:
            load(name)
    open_button=ttk.Button(bar,text="Открыть",command=choose)
    open_button.pack(side="left")
    editor_bar=ttk.Frame(bar)
    combo=ttk.Combobox(editor_bar,textvariable=preset,values=(*BUILTINS,*profiles),state="readonly",width=17)
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
    ttk.Button(editor_bar,text="⚙",width=3,command=lambda:manage_profiles(root,selected=preset.get(),builtins=BUILTINS,on_change=refresh_profiles)).pack(side="left",padx=(0,6))
    styles=ttk.Combobox(editor_bar,textvariable=role,values=tuple(STYLES),state="readonly",width=19)
    styles.pack(side="left",padx=(0,4))
    ttk.Button(editor_bar,text="↶",width=3,command=lambda:history(False)).pack(side="left")
    ttk.Button(editor_bar,text="↷",width=3,command=lambda:history(True)).pack(side="left",padx=(2,0))
    export_button=ttk.Button(bar,text="Экспорт PDF",command=lambda:export())
    update_button=ttk.Button(bar,text="Обновить",command=lambda:update_action())
    empty=ttk.Frame(root)
    empty.grid(row=1,sticky="nsew")
    empty.columnconfigure(0,weight=1)
    empty.rowconfigure(0,weight=1)
    drop=ttk.Button(empty,text="Открыть документ\nили перетащить MD, TXT, DOCX",command=choose)
    drop.grid(row=0,column=0,ipadx=40,ipady=35)
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
        except Exception as exc:
            messagebox.showerror("Открытие документа",str(exc),parent=root)
            return
        state.update(workspace=ws,dirty=False,result=None,selection=[])
        empty.grid_remove()
        editor_bar.pack(side="left")
        export_button.pack(side="right")
        preview.grid(row=1,sticky="nsew")
        render()
    def select(ranges):
        state["selection"]=ranges or []
        if ranges is None:
            message("Этот фрагмент пока нельзя однозначно сопоставить с исходным текстом.")
        elif not state["rendering"]:
            message()
    def render():
        state["generation"]+=1
        generation=state["generation"]
        state["result"]=None
        state["selection"]=[]
        state["rendering"]=True
        export_button.configure(state="disabled")
        styles.configure(state="disabled")
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
        role.set("Стиль фрагмента")
        if not style or not state["workspace"] or state["rendering"]:
            return
        if not state["selection"]:
            message("Выделите текст на странице.")
            return
        try:
            state["workspace"].apply(style,state["selection"])
            state["dirty"]=True
            render()
        except ValueError as exc:
            message(str(exc))
    styles.bind("<<ComboboxSelected>>",apply)
    def history(redo):
        ws=state["workspace"]
        if ws and not state["updating"] and (ws.redo() if redo else ws.undo()):
            state["dirty"]=True
            render()
    def export():
        if not state["result"] or state["rendering"] or state["updating"]:
            return
        try:
            export_bytes(state["workspace"].source,state["result"][0])
            state["dirty"]=False
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
        for widget in (root,drop,preview.canvas):
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
        if not messagebox.askyesno("Обновление","Обновить программу и перезапустить?"+("\nНеэкспортированные изменения будут потеряны." if state["dirty"] else ""),parent=root):
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
                    if kind=="render":
                        try:
                            preview.set_document(value)
                            state["result"]=value
                            export_button.configure(state="normal")
                            message("Некоторые правки не применимы к этому пресету." if state["workspace"].skipped else "")
                        except Exception as exc:
                            message(str(exc))
                    else:
                        message(value)
                elif kind=="update" and value:
                    state["update"]=value
                    update_button.configure(text=("Обновить " if sys.platform=="win32" else "Скачать ")+"v"+value.version)
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
        if state["dirty"] and not messagebox.askyesno("MD to PDF","Закрыть без экспорта изменений?",parent=root):
            return
        preview.close()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW",close)
    root.bind("<Control-o>",lambda e:choose())
    root.bind("<Control-z>",lambda e:history(False))
    root.bind("<Control-y>",lambda e:history(True))
    root.after(80,poll)
    root.mainloop()

if __name__=="__main__":
    main()
