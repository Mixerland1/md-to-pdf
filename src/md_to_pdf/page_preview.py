"""Real PDF pages with conservative, layout-anchor-based text selection."""
from dataclasses import dataclass
import unicodedata
import ctypes
import re
import tkinter as tk
from tkinter import ttk
import pypdfium2 as pdfium
import pypdfium2.raw as raw
from PIL import ImageTk

def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKC",text) if not c.isspace() and c != "\u00ad")

@dataclass
class Glyph:
    page: int
    box: tuple
    char: str
    font: str = ""
    size: float = 0
    color: str = ""

def glyphs_for(document):
    glyphs = []
    for i in range(len(document)):
        page = document[i]
        text = page.get_textpage()
        try:
            height = page.get_height()
            for index in range(text.count_chars()):
                code = raw.FPDFText_GetUnicode(text.raw,index)
                if not code or code > 0x10ffff or 0xd800 <= code <= 0xdfff:
                    continue
                value = normalized(chr(code))
                if not value:
                    continue
                try:
                    l,b,r,t = text.get_charbox(index)
                except Exception:
                    continue
                if r<=l or t<=b:
                    continue
                size=round(raw.FPDFText_GetFontSize(text.raw,index),2)
                family=""
                try:
                    flags=ctypes.c_int()
                    n=raw.FPDFText_GetFontInfo(text.raw,index,None,0,ctypes.byref(flags))
                    if 0<n<512:
                        buffer=ctypes.create_string_buffer(n)
                        raw.FPDFText_GetFontInfo(text.raw,index,buffer,n,ctypes.byref(flags))
                        family=buffer.value.decode("utf-8",errors="replace")
                        family=re.sub(r"^[A-Z]{6}\+","",family)
                        family=re.sub(r"[-, ](?:BoldItalic|BoldOblique|Regular|Bold|Italic|Oblique|Roman|Medium|SemiBold)$","",family,flags=re.I)
                except (AttributeError,TypeError,ValueError):
                    pass
                color=""
                try:
                    rr,gg,bb,aa=(ctypes.c_uint() for _ in range(4))
                    if raw.FPDFText_GetFillColor(text.raw,index,ctypes.byref(rr),ctypes.byref(gg),ctypes.byref(bb),ctypes.byref(aa)):
                        color=f"#{rr.value:02x}{gg.value:02x}{bb.value:02x}"
                except (AttributeError,TypeError,ValueError):
                    pass
                glyphs.extend(Glyph(i,(l,height-t,r,height-b),c,family,size,color) for c in value)
        finally:
            text.close()
            page.close()
    return glyphs

def map_glyphs(document, anchors, texts, locations):
    glyphs = glyphs_for(document)
    flat = "".join(g.char for g in glyphs)
    mapped = {}
    for block,(anchor,text) in enumerate(zip(anchors,texts)):
        expected = []
        for i,char in enumerate(text):
            expected.extend((c,i) for c in normalized(char))
        needle = "".join(c for c,_ in expected)
        if not needle or anchor not in locations:
            continue
        candidates = []
        start = flat.find(needle)
        while start >= 0:
            g = glyphs[start]
            x,y,r,b = g.box
            if any(g.page == p and x >= l-4 and x <= rr+4 and y >= t-5 and y <= bb+5
                   for p,(l,t,rr,bb) in locations[anchor]):
                candidates.append(start)
            start = flat.find(needle,start+1)
        # Table cell text can be interleaved with neighboring cells in PDF
        # extraction order. Fall back to exact text within the anchor box.
        if len(candidates)==1:
            indices=list(range(candidates[0],candidates[0]+len(needle)))
        else:
            inside=[]
            for j,g in enumerate(glyphs):
                x,y,r,b=g.box
                if any(g.page==pg and l-1<=(x+r)/2<=rr+1 and t-1<=(y+b)/2<=bb+1
                       for pg,(l,t,rr,bb) in locations[anchor]):
                    inside.append(j)
            if "".join(glyphs[j].char for j in inside)!=needle:
                continue
            indices=inside
        if any(j in mapped for j in indices):
            continue
        for j,(_,offset) in zip(indices,expected):
            mapped[j] = (block,offset)
    return glyphs,mapped

