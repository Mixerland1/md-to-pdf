"""Portable, validated brand profiles. No executable CSS in profile files."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from io import BytesIO
import base64
import json
import re
import uuid
from .branding import safe_svg

MAX_FILE = 4_000_000
MAX_LOGO = 2_000_000
COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")
FONT = re.compile(r"[\w .-]{1,60}\Z")
BASES = ("technical", "business", "academic", "granulex", "phantom")


def bounded_read(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("File is too large")
    return data


def raster_png(data: bytes) -> bytes:
    from PIL import Image
    with Image.open(BytesIO(data)) as image:
        if image.format not in ("PNG", "JPEG"):
            raise ValueError("Only PNG and JPEG logos are accepted")
        if image.width * image.height > 4_000_000:
            raise ValueError("Logo exceeds four million pixels")
        image.thumbnail((1200, 1200))
        out = BytesIO()
        image.convert("RGBA").save(out, format="PNG", optimize=True)
    result = out.getvalue()
    if len(result) > MAX_LOGO:
        raise ValueError("Normalized logo too large; reduce image dimensions")
    return result


@dataclass(frozen=True)
class Profile:
    name: str = "New brand"
    base: str = "technical"
    product: str = ""
    accent: str = "#23578C"
    text: str = "#1F2937"
    heading: str = "#1F2937"
    table: str = "#23578C"
    table_text: str = "#FFFFFF"
    link: str = "#1556A0"
    muted: str = "#6B7280"
    font: str = "Arial"
    mono: str = "DejaVu Sans Mono"
    body_pt: float = 10.5
    line_height: float = 1.45
    margin_top: float = 18
    margin_right: float = 15
    margin_bottom: float = 20
    margin_left: float = 15
    logo_mm: float = 14
    page_numbers: bool = True
    footer: str = ""
    logo_kind: str = ""
    logo_data: str = ""

    def validate(self):
        for field in ("name", "product", "footer"):
            value = getattr(self, field)
            if not isinstance(value, str) or len(value) > 160 or any(ord(c) < 32 for c in value):
                raise ValueError(f"Invalid {field}")
        if not self.name.strip() or self.base not in BASES:
            raise ValueError("Profile needs a name and valid base template")
        for field in ("accent", "text", "heading", "table", "table_text", "link", "muted"):
            value = getattr(self, field)
            if not isinstance(value, str) or not COLOR.fullmatch(value):
                raise ValueError(f"{field}: enter #RRGGBB")
        for field in ("font", "mono"):
            value = getattr(self, field)
            if not isinstance(value, str) or not FONT.fullmatch(value):
                raise ValueError(f"Invalid font name: {field}")
        for field, lo, hi in (("body_pt", 7, 24), ("line_height", 1, 2.5),
                              ("margin_top", 5, 40), ("margin_right", 5, 40),
                              ("margin_bottom", 8, 40), ("margin_left", 5, 40),
                              ("logo_mm", 5, 35)):
            value = getattr(self, field)
            if type(value) not in (float, int) or not lo <= value <= hi:
                raise ValueError(f"{field}: expected {lo}–{hi}")
        if type(self.page_numbers) is not bool:
            raise ValueError("page_numbers must be boolean")
        if not isinstance(self.logo_data, str) or len(self.logo_data) > 3_000_000:
            raise ValueError("Invalid logo data")
        if self.logo_kind == "svg":
            safe_svg(self.logo_data)
        elif self.logo_kind == "png":
            raster_png(base64.b64decode(self.logo_data, validate=True))
        elif self.logo_kind != "" or self.logo_data:
            raise ValueError("Invalid logo kind")
        return self

    def logo_uri(self):
        if self.logo_kind == "svg":
            svg = safe_svg(self.logo_data)
        elif self.logo_kind == "png":
            # An SVG wrapper is not vector tracing: the embedded pixels remain raster.
            png = raster_png(base64.b64decode(self.logo_data, validate=True))
            from PIL import Image
            with Image.open(BytesIO(png)) as image:
                w, h = image.size
            payload = base64.b64encode(png).decode("ascii")
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                   f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
                   f'<image width="{w}" height="{h}" xlink:href="data:image/png;base64,{payload}"/></svg>')
        else:
            return ""
        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode("ascii")

    def css(self):
        self.validate()
        # Only validated colors, font names and numeric values enter CSS.
        # Footer text is represented using CSS Unicode escapes, never raw CSS.
        footer = '"' + "".join(f"\\{ord(c):x} " for c in self.footer) + '"'
        page = 'counter(page) " / " counter(pages)' if self.page_numbers else "none"
        return f"""
