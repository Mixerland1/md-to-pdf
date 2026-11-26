"""Local decorative artwork and a compact, native-control desktop theme."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageOps, ImageTk, ImageDraw, ImageFilter
import sys
from functools import lru_cache

ASSETS = Path(__file__).with_name("assets")
INK = "#203653"
SURFACE = "#edf2fa"
PANEL = "#ffffff"
BORDER = "#bac9df"
BLUE = "#355d91"

@lru_cache(maxsize=4)
def vector_image(asset, width, height, transparent=False):
    """Render vector artwork to exact device-pixel dimensions, losslessly."""
    from weasyprint import HTML
    import pypdfium2 as pdfium
    svg=(ASSETS/asset).read_text(encoding="utf-8")
    # SVG's viewport scales its viewBox to the requested dimensions.
    import re
    svg=re.sub(r'<svg\b[^>]*>',lambda m: re.sub(r'\bwidth="[^"]*"','width="'+str(width)+'"',re.sub(r'\bheight="[^"]*"','height="'+str(height)+'"',m.group(0))),svg,count=1)
    markup=f'<html><head><style>@page {{size:{width}px {height}px; margin:0}} html,body {{margin:0;padding:0;width:{width}px;height:{height}px;overflow:hidden}} svg {{display:block}}</style></head><body>{svg}</body></html>'
    pdf=HTML(string=markup).write_pdf()
    with pdfium.PdfDocument(pdf) as document:
        page=document[0]
        try:
            bitmap=page.render(scale=4/3,fill_color=(0,0,0,0) if transparent else (255,255,255,255))
            try:
                return bitmap.to_pil().convert("RGBA" if transparent else "RGB").resize((width,height),Image.Resampling.LANCZOS)
            finally:
                bitmap.close()
        finally:
            page.close()

def round_window(window):
    """Keep native window controls; request rounded corners on Windows 11."""
    if sys.platform!="win32":
        return
    def apply(event=None):
        if event is not None and event.widget is not window:
            return
        try:
            import ctypes
            from ctypes import wintypes
            get_ancestor=ctypes.windll.user32.GetAncestor
            get_ancestor.argtypes=(wintypes.HWND,wintypes.UINT)
            get_ancestor.restype=wintypes.HWND
            hwnd=get_ancestor(window.winfo_id(),2)
            if hwnd:
                preference=ctypes.c_int(2)  # DWMWCP_ROUND
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    wintypes.HWND(hwnd),33,ctypes.byref(preference),ctypes.sizeof(preference))
        except (AttributeError,OSError,tk.TclError):
            pass
    window.bind("<Map>",apply,add="+")
    window.after_idle(apply)


@lru_cache(maxsize=8)
def rounded_art(width,height,radius=18,shadow=True,border=BORDER):
    """Antialiased rounded card with transparent corners, soft shadow."""
    width,height=max(1,int(width)),max(1,int(height))
    scale=2
    inset=12 if shadow else 1
    w,h=width*scale,height*scale
    pad=inset*scale
    radius=max(1,min(radius*scale,(min(w,h)-2*pad)//2))
    box=(pad,pad,max(pad,w-pad-1),max(pad,h-pad-1))
    result=Image.new("RGBA",(w,h),(0,0,0,0))
    if shadow and min(width,height)>30:
        layer=Image.new("RGBA",(w,h),(0,0,0,0))
        ImageDraw.Draw(layer).rounded_rectangle((box[0],box[1]+4*scale,box[2],box[3]+4*scale),
            radius=radius,fill=(32,54,83,40))
        result.alpha_composite(layer.filter(ImageFilter.GaussianBlur(4*scale)))
    ImageDraw.Draw(result).rounded_rectangle(box,radius=radius,fill=PANEL,outline=border,width=scale)
    return result.resize((width,height),Image.Resampling.LANCZOS)


class RoundedPanel(tk.Canvas):
    """Real widgets inside an inset surface; the visible perimeter is rounded."""
    def __init__(self,parent,*,radius=18,shadow=True,padding=24,background=SURFACE,**kwargs):
        super().__init__(parent,background=background,highlightthickness=0,borderwidth=0,**kwargs)
        self.radius=radius
        self.shadow=shadow
        self.inset=max(radius+2,padding)+(12 if shadow else 1)
        self.photo=None
        self.pending=None
        self.art=self.create_image(0,0,anchor="nw")
        self.content=ttk.Frame(self,style="Welcome.TFrame")
        self.child=self.create_window(self.inset,self.inset,window=self.content,anchor="nw")
        self.bind("<Configure>",self._schedule)
        self.bind("<Destroy>",self._cancel,add="+")
    def _cancel(self,event=None):
        if self.pending is not None:
            self.after_cancel(self.pending)
            self.pending=None
    def _schedule(self,event=None):
        self._cancel()
        self.pending=self.after(25,self._draw)
    def _draw(self):
        self.pending=None
        w,h=self.winfo_width(),self.winfo_height()
        if w<=2*self.inset or h<=2*self.inset:
            return
        self.photo=ImageTk.PhotoImage(rounded_art(w,h,self.radius,self.shadow),master=self)
        self.itemconfigure(self.art,image=self.photo)
        self.itemconfigure(self.child,width=w-2*self.inset,height=h-2*self.inset)
        self.tag_lower(self.art)


def configure_theme(root):
    root.configure(background=SURFACE)
    round_window(root)
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
        self.asset=asset
        self.original=None
        self.photo=None
        self.pending=None
        self.center=None
        self.card_item=None
        self.card_photo=None
        try:
            if asset.endswith(".svg"):
                self.original=vector_image(asset,1920 if not banner else 1920,1080 if not banner else 96)
            else:
                with Image.open(ASSETS / asset) as source:
                    self.original=source.convert("RGB")
        except (OSError, ValueError, RuntimeError):
            pass
        self.image_item=self.create_image(0,0,anchor="nw")
        self.bind("<Configure>",self._schedule)
    def center_widget(self, widget):
        self.card_item=self.create_image(0,0,anchor="center")
        self.center=self.create_window(0,0,window=widget,anchor="center")
        self.center_content=widget
        widget.bind("<Configure>",self._schedule,add="+")
        self._draw()
    def _schedule(self,event=None):
        if self.pending is not None:
            self.after_cancel(self.pending)
        self.pending=self.after(35,self._draw)
    def _draw(self):
        self.pending=None
        w,h=max(1,self.winfo_width()),max(1,self.winfo_height())
        if self.original is not None:
            original=self.original
            if self.asset.endswith(".svg") and (w>original.width or h>original.height):
                try:
                    factor=max(w/original.width,h/original.height)
                    original=vector_image(self.asset,round(original.width*factor),round(original.height*factor))
                except Exception:
                    pass
            if self.banner:
                im=original.resize((w,h),Image.Resampling.LANCZOS)
            else:
                im=ImageOps.fit(original,(w,h),Image.Resampling.LANCZOS)
            self.photo=ImageTk.PhotoImage(im,master=self)
            self.itemconfigure(self.image_item,image=self.photo)
        if self.center is not None:
            x,y=w*.45,h*.48
            self.coords(self.center,x,y)
            cw=max(self.center_content.winfo_reqwidth(),self.center_content.winfo_width())+76
            ch=max(self.center_content.winfo_reqheight(),self.center_content.winfo_height())+76
            self.card_photo=ImageTk.PhotoImage(rounded_art(cw,ch,18,True),master=self)
            self.itemconfigure(self.card_item,image=self.card_photo)
            self.coords(self.card_item,x,y)
            self.tag_lower(self.card_item,self.center)
        self.tag_lower(self.image_item)


def toolbar_icon(master,name,size=22):
    """Antialiased Office-style pictograms; no third-party icon artwork."""
    k=4
    im=Image.new("RGBA",(24*k,24*k),(0,0,0,0))
    d=ImageDraw.Draw(im)
    def line(points,fill=INK,width=1.5):
        d.line([(round(x*k),round(y*k)) for x,y in points],fill=fill,width=round(width*k),joint="curve")
    def poly(points,fill,outline=None):
        d.polygon([(round(x*k),round(y*k)) for x,y in points],fill=fill)
        if outline:
            line(points+[points[0]],outline,1)
    if name=="format":
        im=vector_image("format-painter.svg",96,96,True)
        bbox=im.getbbox()
        if bbox:
            im=im.crop(bbox)
        im=ImageOps.contain(im,(size-1,size-1),Image.Resampling.LANCZOS)
        canvas=Image.new("RGBA",(size,size),(0,0,0,0))
        canvas.alpha_composite(im,((size-im.width)//2,(size-im.height)//2))
        return ImageTk.PhotoImage(canvas,master=master)
    elif name in ("bullet","numbered"):
        for i,y in enumerate((5,12,19),1):
            line([(9,y),(21,y)],INK,1.6)
            if name=="bullet":
                d.ellipse((3*k,(y-1.4)*k,5.8*k,(y+1.4)*k),fill=BLUE)
            else:
                # Tiny numerals rendered as strokes, avoiding platform fonts.
                if i==1: line([(3,y-1),(4.5,y-2),(4.5,y+2)],BLUE,1)
                elif i==2: line([(3,y-1),(4,y-2),(5.5,y-1),(3,y+2),(5.5,y+2)],BLUE,1)
                else: line([(3,y-2),(5.5,y-2),(4,y),(5.5,y+1),(4,y+2),(3,y+2)],BLUE,1)
    elif name=="table":
        d.rounded_rectangle((2*k,3*k,21*k,21*k),radius=2*k,fill="#ffffff",outline=INK,width=k)
        d.rectangle((3*k,4*k,20*k,8*k),fill="#a7bfdc")
        for x in (8.5,15):
            line([(x,3),(x,21)],INK,1)
        for y in (9,15):
            line([(2,y),(21,y)],INK,1)
    return ImageTk.PhotoImage(im.resize((size,size),Image.Resampling.LANCZOS),master=master)
