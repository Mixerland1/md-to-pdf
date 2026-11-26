"""Compact Phantom title and restricted guide markup adapter."""
from html import escape
from pathlib import Path
import base64
import re
from urllib.parse import urlsplit, unquote
from lxml import html
import bleach
from bleach.css_sanitizer import CSSSanitizer
from .branding import Header, extract_document_header, safe_svg

TITLE=re.compile(r'\A\s*<section\b[^>]*\bclass=["\x27]title-page["\x27][^>]*>[\s\S]*?</section>\s*',re.I)
VERSION=re.compile(r"^(.*?)\s+v?(\d+(?:\.\d+){1,3})$")
TAGS={"h1","h2","h3","h4","h5","h6","p","div","section","span","a","img","strong","em","b","i","u","s","del","sup","sub","ul","ol","li","table","thead","tbody","tfoot","tr","td","th","br","hr","blockquote","pre","code","figure","figcaption","input"}
CSS=CSSSanitizer(allowed_css_properties={"width","height","max-width","margin","margin-left","margin-right","margin-bottom","margin-top","text-align","font-weight","font-style","color","background-color","display","vertical-align"})

def local_image(value):
    try:
        parts=urlsplit(value)
        if parts.scheme or parts.netloc or not parts.path or parts.query:
            return False
        path=unquote(parts.path).replace("\\","/")
        return not path.startswith("/") and ".." not in path.split("/") and Path(path).suffix.lower() in {".svg",".png",".jpg",".jpeg",".webp",".gif",".bmp"}
    except ValueError:
        return False

def image_uri(source,value):
    if not local_image(value):
        return ""
    path=(source.parent / unquote(urlsplit(value).path)).resolve()
    return path.as_uri() if path.is_relative_to(source.parent) and path.is_file() else ""

def default_logo_uri():
    svg=safe_svg(Path(__file__).with_name("templates").joinpath("phantom-logo.svg").read_text(encoding="utf-8"))
    return "data:image/svg+xml;base64,"+base64.b64encode(svg.encode()).decode("ascii")

def extract_phantom(source,text):
    match=TITLE.match(text)
    if not match:
        body,header=extract_document_header(text,default_name="Фантом",keep_embedded_name=False)
        return body,header,"",image_uri(source,"images/logo.svg")
    tree=html.fragment_fromstring(match.group())
    def field(cls):
        return tree.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," '+cls+' ")]')
    title=field("title-main")
    subtitle=field("title-sub")
    logos=field("title-logo")
    product=title[0].text_content().strip() if title else "Фантом"
    name=product
    version=""
    parsed=VERSION.fullmatch(product)
    if parsed:
        name,version=parsed.groups()
        version="Версия "+version
    heading=subtitle[0].text_content().strip() if subtitle else product
    logo=image_uri(source,logos[0].get("src","")) if logos else image_uri(source,"images/logo.svg")
    footer=field("title-footer")
    place=" ".join(footer[0].text_content().split()) if footer else ""
    lead='<h1 class="phantom-document-heading">'+escape(heading)+'</h1>'
    if place:
        lead+='<p class="phantom-origin">'+escape(place)+'</p>'
    return text[match.end():],Header(name=name,version=version),lead,logo

def render_phantom_content(rendered):
    def attrs(tag,name,value):
        if name in ("id","class","title"):
            return True
        if name=="style":
            return tag in {"span","p","div","img","td","th"}
        if tag=="img" and name=="src":
            return local_image(value)
        if tag=="img" and name=="alt":
            return True
        if tag=="a" and name=="href":
            try:
                return value.startswith("#") or urlsplit(value).scheme.lower() in {"https","http","mailto"}
            except ValueError:
                return False
        return (tag in {"td","th"} and name in {"rowspan","colspan"}) or (tag=="ol" and name=="start") or (tag=="input" and name in {"type","checked","disabled"})
    cleaned=bleach.clean(rendered,tags=TAGS,attributes=attrs,protocols={"https","http","mailto"},css_sanitizer=CSS,strip=True)
    tree=html.fragment_fromstring(cleaned,create_parent="div")
    for heading in tree.xpath(".//h1|.//h2|.//h3|.//h4|.//h5|.//h6"):
        if heading.get("id") and heading.xpath(".//*[@id=$id]",id=heading.get("id")):
            heading.attrib.pop("id",None)
    ids=set(tree.xpath(".//*[@id]/@id"))
    for table in tree.xpath(".//table"):
        heads=table.xpath("./thead/tr/th")
        if [x.text_content().strip() for x in heads]!=["Раздел","Стр."]:
            continue
        table.set("class",((table.get("class") or "")+" phantom-toc").strip())
        for row in table.xpath("./tbody/tr"):
            cells=row.xpath("./td")
            if len(cells)!=2 or not cells[1].text_content().strip().isdigit():
                continue
            links=cells[0].xpath(".//a[starts-with(@href,'#')]")
            if not links:
                continue
            href=links[0].get("href")
            if unquote(href[1:]) not in ids:
                continue
            cell=cells[1]
            for child in list(cell):
                cell.remove(child)
            cell.text=None
            cell.append(html.Element("a",attrib={"href":href,"class":"phantom-toc-page"}))
    return (escape(tree.text) if tree.text else "")+"".join(html.tostring(child,encoding="unicode",method="html") for child in tree)
