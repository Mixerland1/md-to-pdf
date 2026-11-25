"""Local decorative artwork and a compact, native-control desktop theme."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageOps, ImageTk

ASSETS = Path(__file__).with_name("assets")
INK = "#203653"
SURFACE = "#edf2fa"
PANEL = "#f7f9fd"
BORDER = "#bac9df"
BLUE = "#355d91"

def configure_theme(root):
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure("Toolbar.TFrame", background=SURFACE)
    style.configure("Welcome.TFrame", background=PANEL)
    style.configure("Welcome.TLabel", background=PANEL, foreground=INK)
    style.configure("Toolbar.TButton", padding=(9,5), foreground=INK,
                    background=PANEL, bordercolor=BORDER, lightcolor=PANEL,
                    darkcolor=PANEL, focusthickness=1, focuscolor=BLUE)
    style.map("Toolbar.TButton", background=[("pressed","#d1e0f2"),("active","#e0eafa")],
              foreground=[("disabled","#8695a8")])
    style.configure("Accent.TButton", padding=(11,6), background=BLUE,
                    foreground="white", bordercolor=BLUE, lightcolor=BLUE,
                    darkcolor=BLUE, focuscolor="#d9e5fb")
    style.map("Accent.TButton", background=[("disabled","#c4cedd"),("pressed","#244571"),("active","#426ca4")],
              foreground=[("disabled","#67778d")])
    style.configure("Toolbar.TCombobox", padding=4, foreground=INK,
                    fieldbackground=PANEL, background=SURFACE,
                    bordercolor=BORDER, arrowcolor=INK)
    style.map("Toolbar.TCombobox", fieldbackground=[("readonly",PANEL),("disabled","#e3e8ef")],
              foreground=[("disabled","#8695a8"),("readonly",INK)])
    return style

class Backdrop(tk.Canvas):
    """Scale approved artwork locally; interactive widgets remain real controls."""
    def __init__(self, parent, asset, *, banner=False, **kwargs):
        super().__init__(parent, background=SURFACE, highlightthickness=0,
                         borderwidth=0, **kwargs)
        self.banner=banner
        self.original=None
        self.photo=None
        self.pending=None
        self.center=None
        try:
            with Image.open(ASSETS / asset) as source:
                self.original=source.convert("RGB")
        except (OSError, ValueError):
            pass
        self.image_item=self.create_image(0,0,anchor="nw")
        self.bind("<Configure>",self._schedule)
    def center_widget(self, widget):
        self.center=self.create_window(0,0,window=widget,anchor="center")
        self._draw()
    def _schedule(self,event=None):
        if self.pending is not None:
            self.after_cancel(self.pending)
        self.pending=self.after(35,self._draw)
    def _draw(self):
        self.pending=None
        w,h=max(1,self.winfo_width()),max(1,self.winfo_height())
        if self.original is not None:
            if self.banner:
                im=self.original.resize((w,h),Image.Resampling.LANCZOS)
            else:
                im=ImageOps.fit(self.original,(w,h),Image.Resampling.LANCZOS)
            self.photo=ImageTk.PhotoImage(im,master=self)
            self.itemconfigure(self.image_item,image=self.photo)
        if self.center is not None:
            self.coords(self.center,w*.45,h*.48)
        self.tag_lower(self.image_item)
