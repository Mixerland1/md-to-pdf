"""Selection-based semantic style operations on a rendered HTML document."""
from __future__ import annotations

from dataclasses import dataclass
from lxml import html, etree
from .profiles import FONT
import math
import json
import re
from copy import deepcopy

INLINE_STYLES = {"bold": ("strong", ""), "italic": ("em", ""),
                 "code": ("code", ""), "accent": ("span", "brand-accent")}
BLOCK_STYLES = {"normal": ("p", ""), "h1": ("h1", ""), "h2": ("h2", ""),
                "h3": ("h3", ""), "quote": ("blockquote", ""),
                "note": ("p", "editor-note"), "warning": ("p", "editor-warning"),
                "code-block": ("pre", ""), "bullet": ("li", ""), "numbered": ("li", ""),
                "h4": ("h4", ""), "h5": ("h5", ""), "h6": ("h6", "")}
METADATA_STYLES = {"meta-version": (1,"Версия"), "meta-updated": (2,"Последнее обновление:")}
BLOCK_STYLES.update({"meta-version":("p","editor-meta-version"),"meta-updated":("p","editor-meta-updated")})
TABLE_STYLES = {"table-cell":"td","table-heading":"th"}
BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "blockquote",
              "li", "td", "th", "div"}
EDITOR_CLASSES = {"editor-note", "editor-warning", "editor-meta-version", "editor-meta-updated"}
EDITOR_CSS = """
.editor-note { border-left: 3px solid #9ca3af; background: #f3f4f6; padding: .7em; }
.editor-warning { border-left: 3px solid #b50e25; background: #fff1f2; padding: .7em; }
.editor-meta-version, .editor-meta-updated { text-align:right; font-size:8pt; line-height:12pt; color:#9ca3af; margin:0 0 4pt; }
.editor-meta-version { font-weight:700; }
.editor-meta-updated { font-weight:400; }
table.editor-grid td, table.editor-grid th { border:1px solid #aab4c0; }
table.editor-no-grid td, table.editor-no-grid th { border:0; }
:where(.brand-accent) { color: #b50e25; }
"""

@dataclass(frozen=True)
class Block:
    text: str
    tag: str
    role: str
    locked: bool


def _is_header(node):
    return any("doc-header" in (el.get("class") or "").split()
               for el in [node, *node.iterancestors()])


def _is_block(node):
    return isinstance(node.tag, str) and node.tag in BLOCK_TAGS


def _text_slots(node):
    # (owner, attribute, text): a tail belongs to the owner's parent.
    if node.text:
        yield node, "text", node.text
    for child in node:
        if isinstance(child.tag, str):
            yield from _text_slots(child)
        if child.tail:
            yield child, "tail", child.tail


def _wrap_slot(node, attr, start, end, tag, cls, css=None, mark=None):
    value = getattr(node, attr)
    wrapper = etree.Element(tag)
    if cls:
        wrapper.set("class", cls)
    if css:
        wrapper.set("style", css)
    if mark:
        wrapper.set("data-editor-format", mark)
    wrapper.text = value[start:end]
    wrapper.tail = value[end:]
    setattr(node, attr, value[:start])
    if attr == "text":
        node.insert(0, wrapper)
    else:
        parent = node.getparent()
        parent.insert(parent.index(node) + 1, wrapper)


def _split_container(child):
    """Lift one direct child out, keeping its preceding/following siblings in
    separate containers. Preserve ordered-list numbering, attrs and tails."""
    container=child.getparent()
    outer=container.getparent()
    if outer is None:
        raise ValueError("Не удалось преобразовать блок")
    children=list(container)
    index=children.index(child)
    before,after=children[:index],children[index+1:]
    position=outer.index(container)
    trailing=container.tail
    container.tail=None
    if after:
        right=etree.Element(container.tag,attrib=dict(container.attrib))
        right.attrib.pop("id",None)
        if container.tag=="ol":
            try:
                first=int(container.get("start","1"))
            except ValueError:
                first=1
            right.set("start",str(first+index+1))
        for sibling in after:
            right.append(sibling)
        right.tail=trailing
    else:
        right=None
    container.remove(child)
    if not before:
        outer.remove(container)
    else:
        position+=1
    outer.insert(position,child)
    if right is not None:
        outer.insert(position+1,right)
    else:
        child.tail=(child.tail or "")+(trailing or "")
    return child


