"""Single-document workspace: style operations survive compatible preset changes."""
from collections import defaultdict
from pathlib import Path
import tempfile
from .cli import render_html, layout_pdf
from .editor_model import DocumentEditor

def block_keys(model):
    counts = defaultdict(int)
    keys = []
    for block in model.blocks():
        key = (block.text, counts[block.text])
        counts[block.text] += 1
        keys.append(key)
    return keys

class Workspace:
    def __init__(self, source, **options):
        self.source = Path(source).resolve()
        self.options = options
        self.actions = []
        self.redo_actions = []
        self.model = DocumentEditor(render_html(self.source, **options))
        self.skipped = 0

    def _rebuild(self, options):
        model = DocumentEditor(render_html(self.source, **options))
        skipped = 0
        for kind, payload in self.actions:
            if kind == "header":
                if model.header_fields() is not None:
                    model.set_header(*payload)
                else:
                    skipped += 1
                continue
            keys = {key:i for i,key in enumerate(block_keys(model))}
            style, selections = payload
            ranges = [(keys[key],a,b) for key,a,b in selections if key in keys]
            # Never apply only a portion of a saved edit silently.
            if len(ranges) != len(selections):
                skipped += 1
                continue
            try:
                model.apply(style,ranges)
            except ValueError:
                skipped += 1
        self.model = model
        self.options = options
        self.skipped = skipped

    def preset(self, **options):
        self._rebuild(options)

    def apply(self, style, ranges):
        keys = block_keys(self.model)
        selections = [(keys[i],a,b) for i,a,b in ranges]
        self.model.apply(style,ranges)
        self.actions.append(("style",(style,selections)))
        self.redo_actions.clear()

    def header(self, fields):
        self.model.set_header(*fields)
        self.actions.append(("header",tuple(fields)))
        self.redo_actions.clear()

    def undo(self):
        if not self.actions:
            return False
        self.redo_actions.append(self.actions.pop())
        self._rebuild(self.options)
        return True

    def redo(self):
        if not self.redo_actions:
            return False
        self.actions.append(self.redo_actions.pop())
        self._rebuild(self.options)
        return True

    def snapshot(self):
        html, anchors = self.model.preview_html()
        return html, anchors, [b.text for b in self.model.blocks()], self.source

def render_snapshot(snapshot):
    html, anchors, texts, source = snapshot
    doc = layout_pdf(html,source)
    locations = {}
    for page_index,page in enumerate(doc.pages):
        for name,box in page.anchors.items():
            if name in anchors:
                locations.setdefault(name,[]).append((page_index,tuple(v*.75 for v in box)))
    return doc.write_pdf(), anchors, texts, locations

def export_bytes(source, data):
    target = Path(source).with_suffix(".pdf").resolve()
    if target == Path(source).resolve():
        raise ValueError("Нельзя заменить исходный документ")
    with tempfile.NamedTemporaryFile(dir=target.parent,suffix=".pdf",delete=False) as out:
        temporary = Path(out.name)
        try:
            out.write(data)
        except Exception:
            out.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
