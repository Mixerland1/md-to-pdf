"""Granulex document header adapter; deliberately narrow SVG allowlist."""
from __future__ import annotations

from dataclasses import dataclass
from html import escape, unescape
from pathlib import Path
import base64
import re
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2000/svg"
HEADER = re.compile(
    r'\A\s*<div\s+class="doc-header">\s*<div\s+class="header-left">\s*'
    r'(?P<svg><svg\b[^>]*>[\s\S]*?</svg>)\s*<span>(?P<name>[^<]*)</span>\s*</div>\s*'
    r'<div\s+class="header-right">\s*<span\s+class="header-right-title">(?P<version>[^<]*)</span>\s*'
    r'<span\s+class="header-right-update">(?P<updated>[^<]*)</span>\s*</div>\s*</div>\s*',
    re.IGNORECASE,
)
SVG_TAGS = {
    "svg": {"width", "height", "viewBox", "fill", "stroke"},
    "path": {"d", "fill", "stroke", "fill-rule", "clip-rule", "stroke-width"},
}
VALUE = re.compile(r"[A-Za-z0-9#.,+\-\s%]*\Z")


@dataclass(frozen=True)
class Header:
    name: str = "Granulex"
    version: str = ""
    updated: str = ""
    svg: str = ""


def safe_svg(svg: str) -> str:
    # Narrow support for self-contained path-only vector marks.
    if len(svg) > 100_000 or "<!" in svg or "<?" in svg:
        raise ValueError("Unsupported SVG declarations or size")
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise ValueError("Invalid SVG") from exc
    if root.tag != f"{{{NS}}}svg":
        raise ValueError("Expected SVG root")
    for el in root.iter():
        tag = el.tag.removeprefix(f"{{{NS}}}")
        if not el.tag.startswith(f"{{{NS}}}") or tag not in SVG_TAGS:
            raise ValueError("Unsupported SVG element")
        if tag == "path" and len(el):
            raise ValueError("Unexpected SVG path children")
        if el is not root and tag == "svg":
            raise ValueError("Nested SVG not supported")
        if any(k not in SVG_TAGS[tag] or not VALUE.fullmatch(v) for k, v in el.attrib.items()):
            raise ValueError("Unsupported SVG attribute")
        if (el.text or "").strip() or (el.tail or "").strip():
            raise ValueError("Unexpected text in SVG")
    ET.register_namespace("", NS)
    return ET.tostring(root, encoding="unicode")


def extract_header(text: str) -> tuple[str, Header]:
    match = HEADER.match(text)
    if not match:
        return text, Header()
    return text[match.end():], Header(
        name=unescape(match["name"]),
        version=unescape(match["version"]),
        updated=unescape(match["updated"]),
        svg=safe_svg(re.sub(r'"\s+"\s*/>', '"/>', match["svg"])),  # legacy stray quote before path close
    )


def render_header(header: Header, *, name: str | None = None,
                  version: str | None = None, updated: str | None = None, logo_uri: str | None = None) -> str:
    if logo_uri is None:
        svg = header.svg or safe_svg(Path(__file__).with_name("templates").joinpath("granulex-logo.svg").read_text(encoding="utf-8"))
        logo_uri = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode("ascii")
    logo = f'<img class="brand-logo" src="{escape(logo_uri, quote=True)}" alt=""/>' if logo_uri else ""
    n = header.name if name is None else name
    v = header.version if version is None else ("Версия " + version if version else "")
    u = header.updated if updated is None else ("Последнее обновление: " + updated if updated else "")
    return (
        '<div class="doc-header"><div class="header-left">'
        f'{logo}<span>{escape(n)}</span></div>'
        '<div class="header-right">'
        f'<span class="header-right-title">{escape(v)}</span>'
        f'<span class="header-right-update">{escape(u)}</span>'
        '</div></div>'
    )
