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
