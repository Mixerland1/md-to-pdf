import tempfile
import unittest
from pathlib import Path
from pypdf import PdfReader
from md_to_pdf.branding import extract_document_header
from md_to_pdf.cli import render_html, convert
from md_to_pdf.profiles import Profile

SAMPLE = "# Руководство пользователя\n\nExample Generator 3.1.0\nПоследнее обновление: август 2025\n\n## Введение\n\nТекст документа.\n"

class MetadataTests(unittest.TestCase):
    def test_exact_metadata_pattern(self):
        body, header = extract_document_header(SAMPLE)
        self.assertEqual(header.name, "Example Generator")
        self.assertEqual(header.version, "Версия 3.1.0")
        self.assertEqual(header.updated, "Последнее обновление: август 2025")
        self.assertEqual(body, "# Руководство пользователя\n\n## Введение\n\nТекст документа.\n")
        self.assertEqual(extract_document_header(SAMPLE.replace("\n", "\r\n"))[1], header)

    def test_only_complete_leading_block(self):
        for text in (
            "# Heading\n\nExample Generator 3.1.0\n\nNormal prose.",
            "# Heading\n\nExample Generator 3.1.0\nПоследнее обновление: август 2025\nStill the same paragraph.",
            "# Heading\n\nNormal introduction.\n\nExample Generator 3.1.0\nПоследнее обновление: август 2025",
            "# Heading\n\n3.1.0\nПоследнее обновление: август 2025",
            "# Heading\n\n- Example Generator 3.1.0\nПоследнее обновление: август 2025",
        ):
            self.assertEqual(extract_document_header(text)[0], text)

    def test_html_and_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "guide.md"
            p.write_text(SAMPLE, encoding="utf-8")
            for options in ({"template":"granulex"}, {"profile":Profile()}):
                html = render_html(p, **options)
                self.assertIn('<span>Example Generator</span>', html)
                self.assertIn('class="header-right-title">Версия 3.1.0</span>', html)
                self.assertIn('class="header-right-update">Последнее обновление: август 2025</span>', html)
                self.assertNotIn("Example Generator 3.1.0", html)
                self.assertEqual(html.count("Последнее обновление: август 2025"), 1)
                self.assertLess(html.index('class="doc-header"'), html.index("<h1 id="))
                self.assertIn("Текст документа.", html)
                overridden = render_html(p, brand_name="Override", brand_version="9.0", brand_updated="2026", **options)
                self.assertIn("<span>Override</span>", overridden)
                self.assertIn("Версия 9.0", overridden)
                self.assertNotIn("Example Generator", overridden)
                self.assertNotIn("август 2025", overridden)
            plain = render_html(p, template="technical")
            self.assertIn("Example Generator 3.1.0", plain)
            convert(p, p.with_suffix(".pdf"), template="granulex")
            page = PdfReader(p.with_suffix(".pdf")).pages[0]
            text = page.extract_text()
            self.assertEqual(text.count("Example Generator"), 1)
            self.assertEqual(text.count("3.1.0"), 1)
            self.assertIn("август 2025", text)
            self.assertIn("Руководство пользователя", text)
            self.assertIn("Текст документа.", text)
