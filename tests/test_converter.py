import tempfile
import unittest
from pathlib import Path
from pypdf import PdfReader
from md_to_pdf.cli import convert, render_html

class ConverterTests(unittest.TestCase):
    def test_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'Тест.md'
            source.write_text('# Заголовок\n\n[Link](https://example.com) [Внутри](#заголовок)\n\n| A | B |\n|---|---|\n| Один | Два |\n', encoding='utf-8')
            target = root / 'result.pdf'
            convert(source, target, document_date='01.01.2026')
            reader = PdfReader(target)
            page = reader.pages[0]
            self.assertAlmostEqual(float(page.mediabox.width), 595.28, places=1)
            self.assertIn('Заголовок', page.extract_text())
            self.assertIn('Стр. 1', page.extract_text())
            anns = [x.get_object() for x in page.get('/Annots', [])]
            self.assertTrue(any(x.get('/A', {}).get('/URI') == 'https://example.com' for x in anns))
            self.assertTrue(any('/Dest' in x for x in anns))
    def test_html_escaping(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'test.md'
            source.write_text('# Title\n\n<script>alert(1)</script>', encoding='utf-8')
            self.assertNotIn('<script>', render_html(source))
    def test_multipage(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'long.md'
            source.write_text('# Title\n\n' + ('Paragraph of text. ' * 15 + '\n\n') * 80, encoding='utf-8')
            target = source.with_suffix('.pdf')
            convert(source, target)
            pages = PdfReader(target).pages
            self.assertGreater(len(pages), 1)
            self.assertIn('Стр. 2', pages[1].extract_text())
