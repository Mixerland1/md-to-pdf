"""Single-window GUI acceptance smoke on virtual display."""
import tempfile,time
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk
from md_to_pdf import gui
from md_to_pdf.page_preview import PagePreview
from md_to_pdf.ui_skin import Backdrop,RoundedPanel

def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)

def buttons(widget):
    return {str(w.cget("text")):w for w in descendants(widget) if isinstance(w,ttk.Button) and w.winfo_ismapped()}

root=tk.Tk()
try:
    with tempfile.TemporaryDirectory() as d:
        source=Path(d)/"guide.md"
        source.write_text("# Руководство\n\nExample text.\n\n- First item\n- Second item",encoding="utf-8")
        with patch.object(gui.tk,"Tk",return_value=root),patch.object(root,"mainloop"),patch.object(gui,"list_profiles",return_value={}),patch.object(gui.filedialog,"askopenfilename",return_value=str(source)):
            gui.main()
            root.update()
            assert not any(isinstance(w,tk.Listbox) for w in descendants(root))
            assert any(isinstance(w,Backdrop) and w.original is not None for w in descendants(root))
            assert "Вставить текст" in buttons(root)
            assert any(isinstance(w,Backdrop) and w.card_photo is not None for w in descendants(root))
            home=next(w for w in descendants(root) if isinstance(w,Backdrop) and not w.banner)
            deadline=time.monotonic()+2
            while home.coords(home.center)!=[home.winfo_width()/2,home.winfo_height()/2] and time.monotonic()<deadline:
                root.update();time.sleep(.05)
            assert home.coords(home.center)==[home.winfo_width()/2,home.winfo_height()/2]
            assert len(home.motion_tracks)==4
            buttons(root)["Открыть"].invoke()
            deadline=time.monotonic()+30
            preview=next(w for w in descendants(root) if isinstance(w,PagePreview))
            while preview.doc is None and time.monotonic()<deadline:
                root.update()
                time.sleep(.05)
            assert preview.doc is not None,"Actual PDF preview did not render"
            assert len(preview.mapping)>0,"PDF selection mapping empty"
            old=preview.scale
            preview._zoom_wheel(SimpleNamespace(delta=120,x=400,y=200))
            assert preview.scale>old
            preview._zoom_wheel(SimpleNamespace(delta=-120,x=400,y=200))
            assert abs(preview.scale-old)<.001
            controls=[w for w in descendants(root) if isinstance(w,ttk.Combobox)]
            role=next(w for w in controls if "Заголовок 2" in w.cget("values"))
            idx=next(i for i,(block,offset) in preview.mapping.items() if block==1)
            l,t,r,b=preview._rect(idx)
            event=SimpleNamespace(x=(l+r)/2-preview.canvas.canvasx(0),y=(t+b)/2-preview.canvas.canvasy(0))
            preview._press(event)
            preview._release(event)
            assert role.get()=="Текст",role.get()
            assert len(preview.selected)>1 and len(preview.handles)==2
            role.set("Заголовок 2")
            role.event_generate("<<ComboboxSelected>>")
            root.update()
            deadline=time.monotonic()+30
            while (str(buttons(root)["Экспорт PDF"].cget("state"))=="disabled" or not preview.selected) and time.monotonic()<deadline:
                root.update()
                time.sleep(.05)
            assert role.get()=="Заголовок 2",role.get()
            assert preview.selected,"Selection lost after reflow"
            idx=next(i for i,(block,offset) in preview.mapping.items() if block==2)
            l,t,r,b=preview._rect(idx)
            event=SimpleNamespace(x=(l+r)/2-preview.canvas.canvasx(0),y=(t+b)/2-preview.canvas.canvasy(0))
            preview._press(event);preview._release(event)
            assert role.get()=="Маркированный список",role.get()
            buttons(root)["Маркированный список"].invoke()
            root.update()
            deadline=time.monotonic()+30
            while str(buttons(root)["Экспорт PDF"].cget("state"))=="disabled" and time.monotonic()<deadline:
                root.update();time.sleep(.05)
            assert role.get()=="Текст",role.get()
            assert preview.selected
            buttons(root)["Сохранить"].invoke()
            assert source.with_name(source.name+".mdtopdf").is_file()
            assert not any(isinstance(w,tk.Toplevel) for w in root.winfo_children())
            buttons(root)["Экспорт PDF"].invoke()
            assert source.with_suffix(".pdf").is_file()
            buttons(root)["Открыть"].invoke()
            root.update()
            assert home.winfo_ismapped() and not preview.winfo_ismapped()
            buttons(root)["Вернуться к документу"].invoke()
            root.update()
            assert preview.winfo_ismapped()
            assert "⚙" not in buttons(root)
            preset=next(w for w in controls if "Настроить пресет…" in w.cget("values"))
            preset.set("Настроить пресет…")
            preset.event_generate("<<ComboboxSelected>>")
            root.update()
            assert any(isinstance(w,ttk.Notebook) and w.winfo_ismapped() for w in descendants(root))
            assert not any(isinstance(w,tk.Toplevel) for w in root.winfo_children())
            buttons(root)["Отмена"].invoke()
            root.update()
            assert len(preview.page_boxes)>0
            root.clipboard_clear()
            root.clipboard_append("# Из буфера\n\nНовый текст.")
            buttons(root)["Вставить текст"].invoke()
            root.update()
            assert not any(isinstance(w,tk.Toplevel) for w in root.winfo_children())
            field=next(w for w in descendants(root) if isinstance(w,tk.Text) and w.winfo_ismapped())
            deadline=time.monotonic()+3
            while field.winfo_height()<=250 and time.monotonic()<deadline:
                root.update();time.sleep(.03)
            assert field.winfo_height()>250
            assert sum(isinstance(w,RoundedPanel) and w.winfo_ismapped() for w in descendants(root))==2
            assert "Новый текст" in field.get("1.0","end")
            field.delete("1.0","end")
            field.insert("1.0","# Из буфера\n\nИсправленный текст.")
            buttons(root)["Открыть в редакторе"].invoke()
            root.update()
            deadline=time.monotonic()+30
            while str(buttons(root)["Экспорт PDF"].cget("state"))=="disabled" and time.monotonic()<deadline:
                root.update()
                time.sleep(.05)
            assert any("Исправленный" in t for t in ["".join(g.char for g in preview.glyphs)]),"Pasted text missing"
            assert not field.winfo_ismapped()
            assert not any(isinstance(w,tk.Toplevel) for w in root.winfo_children())
            with patch.object(gui.filedialog,"asksaveasfilename",return_value=str(Path(d)/"clipboard.pdf")):
                buttons(root)["Экспорт PDF"].invoke()
            assert (Path(d)/"clipboard.pdf").is_file()
            with patch.object(gui.filedialog,"asksaveasfilename",return_value=str(Path(d)/"clipboard.md")):
                buttons(root)["Сохранить"].invoke()
            assert (Path(d)/"clipboard.md").is_file()
            assert (Path(d)/"clipboard.md.mdtopdf").is_file()
            # The confirmation itself uses the actual three-button dialog.
            for label,expected in (("Сохранить","save"),("Не сохранять","discard"),("Отмена","cancel")):
                def answer():
                    prompt=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
                    buttons(prompt)[label].invoke()
                root.after(100,answer)
                assert gui.ask_save_changes(root)==expected
            preview.close()
    print("GUI smoke: one window, real PDF preview and export PASS")
finally:
    root.destroy()
