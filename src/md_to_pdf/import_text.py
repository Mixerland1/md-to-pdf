"""Copy document text into an independent, editable Markdown draft."""
from pathlib import Path
import csv
import re
from datetime import date,datetime
from .inputs import word_html,read_text

COPY_EXTENSIONS={".pdf",".xlsx",".xls",".csv",".docx"}

def cell(value):
    if value is None:
        return ""
    if isinstance(value,(date,datetime)):
        value=value.isoformat()
    return str(value).replace("\\","\\\\").replace("|","\\|").replace("\r","").replace("\n"," ")

def table(rows):
    rows=[list(row) for row in rows]
    while rows and not any(v not in (None,"") for v in rows[-1]):
        rows.pop()
    if not rows:
        return ""
    cols=max((i+1 for row in rows for i,v in enumerate(row) if v not in (None,"")),default=0)
    if not cols:
        return ""
    if cols>256 or len(rows)*cols>500000:
        raise ValueError("Слишком большая таблица для текстового редактора")
    # Do not silently treat the first row of data as column headers.
    def row(values):
        return "| "+" | ".join(cell(v) for v in values[:cols]+[None]*max(0,cols-len(values)))+" |"
    return "\n".join([row([str(i+1) for i in range(cols)]),row(["---"]*cols),*(row(r) for r in rows)])

def word_text(path):
    from lxml import html
    root=html.fragment_fromstring(word_html(path),create_parent="div")
    def inline(n):
        return (n.text or "")+"".join(inline(c)+(c.tail or "") for c in n)
    def blocks(n,depth=0):
        tag=n.tag
        if tag=="table":
            rows=[[inline(c) for c in r.xpath("./td|./th")] for r in n.xpath("./thead/tr|./tbody/tr|./tr")]
            return table(rows)
        if tag in ("ul","ol"):
            result=[]
            for i,li in enumerate(n.xpath("./li"),1):
                text=(li.text or "")+"".join(inline(c)+(c.tail or "") for c in li if c.tag not in ("ul","ol"))
                result.append("  "*depth+(str(i)+". " if tag=="ol" else "- ")+text.strip())
                result.extend(blocks(c,depth+1) for c in li if c.tag in ("ul","ol"))
            return "\n".join(result)
        if re.fullmatch("h[1-6]",tag):
            return "#"*int(tag[1])+" "+inline(n).strip()
        if tag=="p":
            return inline(n).strip()
        return "\n\n".join(filter(None,(blocks(c,depth) for c in n)))
    return blocks(root)

def copy_document(path):
    path=Path(path)
    suffix=path.suffix.lower()
    if suffix==".pdf":
        import pypdfium2 as pdfium
        pages=[]
        with pdfium.PdfDocument(path) as doc:
            for i in range(len(doc)):
                page=doc[i]
                try:
                    text=page.get_textpage()
                    try:
                        value=text.get_text_range().replace("\r\n","\n").strip()
                    finally:
                        text.close()
                finally:
                    page.close()
                if value:
                    pages.append(value)
        result="\n\n".join(pages)
        if not result.strip():
            raise ValueError("В PDF нет текстового слоя. Распознавание сканов (OCR) пока не поддерживается.")
    elif suffix==".docx":
        result=word_text(path)
    elif suffix==".xlsx":
        from openpyxl import load_workbook
        book=load_workbook(path,read_only=True,data_only=True,keep_links=False)
        try:
            sections=[]
            for sheet in book:
                if (sheet.max_row or 0)>100000 or (sheet.max_column or 0)>256:
                    raise ValueError("Слишком большой лист Excel")
                rows=[]
                count=0
                for r in sheet.iter_rows(values_only=True):
                    rows.append(list(r))
                    count+=len(r)
                    if len(rows)>100000 or count>500000:
                        raise ValueError("Слишком большой лист Excel")
                if value:=table(rows):
                    sections.append("## "+sheet.title+"\n\n"+value)
            result="\n\n".join(sections)
        finally:
            book.close()
    elif suffix==".xls":
        import xlrd
        book=xlrd.open_workbook(str(path),on_demand=True)
        try:
            sections=[]
            for sheet in book.sheets():
                if sheet.nrows*sheet.ncols>500000 or sheet.ncols>256:
                    raise ValueError("Слишком большой лист Excel")
                if value:=table(sheet.row_values(i) for i in range(sheet.nrows)):
                    sections.append("## "+sheet.name+"\n\n"+value)
            result="\n\n".join(sections)
        finally:
            book.release_resources()
    elif suffix==".csv":
        text=read_text(path)
        try:
            dialect=csv.Sniffer().sniff(text[:8192],delimiters=",;\t")
        except csv.Error:
            dialect=csv.excel
        result=table(csv.reader(text.splitlines(),dialect))
    else:
        raise ValueError("Неподдерживаемый формат")
    if not result.strip():
        raise ValueError("Документ не содержит доступного текста")
    if len(result.encode("utf-8"))>8_000_000:
        raise ValueError("Слишком большой текст")
    return result
