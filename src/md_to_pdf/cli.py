"""Convert local Markdown, TXT and DOCX files to paginated PDF or standalone HTML."""
from __future__ import annotations

import argparse
from datetime import date
from html import escape, unescape
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit, unquote

import mistune
from .inputs import source_html, read_text, MARKDOWN_EXTENSIONS
from .branding import Header, extract_document_header, render_header
from .profiles import Profile, load_profile
from .font_assets import bundled_font_css

TEMPLATES = ('technical', 'business', 'academic', 'granulex')


class DocumentRenderer(mistune.HTMLRenderer):
    def __init__(self, *, allow_html: bool = False):
        super().__init__(escape=not allow_html)
        self.ids: set[str] = set()

    def heading(self, text: str, level: int, **attrs) -> str:
        plain = unescape(re.sub(r"<[^>]*>", "", text)).lower()
        slug = re.sub(r"[^\w\- ]", "", plain).replace(" ", "-") or "section"
        candidate, n = slug, 1
        while candidate in self.ids:
            candidate = f"{slug}-{n}"
            n += 1
        self.ids.add(candidate)
        return f'<h{level} id="{escape(candidate, quote=True)}">{text}</h{level}>\n'


def render_html(source: Path, *, title: str | None = None,
                document_date: str | None = None, css: Path | None = None,
                allow_html: bool = False, template: str = 'technical',
                brand_name: str | None = None, brand_version: str | None = None,
                brand_updated: str | None = None, profile: Profile | None = None) -> str:
    source = source.resolve()
    title = title or source.stem
    document_date = document_date or date.today().strftime("%d.%m.%Y")
    markdown = mistune.create_markdown(renderer=DocumentRenderer(allow_html=allow_html),
                                      plugins=["table", "strikethrough", "task_lists", "footnotes", "url"])
    brand = ""
    if profile is not None:
        profile.validate()
        template = profile.base
        if source.suffix.lower() in MARKDOWN_EXTENSIONS:
            text, header = extract_document_header(read_text(source), default_name=profile.product or profile.name,
                                                   keep_embedded_name=False)
            content = markdown(text)
        else:
            header = Header(name=profile.product or profile.name)
            content = source_html(source, markdown)
        brand = render_header(header, name=brand_name,
                              version=brand_version, updated=brand_updated, logo_uri=profile.logo_uri())
    elif template == "granulex":
        if source.suffix.lower() in MARKDOWN_EXTENSIONS:
            text, header = extract_document_header(read_text(source))
            content = markdown(text)
        else:
            header = Header()
            content = source_html(source, markdown)
        brand = render_header(header, name=brand_name, version=brand_version, updated=brand_updated)
    else:
        content = source_html(source, markdown)
    style = Path(__file__).with_name("print.css").read_text(encoding="utf-8")
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template: {template}")
    style += "\n" + Path(__file__).with_name("templates").joinpath(template + ".css").read_text(encoding="utf-8")
    if profile is not None:
        style += "\n" + profile.css()
    if template == "granulex" or profile is not None:
        style = bundled_font_css() + "\n" + style
    # A linked custom stylesheet retains its own base URL for relative assets.
    custom = f'<link rel="stylesheet" href="{escape(css.resolve().as_uri(), quote=True)}">' if css else ""
    return f'''<!doctype html>
<html lang="und"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<base href="{escape(source.parent.as_uri() + '/', quote=True)}">
<title>{escape(title)}</title><style>{style}</style>{custom}</head>
<body><div class="document-title">{escape(title)}</div>
<div class="document-date">{escape(document_date)}</div>
<main>{brand}{content}</main></body></html>'''