def _list_item(node):
    parent=node.getparent()
    if node.tag=="li" and parent is not None and parent.tag in ("ul","ol"):
        return node
    if node.tag=="p" and parent is not None and parent.tag=="li" and len(parent)==1 and not (parent.text or "").strip():
        return parent
    return None


def _role_change(node,style):
    tag,cls=BLOCK_STYLES[style]
    item=_list_item(node)
    desired="ul" if style=="bullet" else "ol" if style=="numbered" else None
    if item is not None:
        container=item.getparent()
        if desired==container.tag:
            return
        if item is not node:
            # A loose list item containing just a paragraph can be flattened
            # without changing the visible text or dropping inline children.
            item.text=node.text
            for child in list(node):
                item.append(child)
            for key,value in node.attrib.items():
                if key!="id" or "id" not in item.attrib:
                    item.set(key,value)
            item.remove(node)
            node=item
        _split_container(node)
    elif node.getparent() is not None and node.getparent().tag=="blockquote" and style!="quote":
        _split_container(node)
    elif node.getparent() is not None and node.getparent().tag=="blockquote" and style=="quote":
        return
    node.tag=tag
    classes=[c for c in (node.get("class") or "").split() if c not in EDITOR_CLASSES]
    if cls:
        classes.append(cls)
    if classes:
        node.set("class"," ".join(classes))
    else:
        node.attrib.pop("class",None)
    if desired:
        parent=node.getparent()
        index=parent.index(node)
        tail=node.tail
        node.tail=None
        wrapper=etree.Element(desired)
        parent.insert(index,wrapper)
        wrapper.append(node)
        wrapper.tail=tail
        # Adjacent lists with matching kind form one list.
        previous=wrapper.getprevious()
        if previous is not None and previous.tag==desired and not (previous.tail or "").strip():
            previous.append(node)
            previous.tail=wrapper.tail
            parent.remove(wrapper)
            wrapper=previous
        following=wrapper.getnext()
        if following is not None and following.tag==desired and not (wrapper.tail or "").strip():
            if desired=="ul" or following.get("start") is None:
                for sibling in list(following):
                    wrapper.append(sibling)
                wrapper.tail=following.tail
                parent.remove(following)


