"""Local decorative artwork and a compact, native-control desktop theme."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageOps, ImageTk, ImageDraw, ImageFilter
import sys
import time
import math
import re
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
        self.motion_job=None
        self.motion_tracks=[]
        self.motion_items=[]
        self.motion_origin=time.monotonic()
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
        self.bind("<Map>",self._start_motion,add="+")
        self.bind("<Unmap>",self._stop_motion,add="+")
        self.bind("<Destroy>",self._stop_motion,add="+")
        if not banner and asset=="welcome.svg":
            self.motion_tracks=welcome_tracks()
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
            x,y=w/2,h/2
            self.coords(self.center,x,y)
            cw=max(self.center_content.winfo_reqwidth(),self.center_content.winfo_width())+76
            ch=max(self.center_content.winfo_reqheight(),self.center_content.winfo_height())+76
            self.card_photo=ImageTk.PhotoImage(rounded_art(cw,ch,18,True),master=self)
            self.itemconfigure(self.card_item,image=self.card_photo)
            self.coords(self.card_item,x,y)
            self.tag_lower(self.card_item,self.center)
        self.tag_lower(self.image_item)
        self._start_motion()

    def _start_motion(self,event=None):
        if self.motion_tracks and self.motion_job is None and self.winfo_ismapped():
            self.motion_job=self.after(40,self._animate)
    def _stop_motion(self,event=None):
        if self.motion_job is not None:
            self.after_cancel(self.motion_job)
            self.motion_job=None
    def _animate(self):
        self.motion_job=None
        if not self.winfo_ismapped():
            return
        w,h=self.winfo_width(),self.winfo_height()
        scale=max(w/640,h/360)
        dx=(w-640*scale)/2
        dy=(h-360*scale)/2
        elapsed=time.monotonic()-self.motion_origin
        if not self.motion_items:
            for _ in self.motion_tracks:
                group=[self.create_line(0,0,0,0,fill=c,width=width,capstyle="round",joinstyle="round")
                       for c,width in (("#c2d5ed",4),("#dcecff",2.5),("#f7fbff",1.5))]
                self.motion_items.append(group)
                for item in group:
                    if self.card_item is not None:
                        self.tag_lower(item,self.card_item)
        for (points,duration,offset,red),group in zip(self.motion_tracks,self.motion_items):
            end=int(((elapsed+offset)%duration)/duration*(len(points)+20))
            for j,item in enumerate(group):
                begin=max(0,end-(13-j*3))
                stop=min(len(points),end)
                if stop-begin<2:
                    self.itemconfigure(item,state="hidden")
                    continue
                coords=[v for x,y in points[begin:stop] for v in (x*scale+dx,y*scale+dy)]
                self.coords(item,*coords)
                self.itemconfigure(item,state="normal",fill=("#e7a9b7","#f2c1cb","#fff2e8")[j] if red else ("#c2d5ed","#dcecff","#ffffff")[j])
        self.motion_job=self.after(40,self._animate)


def welcome_tracks():
    """Use the actual cubic tracks in the artwork, not unrelated overlay lines."""
    svg=(ASSETS/"welcome.svg").read_text(encoding="utf-8")
    matches=re.findall(r'<path d="M(-?[\d.]+) ([\d.-]+) C ([\d.-]+) ([\d.-]+), ([\d.-]+) ([\d.-]+), ([\d.-]+) ([\d.-]+)" fill="none"',svg)
    tracks=[]
    for index,duration,offset,red in ((3,13,1,False),(9,17,7,False),(17,20,12,False),(23,18,9,True)):
        if index>=len(matches):
            continue
        x0,y0,x1,y1,x2,y2,x3,y3=map(float,matches[index])
        points=[]
        for i in range(241):
            t=i/240;u=1-t
            points.append((u**3*x0+3*u*u*t*x1+3*u*t*t*x2+t**3*x3,
                           u**3*y0+3*u*u*t*y1+3*u*t*t*y2+t**3*y3))
        tracks.append((points,duration,offset,red))
    return tracks


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
    elif name=="open":
        poly([(2,6),(9,6),(11,8),(21,8),(21,19),(2,19)],"#d3a75d",INK)
        poly([(2,19),(5,10),(23,10),(20,19)],"#f3ce80",INK)
    elif name=="save":
        poly([(3,3),(18,3),(21,6),(21,21),(3,21)],"#779ac4",INK)
        poly([(7,3),(16,3),(16,10),(7,10)],"#ffffff",INK)
        poly([(6,13),(18,13),(18,21),(6,21)],"#eaf1fa",INK)
    elif name=="paste":
        poly([(5,4),(19,4),(19,22),(5,22)],"#ffffff",INK)
        poly([(8,2),(16,2),(17,7),(7,7)],"#a7bfdc",INK)
        for y in (11,15,18):
            line([(8,y),(16,y)],INK,1.3)
    elif name=="pdf":
        poly([(5,2),(15,2),(20,7),(20,22),(5,22)],"#ffffff",INK)
        line([(15,2),(15,7),(20,7)],INK,1)
        poly([(3,12),(22,12),(22,18),(3,18)],"#b73b47")
        # PDF pictogram, with recognizable tiny letter strokes.
        for x,points in ((5,[(0,4),(0,0),(3,0),(3,2),(0,2)]),(11,[(0,4),(0,0),(2,0),(3,1),(3,3),(2,4),(0,4)]),(17,[(0,4),(0,0),(3,0),(0,0),(0,2),(2,2)])):
            line([(x+a,13+b) for a,b in points],"#ffffff",.8)
    elif name in ("undo","redo","back"):
        pts=[(5,11),(10,6),(10,10),(16,10),(20,13),(20,17),(15,20)]
        if name=="redo":pts=[(24-x,y) for x,y in pts]
        if name=="back":pts=[(13,5),(6,12),(13,19),(6,12),(21,12)]
        line(pts,INK,2)
    elif name=="clear":
        line([(5,6),(19,6),(17,21),(7,21),(5,6)],INK,1.5)
        line([(3,6),(21,6),(15,6),(15,3),(9,3),(9,6)],INK,1.5)
    elif name=="update":
        line([(12,3),(12,16),(6,10),(12,16),(18,10)],INK,2)
        line([(4,17),(4,21),(20,21),(20,17)],INK,1.6)
    elif name=="table":
        d.rounded_rectangle((2*k,3*k,21*k,21*k),radius=2*k,fill="#ffffff",outline=INK,width=k)
        d.rectangle((3*k,4*k,20*k,8*k),fill="#a7bfdc")
        for x in (8.5,15):
            line([(x,3),(x,21)],INK,1)
        for y in (9,15):
            line([(2,y),(21,y)],INK,1)
    return ImageTk.PhotoImage(im.resize((size,size),Image.Resampling.LANCZOS),master=master)