class PagePreview(ttk.Frame):
    def __init__(self,parent,on_select,on_context):
        super().__init__(parent)
        self.columnconfigure(0,weight=1)
        self.rowconfigure(0,weight=1)
        self.canvas=tk.Canvas(self,bg="#e7edf6",highlightthickness=0)
        self.canvas.grid(sticky="nsew")
        self.scroll=ttk.Scrollbar(self,orient="vertical",command=self._scroll)
        self.scroll.grid(row=0,column=1,sticky="ns")
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.on_select=on_select
        self.on_context=on_context
        self.doc=None
        self.page_boxes=[]
        self.page_images={}
        self.glyphs=[]
        self.mapping={}
        self.selected=[]
        self.start=None
        self.press_xy=None
        self.handle_drag=False
        self.handles=[]
        self.scale=1.15
        self.canvas.bind("<Configure>",self._resize)
        self.canvas.bind("<MouseWheel>",self._wheel)
        self.canvas.bind("<Button-4>",lambda e:self._scroll("scroll",-3,"units"))
        self.canvas.bind("<Button-5>",lambda e:self._scroll("scroll",3,"units"))
        self.canvas.bind("<ButtonPress-1>",self._press)
        self.canvas.bind("<B1-Motion>",self._drag)
        self.canvas.bind("<ButtonRelease-1>",self._release)
        self.canvas.bind("<Button-3>",lambda e:self.on_context(e))
        self.canvas.bind("<Control-Button-1>",lambda e:self.on_context(e))

    def close(self):
        if self.doc is not None:
            self.doc.close()
            self.doc=None

    def set_document(self,result):
        data,anchors,texts,locations=result
        fraction=self.canvas.yview()[0]
        new=pdfium.PdfDocument(data)
        try:
            glyphs,mapping=map_glyphs(new,anchors,texts,locations)
        except Exception:
            new.close()
            raise
        self.close()
        self.doc=new
        self.glyphs,self.mapping=glyphs,mapping
        self.selected=[]
        self.start=None
        self._layout()
        self.canvas.yview_moveto(fraction)
        self._visible()

    def _resize(self,event):
        if self.doc:
            old=self.canvas.yview()[0]
            self._layout()
            self.canvas.yview_moveto(old)
            self._visible()

    def _layout(self):
        self.canvas.delete("all")
        self.page_images={}
        self.page_boxes=[]
        if self.doc is None:
            return
        width=max(200,self.canvas.winfo_width())
        page=self.doc[0]
        try:
            self.scale=max(.2,min(1.6,(width-40)/page.get_width()))
        finally:
            page.close()
        y=20
        for i in range(len(self.doc)):
            page=self.doc[i]
            try:
                w,h=page.get_size()
            finally:
                page.close()
            w,h=w*self.scale,h*self.scale
            x=max(12,(width-w)/2)
            self.page_boxes.append((x,y,w,h))
            self.canvas.create_rectangle(x,y,x+w,y+h,fill="white",outline="#c5d0df")
            y+=h+20
        self.canvas.configure(scrollregion=(0,0,width,y))
        self._draw_selection()

    def _visible(self):
        if self.doc is None:
            return
        top=self.canvas.canvasy(0)
        bottom=top+self.canvas.winfo_height()
        visible={i for i,(_,y,_,h) in enumerate(self.page_boxes) if y+h>=top-100 and y<=bottom+100}
        for i in list(self.page_images):
            if i not in visible:
                _,item=self.page_images.pop(i)
                self.canvas.delete(item)
        for i in sorted(visible):
            if i in self.page_images:
                continue
            page=self.doc[i]
            try:
                bitmap=page.render(scale=self.scale)
                try:
                    image=ImageTk.PhotoImage(bitmap.to_pil().copy(),master=self.canvas)
                finally:
                    bitmap.close()
            finally:
                page.close()
            x,y,_,_=self.page_boxes[i]
            item=self.canvas.create_image(x,y,image=image,anchor="nw")
            self.page_images[i]=(image,item)
        self.canvas.tag_raise("selection")

    def _scroll(self,*args):
        self.canvas.yview(*args)
        self._visible()

    def _wheel(self,event):
        delta=event.delta
        if delta:
            self._scroll("scroll",-max(1,abs(delta)//120)*(1 if delta>0 else -1)*3,"units")

    def _hit(self,event):
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        page=next((i for i,(l,t,w,h) in enumerate(self.page_boxes) if l<=x<=l+w and t<=y<=t+h),None)
        if page is None:
            return None
        l,t,_,_=self.page_boxes[page]
        x,y=(x-l)/self.scale,(y-t)/self.scale
        candidates=[]
        for i,g in enumerate(self.glyphs):
            if g.page!=page:
                continue
            a,b,c,d=g.box
            dx=max(a-x,0,x-c)
            dy=max(b-y,0,y-d)
            if dx<=5 and dy<=3:
                candidates.append((dx+dy*3,i))
        return min(candidates)[1] if candidates else None

    def restore_selection(self,ranges):
        self.selected=[i for i,(block,offset) in self.mapping.items()
                       if any(block==b and a<=offset<z for b,a,z in ranges)]
        self.selected.sort()
        self._draw_selection()
        self._notify()

    def selection_format(self):
        fonts={self.glyphs[i].font for i in self.selected if self.glyphs[i].font}
        sizes={self.glyphs[i].size for i in self.selected if self.glyphs[i].size}
        return (next(iter(fonts)) if len(fonts)==1 else "Разные" if fonts else "",
                f"{next(iter(sizes)):g}" if len(sizes)==1 else "Разные" if sizes else "")

    def selection_color(self):
        colors={self.glyphs[i].color for i in self.selected if self.glyphs[i].color}
        return next(iter(colors)) if len(colors)==1 else None

    def _notify(self):
        if not self.selected:
            self.on_select([])
            return
        unmapped=[i for i in self.selected if i not in self.mapping]
        # A PDF list marker is generated by the renderer, not source text.
        # Allow it only as a separate run to the left of a mapped item on
        # the same line. Never ignore arbitrary unmapped text.
        for i in unmapped:
            g=self.glyphs[i]
            marker=(g.char in "•◦▪‣⁃–-" or g.char.isdigit() or g.char in ".)")
            following=next((j for j in range(i+1,min(len(self.glyphs),i+12)) if j in self.mapping),None)
            if not marker or following is None:
                self.on_select(None)
                return
            nxt=self.glyphs[following]
            if nxt.page!=g.page or abs(nxt.box[1]-g.box[1])>5 or nxt.box[0]<g.box[2] or nxt.box[0]-g.box[2]>45 or self.mapping[following][1]>2:
                self.on_select(None)
                return
        groups={}
        for i in self.selected:
            if i not in self.mapping:
                continue
            block,offset=self.mapping[i]
            groups.setdefault(block,[]).append(offset)
        self.on_select([(i,min(v),max(v)+1) for i,v in sorted(groups.items())])

    def _press(self,event):
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        self.press_xy=(event.x,event.y)
        self.handle_drag=False
        for side,hx,hy in self.handles:
            if (x-hx)**2+(y-hy)**2<=15**2 and self.selected:
                self.start=self.selected[-1] if side=="left" else self.selected[0]
                self.handle_drag=True
                return
        self.canvas.focus_set()
        self.start=self._hit(event)
        self.selected=[]
        self.on_select([])
        self._draw_selection()

    def _drag(self,event):
        end=self._hit(event)
        if self.start is None or end is None:
            return
        if not self.handle_drag and self.press_xy and max(abs(event.x-self.press_xy[0]),abs(event.y-self.press_xy[1]))<4:
            return
        a,b=sorted((self.start,end))
        self.selected=list(range(a,b+1))
        self._draw_selection()

    def _release(self,event):
        self._drag(event)
        if not self.handle_drag and not self.selected and self.start in self.mapping:
            block,_=self.mapping[self.start]
            self.selected=sorted(i for i,(b,_) in self.mapping.items() if b==block)
            self._draw_selection()
        self._notify()

    def _rect(self,index):
        g=self.glyphs[index]
        x,y,_,_=self.page_boxes[g.page]
        l,t,r,b=g.box
        return (x+l*self.scale,y+t*self.scale,x+r*self.scale,y+b*self.scale)

    def _draw_selection(self):
        self.canvas.delete("selection")
        self.handles=[]
        if not self.page_boxes or not self.selected:
            return
        # Merge adjacent glyph rectangles on each line, including whitespace.
        lines=[]
        for i in self.selected:
            l,t,r,b=self._rect(i)
            page=self.glyphs[i].page
            if lines and lines[-1][0]==page and abs((t+b)/2-(lines[-1][2]+lines[-1][4])/2)<max(4,(b-t)*.5) and l<=lines[-1][3]+12:
                old=lines[-1]
                lines[-1]=(page,min(l,old[1]),min(t,old[2]),max(r,old[3]),max(b,old[4]))
            else:
                lines.append((page,l,t,r,b))
        for _,l,t,r,b in lines:
            self.canvas.create_rectangle(l-1,t-2,r+1,b+2,fill="#408cf5",stipple="gray50",
                outline="#2673d9",width=1,tags=("selection",))
        first=self._rect(self.selected[0]);last=self._rect(self.selected[-1])
        for side,x,y,top in (("left",first[0],first[3]+9,first[1]),("right",last[2],last[3]+9,last[1])):
            self.canvas.create_line(x,top,x,y,fill="#1565d8",width=2,tags=("selection",))
            self.canvas.create_oval(x-6,y-6,x+6,y+6,fill="#1565d8",outline="white",width=1,tags=("selection",))
            self.handles.append((side,x,y))
        self.canvas.tag_raise("selection")
