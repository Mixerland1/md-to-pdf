import unittest
from lxml import html
from md_to_pdf.editor_model import DocumentEditor

SOURCE = '<html><head><title>Sample</title></head><body><main><div class="doc-header"><p>Brand</p></div><h1>Title</h1><p>Alpha <a href="https://example.com">linked <em>words</em></a> tail.</p><table><tr><td>Cell</td></tr></table><ul><li>List</li></ul><p><img src="media/a.png">Picture</p></main></body></html>'

class EditorTests(unittest.TestCase):
    def test_exact_range_across_links_and_emphasis(self):
        editor = DocumentEditor(SOURCE)
        original = editor.html()
        editor.apply("accent", [(1, 4, 16)])
        doc = html.document_fromstring(editor.html())
        self.assertEqual(doc.xpath("//a/@href"), ["https://example.com"])
        self.assertEqual(doc.xpath("//main/p[1]")[0].text_content(), "Alpha linked words tail.")
        spans = doc.xpath('//span[@class="brand-accent"]')
        self.assertEqual("".join(s.text_content() for s in spans), "a linked wor")
        self.assertTrue(editor.undo())
        self.assertEqual(editor.html(), original)
        self.assertTrue(editor.redo())
        self.assertIn("brand-accent", editor.html())

    def test_block_roles_and_protection(self):
        editor = DocumentEditor(SOURCE)
        self.assertEqual(editor.blocks()[0].text, "Title")
        editor.apply("h2", [(1, 1, 2)])
        self.assertIn("<h2>Alpha", editor.html())
        self.assertEqual(editor.blocks()[1].text, "Alpha linked words tail.")
        with self.assertRaises(ValueError):
            editor.apply("h1", [(2, 0, 2)])
        self.assertIn("<td>Cell</td>", editor.html())
        self.assertIn("<li>List</li>", editor.html())
        self.assertIn('src="media/a.png"', editor.html())

    def test_selection_is_not_source_reconstruction(self):
        editor = DocumentEditor(SOURCE)
        editor.apply("warning", [(0, 0, 2), (1, 0, 2)])
        doc = html.document_fromstring(editor.html())
        self.assertEqual(len(doc.xpath('//p[@class="editor-warning"]')), 2)
        self.assertEqual(doc.xpath("//a/@href"), ["https://example.com"])
        self.assertEqual(doc.xpath("//img/@src"), ["media/a.png"])
        self.assertIn("Brand", doc.text_content())

    def test_inline_runs_and_pdf_pipeline(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from md_to_pdf.cli import render_html, write_rendered_pdf
        from pypdf import PdfReader
        with TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/"sample.md"
            original = "# Heading\n\nAlpha [linked](https://example.com) tail.\n"
            source.write_text(original,encoding="utf-8")
            editor = DocumentEditor(render_html(source,template="granulex"))
            editor.apply("accent",[(1,6,12)])
            self.assertTrue(any(r[4] and r[0]=="linked" for r in editor.runs(1)))
            output = root/"edited.pdf"
            write_rendered_pdf(editor.html(),source,output)
            page = PdfReader(output).pages[0]
            self.assertIn("Alpha linked tail.",page.extract_text())
            self.assertTrue(any(a.get_object().get("/A",{}).get("/URI")=="https://example.com" for a in page["/Annots"]))
            self.assertEqual(source.read_text(encoding="utf-8"),original)

    def test_header_edit_undo(self):
        from md_to_pdf.branding import Header, render_header
        model=DocumentEditor("<html><head></head><body><main>"+render_header(Header())+"<p>Body</p></main></body></html>")
        self.assertEqual(model.header_fields(),("Granulex","",""))
        model.set_header("Other & Co","Версия 2.0","Последнее обновление: 2026")
        self.assertEqual(model.header_fields()[0],"Other & Co")
        self.assertIn("Other &amp; Co",model.html())
        self.assertTrue(model.undo())
        self.assertEqual(model.header_fields(),("Granulex","",""))
