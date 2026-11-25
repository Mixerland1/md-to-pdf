"""Selection-based semantic style operations on a rendered HTML document."""
from __future__ import annotations

from dataclasses import dataclass
from lxml import html, etree
from .profiles import FONT
import math

INLINE_STYLES = {"bold": ("strong", ""), "italic": ("em", ""),
                 "code": ("code", ""), "accent": ("span", "brand-accent")}
BLOCK_STYLES = {"normal": ("p", ""), "h1": ("h1", ""), "h2": ("h2", ""),
                "h3": ("h3", ""), "quote": ("blockquote", ""),
                "note": ("p", "editor-note"), "warning": ("p", "editor-warning"),
                "code-block": ("pre", "")}
BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "blockquote",
              "li", "td", "th", "div"}
EDITOR_CLASSES = {"editor-note", "editor-warning"}
EDITOR_CSS = """
.editor-note { border-left: 3px solid #9ca3af; background: #f3f4f6; padding: .7em; }
.editor-warning { border-left: 3px solid #b50e25; background: #fff1f2; padding: .7em; }
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


def _wrap_slot(node, attr, start, end, tag, cls, css=None):
    value = getattr(node, attr)
    wrapper = etree.Element(tag)
    if cls:
        wrapper.set("class", cls)
    if css:
        wrapper.set("style", css)
    wrapper.text = value[start:end]
    wrapper.tail = value[end:]
    setattr(node, attr, value[:start])
    if attr == "text":
        node.insert(0, wrapper)
    else:
        parent = node.getparent()
        parent.insert(parent.index(node) + 1, wrapper)


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
        return nodes

    def blocks(self):
        result = []
        for n in self._nodes():
            classes = (n.get("class") or "").split()
            role = "note" if "editor-note" in classes else "warning" if "editor-warning" in classes else n.tag
            if role=="p" and any(a.tag=="blockquote" for a in n.iterancestors()):
                role="blockquote"
            locked = n.tag in {"li", "td", "th"} or any(
                a.tag in {"ul", "ol", "table", "blockquote", "li", "td", "th"} for a in n.iterancestors())
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
            result.append((value, "strong" in tags or "b" in tags,
                           "em" in tags or "i" in tags, "code" in tags or "pre" in tags,
                           "brand-accent" in classes))
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

    def apply(self, style, ranges):
        """Ranges are (block index, start, end) in Python Unicode characters."""
        nodes = self._nodes()
        css = None
        if style.startswith("font:"):
            family = style[5:]
            if not FONT.fullmatch(family):
                raise ValueError("Недопустимое название шрифта")
            css = 'font-family: "' + family + '", sans-serif'
        elif style.startswith("size:"):
            size = float(style[5:])
            if not math.isfinite(size) or not 5 <= size <= 72:
                raise ValueError("Размер шрифта: от 5 до 72 pt")
            css = f"font-size: {size:g}pt"
        elif style not in INLINE_STYLES and style not in BLOCK_STYLES:
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
        if style in BLOCK_STYLES:
            blocks = self.blocks()
            if any(blocks[i].locked for i in spans):
                raise ValueError("Paragraph styles cannot replace table cells, list items or nested quotes")
        self._checkpoint()
        for i, (start, end) in spans.items():
            node = nodes[i]
            if style in BLOCK_STYLES:
                tag, cls = BLOCK_STYLES[style]
                node.tag = tag
                classes = [c for c in (node.get("class") or "").split() if c not in EDITOR_CLASSES]
                if cls:
                    classes.append(cls)
                if classes:
                    node.set("class", " ".join(classes))
                else:
                    node.attrib.pop("class", None)
            else:
                tag, cls = ("span","") if css else INLINE_STYLES[style]
                pos = 0
                changes = []
                for owner, attr, text in _text_slots(node):
                    a, b = max(0, start-pos), min(len(text), end-pos)
                    if a < b:
                        changes.append((owner, attr, a, b))
                    pos += len(text)
                for owner, attr, a, b in reversed(changes):
                    _wrap_slot(owner, attr, a, b, tag, cls, css)
