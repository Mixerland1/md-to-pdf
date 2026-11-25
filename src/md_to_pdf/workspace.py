"""Single-document workspace: style operations survive compatible preset changes."""
from collections import defaultdict
from pathlib import Path
import tempfile
import hashlib
import json
from dataclasses import asdict
from .profiles import Profile
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
        self.source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
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
            previous=model.html()
            try:
                for item in (style if isinstance(style,list) else [style]):
                    ranges=model.apply(item,ranges) or ranges
            except (ValueError,TypeError):
                model._load(previous)
                skipped += 1
        self.model = model
        self.options = options
        self.skipped = skipped

    def preset(self, **options):
        self._rebuild(options)

    def apply(self, style, ranges):
        # Composite brush changes are one undoable operation.
        previous = self.model.html()
        keys = block_keys(self.model)
        selections = [(keys[i],a,b) for i,a,b in ranges]
        result=ranges
        try:
            for item in (style if isinstance(style,list) else [style]):
                result=self.model.apply(item,result) or result
        except Exception:
            self.model._load(previous)
            raise
        self.actions.append(("style",(style,selections)))
        self.redo_actions.clear()
        return result

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

    @property
    def project_path(self):
        return self.source.with_name(self.source.name+".mdtopdf")

    @classmethod
    def from_clipboard(cls, text, directory, **options):
        if not isinstance(text,str) or not text.strip():
            raise ValueError("В буфере обмена нет текста")
        if len(text.encode("utf-8"))>8_000_000:
            raise ValueError("Слишком большой текст")
        # Use a private, per-document folder. No clipboard data is sent online.
        folder=Path(tempfile.mkdtemp(prefix="clipboard-",dir=directory))
        source=folder/"Без названия.md"
        source.write_bytes(text.encode("utf-8"))
        return cls(source,**options)

    def save_pasted(self, target, label):
        target=Path(target).resolve()
        if target.suffix.lower()!=".md":
            raise ValueError("Сохраните текст как Markdown (.md)")
        sidecar=target.with_name(target.name+".mdtopdf")
        if target.exists() or sidecar.exists():
            raise FileExistsError("Выберите новое имя: исходные файлы не перезаписываются")
        previous=self.source
        previous_model=self.model
        previous_skipped=self.skipped
        created=False
        try:
            with target.open("xb") as stream:
                created=True
                stream.write(previous.read_bytes())
            self.source=target
            self._rebuild(self.options)
            self.save(label)
        except Exception:
            self.source=previous
            self.model=previous_model
            self.skipped=previous_skipped
            if created:
                target.unlink(missing_ok=True)
            raise
        return target

    def save(self, label):
        if hashlib.sha256(self.source.read_bytes()).hexdigest()!=self.source_hash:
            raise ValueError("Исходный файл изменился. Откройте его заново.")
        profile=self.options.get("profile")
        value={"schema":1,"source_sha256":self.source_hash,"preset":label,
               "template":self.options.get("template","technical"),
               "profile":asdict(profile) if profile else None,"actions":self.actions}
        data=json.dumps(value,ensure_ascii=False,indent=2).encode("utf-8")
        if len(data)>8_000_000:
            raise ValueError("Слишком большой проект")
        with tempfile.NamedTemporaryFile(dir=self.source.parent,delete=False) as out:
            temporary=Path(out.name)
            try:
                out.write(data)
            except Exception:
                out.close()
                temporary.unlink(missing_ok=True)
                raise
        try:
            temporary.replace(self.project_path)
        finally:
            temporary.unlink(missing_ok=True)
        return self.project_path

    def restore(self):
        if not self.project_path.is_file():
            return None
        with self.project_path.open("rb") as stream:
            data=stream.read(8_000_001)
        if len(data)>8_000_000:
            raise ValueError("Слишком большой проект")
        value=json.loads(data)
        if value.get("schema")!=1 or value.get("source_sha256")!=self.source_hash:
            raise ValueError("Сохранённые правки относятся к другой версии исходного файла.")
        profile=Profile(**value["profile"]).validate() if value.get("profile") else None
        actions=[]
        for kind,payload in value["actions"]:
            if kind=="header" and len(payload)==3 and all(isinstance(v,str) for v in payload):
                actions.append((kind,tuple(payload)))
            elif kind=="style":
                style,selections=payload
                styles=style if isinstance(style,list) else [style]
                if not styles or len(styles)>3 or not all(isinstance(v,str) for v in styles):
                    raise ValueError("Некорректный стиль проекта")
                actions.append((kind,(style,[(tuple(key),a,b) for key,a,b in selections])))
            else:
                raise ValueError("Неизвестная операция проекта")
        self.actions=actions
        self._rebuild(dict(template=value["template"],profile=profile))
        return value.get("preset","")

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
    return write_pdf_bytes(target,data)

def write_pdf_bytes(target,data):
    target=Path(target).resolve()
    if target.suffix.lower()!=".pdf":
        raise ValueError("Выберите файл PDF")
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