@page {{
 margin: {self.margin_top}mm {self.margin_right}mm {self.margin_bottom}mm {self.margin_left}mm;
 @top-center {{ content: none; }}
 @bottom-left {{ content: {footer}; color:{self.muted}; font:8pt "{self.font}",sans-serif; }}
 @bottom-center {{ content: none; }}
 @bottom-right {{ content: {page}; color:{self.muted}; font:8pt "{self.font}",sans-serif; }}
}}
body {{ color:{self.text}; font: {self.body_pt}pt/{self.line_height} "{self.font}",sans-serif; }}
h1,h2,h3,h4,h5,h6 {{ color:{self.heading}; font-family:"{self.font}",sans-serif; }}
code {{ font-family:"{self.mono}",monospace; }}
a {{ color:{self.link}; }}
th {{ background:{self.table}; color:{self.table_text}; }}
blockquote {{ border-left-color:{self.accent}; }}
.brand-accent {{ color:{self.accent}; }}
.doc-header {{ display:flex; align-items:center; justify-content:space-between; gap:12px; margin:0 0 16px; break-inside:avoid; break-after:avoid-page; }}
.header-left {{ display:flex; align-items:center; flex:1; color:{self.heading}; font-weight:700; }}
.header-left .brand-logo {{ width:auto; height:{self.logo_mm}mm; max-width:{self.logo_mm*2.5}mm; max-height:{self.logo_mm}mm; object-fit:contain; flex:none; margin-right:12px; }}
.header-right {{ display:flex; flex-direction:column; align-items:flex-end; text-align:right; color:{self.muted}; font-size:8pt; }}
.header-right span:empty {{ display:none; }}
.header-right-title {{ font-weight:700; }}
"""


def granulex_profile():
    logo = Path(__file__).with_name("templates").joinpath("granulex-logo.svg").read_text(encoding="utf-8")
    return Profile(name="Granulex", base="granulex", product="Granulex",
                   accent="#E2112E", table="#9CA3AF", link="#1A0DAB", muted="#6B7280",
                   font="Montserrat", mono="Roboto Mono", body_pt=8, line_height=1.5,
                   margin_top=8.4667, margin_right=14.8167, margin_bottom=19.05,
                   margin_left=14.8167, logo_mm=14.8167,
                   logo_kind="svg", logo_data=safe_svg(logo)).validate()


def phantom_profile():
    logo=Path(__file__).with_name("templates").joinpath("phantom-logo.svg").read_text(encoding="utf-8")
    return Profile(name="Фантом",base="phantom",product="Фантом",accent="#1F5F99",
                   text="#222222",heading="#222222",table="#F3F4F6",table_text="#222222",
                   link="#1F5F99",muted="#555555",font="Manrope",mono="Roboto Mono",
                   body_pt=10.5,line_height=1.45,margin_top=18,margin_right=18,
                   margin_bottom=18,margin_left=18,logo_mm=14,
                   logo_kind="svg",logo_data=safe_svg(logo)).validate()


def import_logo(path: Path):
    data = bounded_read(path, MAX_LOGO)
    if path.suffix.lower() == ".svg":
        return "svg", safe_svg(data.decode("utf-8-sig"))
    if path.suffix.lower() in (".png", ".jpg", ".jpeg"):
        return "png", base64.b64encode(raster_png(data)).decode("ascii")
    raise ValueError("Choose SVG, PNG or JPEG")


def load_profile(path: Path):
    data = json.loads(bounded_read(path, MAX_FILE).decode("utf-8-sig"))
    if not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != 1:
        raise ValueError("Unsupported profile schema")
    try:
        return Profile(**{k:v for k,v in data.items() if k != "schema"}).validate()
    except TypeError as exc:
        raise ValueError("Unknown profile fields") from exc


def save_profile(profile: Profile, path: Path):
    data = json.dumps({"schema":1, **asdict(profile.validate())}, ensure_ascii=False, indent=2)
    if len(data.encode()) > MAX_FILE:
        raise ValueError("Profile too large")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(data, encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def library_dir():
    return Path.home() / ".md-to-pdf" / "profiles"


def list_profiles():
    result = {}
    for path in sorted(library_dir().glob("*.json")):
        try:
            profile = load_profile(path)
        except (OSError, ValueError, TypeError, SyntaxError):
            continue
        result[f"{profile.name} [{path.stem[:8]}]"] = path
    return result