def convert(source: Path, output: Path, *, title: str | None = None,
            document_date: str | None = None, css: Path | None = None,
            allow_html: bool = False, html_only: bool = False, template: str = 'technical',
                brand_name: str | None = None, brand_version: str | None = None,
                brand_updated: str | None = None, profile: Profile | None = None) -> None:
    source, output = source.resolve(), output.resolve()
    if source == output:
        raise ValueError("Input and output must be different files")
    if css and not css.is_file():
        raise FileNotFoundError(css)
    html = render_html(source, title=title, document_date=document_date,
                       css=css, allow_html=allow_html, template=template,
                       brand_name=brand_name, brand_version=brand_version, brand_updated=brand_updated, profile=profile)
    output.parent.mkdir(parents=True, exist_ok=True)
    if html_only:
        output.write_text(html, encoding="utf-8")
        return
    from weasyprint import HTML
    from weasyprint.urls import URLFetcher
    from urllib.request import url2pathname

    roots = [source.parent]
    if css:
        roots.append(css.resolve().parent)
    default = URLFetcher()

    class LocalFetcher(URLFetcher):
        def fetch(self, url, *args, **kwargs):
            parts = urlsplit(url)
            if parts.scheme == "data":
                return default.fetch(url, *args, **kwargs)
            if parts.scheme == "file" and parts.netloc in ("", "localhost"):
                candidate = Path(url2pathname(parts.path)).resolve()
                if any(candidate.is_relative_to(root) for root in roots):
                    return default.fetch(url, *args, **kwargs)
            raise ValueError(f"Blocked resource outside local document folders: {url}")

    HTML(string=html, base_url=source.parent.as_uri() + "/", url_fetcher=LocalFetcher()).write_pdf(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="+", help="Markdown, TXT, DOCX files or folders")
    parser.add_argument("--recursive", action="store_true", help="Include subfolders")
    parser.add_argument("--output-dir", type=Path, help="Output folder for batch conversion")
    parser.add_argument("--overwrite", action="store_true", help="Allow replacing existing outputs")
    parser.add_argument("--template", choices=TEMPLATES, default="technical")
    parser.add_argument("-o", "--output", type=Path, help="Output path (default: next to input)")
    parser.add_argument("--css", type=Path, help="Additional print stylesheet")
    parser.add_argument("--title", help="Document title (default: filename without extension)")
    parser.add_argument("--date", help="Footer date (default: today, DD.MM.YYYY)")
    parser.add_argument("--html-only", action="store_true", help="Export HTML rather than PDF")
    parser.add_argument("--allow-html", action="store_true", help="Allow raw HTML in trusted Markdown (not TXT or DOCX)")
    parser.add_argument("--brand-name", help="Brand header product name")
    parser.add_argument("--brand-version", help="Brand header product version")
    parser.add_argument("--brand-updated", help="Brand header update date/text")
    parser.add_argument("--profile", type=Path, help="Portable brand profile JSON (overrides template)")
    args = parser.parse_args(argv)
    from .batch import collect_sources, plan_outputs
    try:
        profile = load_profile(args.profile) if args.profile else None
        sources = collect_sources(args.source, recursive=args.recursive)
        if args.output and (len(sources) != 1 or args.output_dir):
            raise ValueError("-o requires exactly one input and cannot be combined with --output-dir")
        jobs = plan_outputs(sources, output_dir=args.output_dir, explicit=args.output,
                            html_only=args.html_only, overwrite=args.overwrite)
    except (OSError, ValueError) as exc:
        print(f"md-to-pdf: {exc}", file=sys.stderr)
        return 1
    failures = 0
    for source, output in jobs:
        try:
            convert(source, output, title=args.title, document_date=args.date,
                    css=args.css, allow_html=args.allow_html, html_only=args.html_only,
                    template=args.template, brand_name=args.brand_name,
                    brand_version=args.brand_version, brand_updated=args.brand_updated, profile=profile)
            print(f"Wrote {output.resolve()}")
        except Exception as exc:
            failures += 1
            print(f"{source}: {exc}", file=sys.stderr)
    return int(failures != 0)


if __name__ == "__main__":
    raise SystemExit(main())