class DocumentEditor:
    def __init__(self, rendered_html: str):
        self._undo = []
        self._redo = []
        self._load(rendered_html)
        head = self._doc.find("head")
        style = etree.SubElement(head, "style")
        style.text = EDITOR_CSS

    def _load(self, value):
        self._doc = html.document_fromstring(value)
        mains = self._doc.xpath("//main")
        if len(mains) != 1:
            raise ValueError("Expected one document body")
        self._main = mains[0]

    def _nodes(self):
        nodes = []
        for node in self._main.iterdescendants():
            if not _is_block(node) or _is_header(node):
                continue
            if any(_is_block(child) for child in node.iterdescendants()):
                continue
            if node.tag == "div" and "plain-text" not in (node.get("class") or "").split():
                continue
            if "".join(node.itertext()).strip():
                nodes.append(node)
        # Header fields follow body blocks in the model so existing project
        # indices and matching keys remain compatible with previous versions.
        nodes.extend(n for n in self._header_nodes()[1:] if "".join(n.itertext()).strip())
        return nodes

    def blocks(self):
        result = []
        for n in self._nodes():
            classes = (n.get("class") or "").split()
            role = "note" if "editor-note" in classes else "warning" if "editor-warning" in classes else n.tag
            if "header-right-title" in classes or "editor-meta-version" in classes:
                role="meta-version"
            elif "header-right-update" in classes or "editor-meta-updated" in classes:
                role="meta-updated"
            if role=="p" and any(a.tag=="blockquote" for a in n.iterancestors()):
                role="blockquote"
            item=_list_item(n)
            if item is not None:
                role="bullet" if item.getparent().tag=="ul" else "numbered"
            locked = n.tag in {"td","th"} or any(a.tag in {"table","td","th"} for a in n.iterancestors())
            if item is None and any(a.tag in {"ul","ol","li"} for a in n.iterancestors()):
                locked=True
            if any(a.tag=="blockquote" for a in n.iterancestors()) and n.getparent().tag!="blockquote":
                locked=True
            cell=self._cell(n)
            if cell is not None:
                role="table-heading" if cell.tag=="th" else "table-cell"
            if _is_header(n):
                locked=True
            result.append(Block("".join(n.itertext()), n.tag, role, locked))
        return result

    def runs(self, index):
        """Visible inline runs in source order; their concatenation matches block text."""
        node = self._nodes()[index]
        result = []
        for owner, attr, value in _text_slots(node):
            parent = owner if attr == "text" else owner.getparent()
            lineage = [parent, *parent.iterancestors()]
            tags = {el.tag for el in lineage}
            classes = {cls for el in lineage for cls in (el.get("class") or "").split()}
            flags=("strong" in tags or "b" in tags,
                   "em" in tags or "i" in tags, "code" in tags or "pre" in tags,
                   "brand-accent" in classes)
            explicit=next((el.get("data-editor-format") for el in lineage if el.get("data-editor-format") is not None),None)
            if explicit is not None and re.fullmatch("[01]{4}",explicit):
                flags=tuple(c=="1" for c in explicit)
            result.append((value,*flags))
        return result

    def html(self):
        return html.tostring(self._doc, encoding="unicode", method="html", doctype="<!doctype html>")

    def preview_html(self):
        """Return HTML with unique layout anchors and a parallel block ID list."""
        ids = {n.get("id") for n in self._doc.xpath("//*[@id]")}
        anchors = []
        for i,node in enumerate(self._nodes()):
            value = node.get("id")
            if not value or len(self._doc.xpath("//*[@id=$value]",value=value)) != 1:
                value = "mdtopdf-preview-" + str(i)
                while value in ids:
                    value += "-x"
                node.set("id",value)
                ids.add(value)
            anchors.append(value)
        return self.html(), anchors

    def _header_nodes(self):
        headers = self._main.xpath('./div[contains(concat(" ",normalize-space(@class)," ")," doc-header ")]')
        if not headers:
            return []
        nodes = []
        for query in ('./div[@class="header-left"]/span','./div[@class="header-right"]/span[@class="header-right-title"]','./div[@class="header-right"]/span[@class="header-right-update"]'):
            found = headers[0].xpath(query)
            if len(found)!=1:
                return []
            nodes.append(found[0])
        return nodes

    def header_fields(self):
        nodes = self._header_nodes()
        return tuple(n.text or "" for n in nodes) if nodes else None

    def set_header(self, name, version, updated):
        nodes = self._header_nodes()
        if not nodes:
            raise ValueError("No brand header")
        self._checkpoint()
        for node,value in zip(nodes,(name,version,updated)):
            node.text = value.strip()

    def _checkpoint(self):
        self._undo.append(self.html())
        self._redo.clear()

    def undo(self):
        if self._undo:
            self._redo.append(self.html())
            self._load(self._undo.pop())
            return True
        return False

    def redo(self):
        if self._redo:
            self._undo.append(self.html())
            self._load(self._redo.pop())
            return True
        return False

    def selection_role(self, ranges):
        roles = []
        blocks = self.blocks()
        for i,a,b in ranges:
            block = blocks[i]
            role = {"p":"normal","div":"normal","blockquote":"quote","pre":"code-block"}.get(block.role,block.role)
            pos = 0
            for value,bold,italic,mono,accent in self.runs(i):
                if pos < b and pos+len(value)>a:
                    # Semantic paragraph roles take precedence; inline roles
                    # are shown for ordinary text only.
                    inline = [k for k,flag in (("bold",bold),("italic",italic),("code",mono),("accent",accent)) if flag]
                    roles.append(role if role!="normal" or not inline else inline[0] if len(inline)==1 else "mixed")
                pos += len(value)
        return roles[0] if roles and all(x==roles[0] for x in roles) else "mixed" if roles else ""

    def sample(self,ranges,family,points,color=None):
        """Capture a uniform role plus visible typography; copy no text."""
        if not ranges:
            raise ValueError("Выделите образец оформления")
        roles=set()
        flags=set()
        for i,a,b in ranges:
            role=self.blocks()[i].role
            roles.add({"p":"normal","div":"normal","blockquote":"quote","pre":"code-block"}.get(role,role))
            pos=0
            for value,*marks in self.runs(i):
                if pos<b and pos+len(value)>a:
                    flags.add(tuple(marks))
                pos+=len(value)
        if len(roles)!=1 or len(flags)!=1 or next(iter(roles)) not in BLOCK_STYLES or next(iter(roles)) in METADATA_STYLES:
            raise ValueError("Выберите фрагмент с единым оформлением")
        if not FONT.fullmatch(family):
            raise ValueError("Не удалось определить шрифт образца")
        size=float(points)
        if not math.isfinite(size) or not 5<=size<=72:
            raise ValueError("Не удалось определить размер образца")
        return "sample:"+json.dumps(dict(role=next(iter(roles)),font=family,size=size,
                   marks="".join("1" if v else "0" for v in next(iter(flags))),color=color),
                   ensure_ascii=False,separators=(",",":"))

    @staticmethod
    def _cell(node):
        return next((n for n in [node,*node.iterancestors()] if n.tag in ("td","th")),None)

    def _table(self,ranges):
        nodes=self._nodes()
        tables=set()
        for i,_,_ in ranges:
            if not 0<=i<len(nodes):
                raise ValueError("Неверное выделение")
            table=next((n for n in nodes[i].iterancestors() if n.tag=="table"),None)
            if table is None:
                raise ValueError("Выберите ячейку таблицы")
            tables.add(table)
        if len(tables)!=1:
            raise ValueError("Выберите одну таблицу")
        return next(iter(tables))

    def table_settings(self,ranges):
        table=self._table(ranges)
        try:
            return json.loads(table.get("data-editor-table","{}")) or {"width":100,"align":"left","grid":"preset"}
        except ValueError:
            return {"width":100,"align":"left","grid":"preset"}

    def _assign_metadata(self,style,spans):
        if len(spans)!=1:
            raise ValueError("Выделите один абзац для шапки.")
        i,(start,end)=next(iter(spans.items()))
        node=self._nodes()[i]
        headers=self._header_nodes()
        text="".join(node.itertext())
        field,prefix=METADATA_STYLES[style]
        target=headers[field] if headers else None
        if target is node:
            return [(i,start,end)]
        if _is_header(node):
            raise ValueError("Изменить значения шапки можно через «Изменить шапку».")
        if self.blocks()[i].locked:
            raise ValueError("Выберите самостоятельный текстовый абзац.")
        if target is None:
            self._checkpoint()
            _role_change(node,style)
            return [(i,start,end)]
        if text[start:end].strip()!=text.strip():
            raise ValueError("Для переноса в шапку выделите весь абзац одним кликом.")
        if node.xpath(".//a|.//img|.//table|.//input"):
            raise ValueError("Для шапки выберите текст без ссылок и изображений.")
        value=text.strip()
        pattern=r"^\s*(?:версия|version)\s*:?\s*" if field==1 else r"^\s*(?:последнее обновление|last updated|last update)\s*:?\s*"
        value=prefix+" "+re.sub(pattern,"",value,flags=re.I).strip()
        if not value[len(prefix):].strip():
            raise ValueError("Укажите значение, а не только название поля.")
        existing="".join(target.itertext()).strip()
        if existing and existing!=value:
            raise ValueError("Поле шапки уже заполнено. Измените его через «Изменить шапку».")
        self._checkpoint()
        # Lift a simple list item or quote paragraph before removal, preserving
        # adjacent entries. Never leave an empty list or duplicate body text.
        _role_change(node,"normal")
        node=self._nodes()[i]
        parent=node.getparent()
        tail=node.tail
        previous=node.getprevious()
        if tail:
            if previous is not None:
                previous.tail=(previous.tail or "")+tail
            else:
                parent.text=(parent.text or "")+tail
        parent.remove(node)
        for child in list(target):
            target.remove(child)
        target.text=value
        j=self._nodes().index(target)
        return [(j,0,len(value))]

    def apply(self, style, ranges):
        """Ranges are (block index, start, end) in Python Unicode characters."""
        nodes = self._nodes()
        css = None
        mark = None
        sample = None
        if style.startswith("sample:"):
            sample=json.loads(style[7:])
            role=sample["role"]
            family=sample["font"]
            size=float(sample["size"])
            mark=sample["marks"]
            color=sample.get("color")
            if role not in BLOCK_STYLES or role in METADATA_STYLES or not FONT.fullmatch(family) or not math.isfinite(size) or not 5<=size<=72 or not re.fullmatch("[01]{4}",mark):
                raise ValueError("Недопустимый образец оформления")
            if color is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}",color):
                raise ValueError("Недопустимый цвет образца")
            css=f'font-family: "{family}", sans-serif; font-size: {size:g}pt; font-weight: '+("bold" if mark[0]=="1" or role.startswith("h") else "normal")+"; font-style: "+("italic" if mark[1]=="1" else "normal")
            if color:
                css+="; color: "+color
        elif style.startswith("font:"):
            family = style[5:]
            if not FONT.fullmatch(family):
                raise ValueError("Недопустимое название шрифта")
            css = 'font-family: "' + family + '", sans-serif'
        elif style.startswith("size:"):
            size = float(style[5:])
            if not math.isfinite(size) or not 5 <= size <= 72:
                raise ValueError("Размер шрифта: от 5 до 72 pt")
            css = f"font-size: {size:g}pt"
        elif style not in INLINE_STYLES and style not in BLOCK_STYLES and style not in TABLE_STYLES and not style.startswith("table-settings:"):
            raise ValueError("Unknown style")
        spans = {}
        for index, start, end in ranges:
            if not 0 <= index < len(nodes):
                raise ValueError("Invalid block")
            length = len("".join(nodes[index].itertext()))
            if not 0 <= start < end <= length:
                raise ValueError("Invalid text selection")
            if index in spans:
                raise ValueError("One range per block")
            spans[index] = (start, end)
        if not spans:
            raise ValueError("Select text first")
        if style in METADATA_STYLES:
            return self._assign_metadata(style,spans)
        if style in TABLE_STYLES:
            cells=[self._cell(nodes[i]) for i in spans]
            if any(c is None for c in cells):
                raise ValueError("Этот стиль применяется к существующей ячейке таблицы.")
            self._checkpoint()
            for cell in set(cells):
                cell.tag=TABLE_STYLES[style]
            return list(ranges)
        if style.startswith("table-settings:"):
            table=self._table(ranges)
            settings=json.loads(style.split(":",1)[1])
            width=settings.get("width")
            align=settings.get("align")
            grid=settings.get("grid")
            if type(width) is not int or not 20<=width<=100 or align not in ("left","center","right") or grid not in ("preset","show","hide"):
                raise ValueError("Недопустимые параметры таблицы")
            self._checkpoint()
            classes=[c for c in (table.get("class") or "").split() if c not in ("editor-grid","editor-no-grid")]
            if grid!="preset":
                classes.append("editor-grid" if grid=="show" else "editor-no-grid")
            table.set("class"," ".join(classes))
            margins={"left":"0 auto","center":"auto auto","right":"auto 0"}
            left,right=margins[align].split()
            table.set("style",f"width: {width}%; margin-left: {left}; margin-right: {right};")
            table.set("data-editor-table",json.dumps(settings,ensure_ascii=False))
            return list(ranges)
        if style in BLOCK_STYLES or sample is not None:
            blocks = self.blocks()
            if any(blocks[i].locked for i in spans):
                raise ValueError("Для этой ячейки таблицы или сложного вложенного блока доступны только символьные стили, шрифт и размер.")
        self._checkpoint()
        for i, (start, end) in spans.items():
            node = nodes[i]
            if style in BLOCK_STYLES:
                _role_change(node,style)
            else:
                if sample is not None:
                    _role_change(node,sample["role"])
                    # Block indices and text remain stable for supported transformations.
                    node=self._nodes()[i]
                tag, cls = ("span","") if css else INLINE_STYLES[style]
                pos = 0
                changes = []
                for owner, attr, text in _text_slots(node):
                    a, b = max(0, start-pos), min(len(text), end-pos)
                    if a < b:
                        changes.append((owner, attr, a, b))
                    pos += len(text)
                for owner, attr, a, b in reversed(changes):
                    _wrap_slot(owner, attr, a, b, tag, cls, css, mark)
