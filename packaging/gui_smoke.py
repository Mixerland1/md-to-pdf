"""Single-window GUI acceptance smoke on virtual display."""
import tempfile,time
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk
from md_to_pdf import gui
from md_to_pdf.page_preview import PagePreview

def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)

def buttons(widget):
    return {str(w.cget("text")):w for w in descendants(widget) if isinstance(w,ttk.Button)}

root=tk.Tk()
try:
    with tempfile.TemporaryDirectory() as d:
        source=Path(d)/"guide.md"
        source.write_text("# Руководство\n\nExample text.",encoding="utf-8")
        with patch.object(gui.tk,"Tk",return_value=root),patch.object(root,"mainloop"),patch.object(gui,"list_profiles",return_value={}),patch.object(gui.filedialog,"askopenfilename",return_value=str(source)):
            gui.main()
            root.update()
            assert not any(isinstance(w,tk.Listbox) for w in descendants(root))
            buttons(root)["Открыть"].invoke()
            deadline=time.monotonic()+30
            preview=next(w for w in descendants(root) if isinstance(w,PagePreview))
            while preview.doc is None and time.monotonic()<deadline:
                root.update()
                time.sleep(.05)
            assert preview.doc is not None,"Actual PDF preview did not render"
            assert len(preview.mapping)>0,"PDF selection mapping empty"
            assert not any(isinstance(w,tk.Toplevel) for w in root.winfo_children())
            buttons(root)["Экспорт PDF"].invoke()
            assert source.with_suffix(".pdf").is_file()
            assert len(preview.page_boxes)>0
            preview.close()
    print("GUI smoke: one window, real PDF preview and export PASS")
finally:
    root.destroy()
