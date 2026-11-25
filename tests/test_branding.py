import tempfile
import unittest
from pathlib import Path
from pypdf import PdfReader
from md_to_pdf.cli import render_html, convert
from md_to_pdf.branding import safe_svg

SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="42" height="42" viewBox="0 0 42 42" fill="#E2112E"><path d="M0 0 L42 42 Z"/></svg>'
HEADER = ('<div class="doc-header"><div class="header-left">' + SVG +
          '<span>Example product</span></div><div class="header-right">'
          '<span class="header-right-title">Version X</span>'
          '<span class="header-right-update">Date X</span></div></div>\n\n')

class BrandingTests(unittest.TestCase):
    def test_embedded_header_and_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.md"
            p.write_text(HEADER + "# Body marker", encoding="utf-8")
            html = render_html(p, template="granulex")
            self.assertEqual(html.count('class="doc-header"'), 1)
            self.assertEqual(html.count('class="brand-logo"'), 1)
            self.assertIn("Example product", html)
            self.assertIn("Version X", html)
            self.assertIn("<h1", html)
            override = render_html(p, template="granulex", brand_name="New & name", brand_version="1.2")
            self.assertIn("New &amp; name", override)
            self.assertNotIn("Version X", override)
            convert(p, p.with_suffix(".pdf"), template="granulex")
            page = PdfReader(p.with_suffix(".pdf")).pages[0]
            self.assertIn("Example product", page.extract_text())
            self.assertIn("Body marker", page.extract_text())
            self.assertEqual(len(page.images), 0)

    def test_automatic_header_and_no_html_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.md"
            p.write_text("# Content\n\n<script>alert(1)</script>", encoding="utf-8")
            html = render_html(p, template="granulex")
            self.assertEqual(html.count('class="brand-logo"'), 1)
            self.assertNotIn("<script>", html)
            self.assertNotIn('class="brand-logo"', render_html(p))

    def test_legacy_header_stray_quote(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "legacy.md"
            p.write_text(HEADER.replace('Z"/>', 'Z"  "/>') + "# Body", encoding="utf-8")
            html = render_html(p, template="granulex")
            self.assertEqual(html.count('class="brand-logo"'), 1)
            self.assertIn("Example product", html)

    def test_svg_rejects_external_and_active_content(self):
        for bad in ('<script/>', '<image href="https://example.com/logo.png"/>',
                    '<path d="M0 0" onload="x"/>', '<path fill="url(https://example.com/x)"/>'):
            with self.assertRaises(ValueError):
                safe_svg('<svg xmlns="http://www.w3.org/2000/svg">' + bad + '</svg>')
