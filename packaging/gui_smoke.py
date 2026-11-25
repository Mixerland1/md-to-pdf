"""Source GUI smoke test on a virtual display; no user files or saved profiles."""
import tempfile
from pathlib import Path
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk
from md_to_pdf import gui
from md_to_pdf.profile_editor import edit_profile, manage_profiles
from md_to_pdf.profiles import granulex_profile
from md_to_pdf.document_editor import open_editor

def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)

def buttons(widget):
    return {str(w.cget("text")):w for w in descendants(widget) if isinstance(w,ttk.Button)}

root = tk.Tk()
try:
    with patch.object(gui.tk,"Tk",return_value=root), patch.object(root,"mainloop"), patch.object(gui,"list_profiles",return_value={}):
        gui.main()
    root.update_idletasks()
    main_buttons = buttons(root)
    assert {"Создать PDF","Редактировать документ","Настроить стили…"} <= main_buttons.keys()
    assert not any(isinstance(w,ttk.Checkbutton) for w in descendants(root))
    assert not any(isinstance(w,ttk.Entry) and not isinstance(w,ttk.Combobox) for w in descendants(root))
    with patch("md_to_pdf.profile_editor.list_profiles",return_value={}):
        manage_profiles(root,selected="Granulex",builtins={"Granulex":"granulex"},on_change=lambda *_:None)
    library = next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
    assert {"Настроить…","Создать стиль…","Импорт…","Готово"} <= buttons(library).keys()
    library.destroy()
    errors = []
    def inspect_profile():
        dialog = next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
        try:
            tabs = next(w for w in descendants(dialog) if isinstance(w,ttk.Notebook))
            assert [tabs.tab(t,"text") for t in tabs.tabs()] == ["Шрифты","Цвета","Страница","Логотип и бренд"]
            combos = [w for w in descendants(dialog) if isinstance(w,ttk.Combobox)]
            assert any("Montserrat" in w.cget("values") for w in combos)
            assert any("Roboto Mono" in w.cget("values") for w in combos)
        except Exception as exc:
            errors.append(exc)
        finally:
            dialog.destroy()
    root.after(50,inspect_profile)
    edit_profile(root,initial=granulex_profile(),on_save=lambda *_:None)
    assert not errors, errors
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder)/"example.md"
        source.write_text("# Title\n\nExample text.",encoding="utf-8")
        open_editor(root,source,template="granulex")
        dialog = next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
        assert {"Полужирный","Курсив","Акцент","Создать PDF","Шапка…"} <= buttons(dialog).keys()
        text = next(w for w in descendants(dialog) if isinstance(w,tk.Text))
        start = text.search("Example", "1.0", stopindex="end")
        assert start
        text.tag_add("sel",start,start+"+7c")
        buttons(dialog)["Акцент"].invoke()
        assert "Example" in text.get("1.0","end")
        dialog.destroy()
    print("GUI smoke: main window, style library, font tabs, document selection editor PASS")
finally:
    root.destroy()
