import base64
from io import BytesIO
import tempfile
import unittest
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from PIL import Image
from pypdf import PdfReader

from md_to_pdf.cli import main, render_html, convert
from md_to_pdf.batch import collect_sources

class InputTests(unittest.TestCase):
    def test_txt_plain_and_utf16(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "text.txt"
            p.write_text("Кириллица\n<script>evil</script>\n# not markdown", encoding="utf-16")
            h = render_html(p)
            self.assertIn("Кириллица\n&lt;script&gt;", h)
            self.assertIn("# not markdown", h)
            self.assertNotIn("<script>", h)
            convert(p, p.with_suffix(".pdf"))
            self.assertIn("Кириллица", PdfReader(p.with_suffix(".pdf")).pages[0].extract_text())

    def test_docx_semantic_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "word.docx"
            d = Document()
            d.add_heading("Word heading", level=1)
            para = d.add_paragraph()
            para.add_run("Bold marker").bold = True
            d.add_paragraph("List item", style="List Bullet")
            d.add_table(rows=1, cols=1).cell(0,0).text = "Table marker"
            for url in ("https://example.com", "javascript:alert(1)"):
                link = OxmlElement("w:hyperlink")
                link.set(qn("r:id"), para.part.relate_to(url, RT.HYPERLINK, is_external=True))
                run = OxmlElement("w:r"); txt = OxmlElement("w:t")
                txt.text = "Link marker"; run.append(txt); link.append(run); para._p.append(link)
            image = BytesIO()
            Image.new("RGB", (20,20), "red").save(image, "PNG"); image.seek(0)
            d.add_picture(image)
            d.save(p)
            html = render_html(p, template="granulex")
            for token in ("<h1>Word heading</h1>", "<strong>Bold marker</strong>", "<li>List item</li>", "Table marker", 'href="https://example.com"', "data:image/png;base64,"):
                self.assertIn(token, html)
            self.assertNotIn('href="javascript:', html)
            convert(p, p.with_suffix(".pdf"), template="granulex")
            pdf = PdfReader(p.with_suffix(".pdf"))
            self.assertIn("Word heading", pdf.pages[0].extract_text())
            self.assertGreater(len(pdf.pages[0].images), 0)

    def test_mixed_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "a.md").write_text("# Markdown", encoding="utf-8")
            (root / "b.txt").write_text("Text", encoding="utf-8")
            d = Document(); d.add_paragraph("Word"); d.save(root / "c.docx")
            self.assertEqual(len(collect_sources([root])), 3)
            self.assertEqual(main([str(root), "--template", "granulex"]), 0)
            self.assertEqual(len(list(root.glob("*.pdf"))), 3)
