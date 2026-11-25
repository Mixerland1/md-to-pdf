"""Source adapters: semantic HTML for Markdown, plain text and Word."""
from __future__ import annotations

from html import escape
from pathlib import Path
import re
from urllib.parse import urlsplit
import warnings

MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdown"}
EXTENSIONS = MARKDOWN_EXTENSIONS | {".txt", ".docx"}


def read_text(source: Path) -> str:
    raw = source.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Use UTF-8 or UTF-16 with BOM for text documents") from exc


def plain_text_html(source: Path) -> str:
    text = read_text(source).replace("\r\n", "\n").replace("\r", "\n")
    return '<div class="plain-text">' + escape(text) + '</div>'


def word_html(source: Path) -> str:
    import mammoth
    import bleach

    with source.open("rb") as stream:
        result = mammoth.convert_to_html(stream, external_file_access=False,
                                         include_embedded_style_map=False)
    for message in result.messages:
        warnings.warn(f"{source.name}: {message.message}", UserWarning, stacklevel=2)

    def allowed_attribute(tag, name, value):
        if name in {"id", "title"}:
            return True
        if tag == "a" and name == "href":
            try:
                return urlsplit(value).scheme.lower() in {"", "http", "https", "mailto"} and (
                    value.startswith("#") or urlsplit(value).scheme.lower() in {"http", "https", "mailto"})
            except ValueError:
                return False
        if tag == "img" and name == "src":
            return bool(re.match(r"^data:image/(png|jpeg|gif|webp|bmp|tiff);base64,[A-Za-z0-9+/=\r\n]+$", value, re.I))
        return ((tag == "img" and name == "alt") or
                (tag in {"td", "th"} and name in {"colspan", "rowspan"}) or
                (tag == "ol" and name == "start"))

    return bleach.clean(result.value, tags={
        "h1", "h2", "h3", "h4", "h5", "h6", "p", "div", "span", "a", "img",
        "strong", "em", "b", "i", "u", "s", "del", "sup", "sub", "ul", "ol",
        "li", "table", "thead", "tbody", "tfoot", "tr", "td", "th", "br",
        "hr", "blockquote", "pre", "code"
    }, attributes=allowed_attribute, protocols={"http", "https", "mailto", "data"}, strip=True)


def source_html(source: Path, markdown) -> str:
    suffix = source.suffix.lower()
    if suffix in MARKDOWN_EXTENSIONS:
        return markdown(read_text(source))
    if suffix == ".txt":
        return plain_text_html(source)
    if suffix == ".docx":
        return word_html(source)
    raise ValueError(f"Unsupported input: {suffix}")
