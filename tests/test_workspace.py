import tempfile
import unittest
from pathlib import Path
import pypdfium2 as pdfium
from md_to_pdf.workspace import Workspace,render_snapshot,export_bytes
from md_to_pdf.page_preview import map_glyphs

class WorkspaceTests(unittest.TestCase):
    def test_real_preview_selection_and_exact_export(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"guide.md"
            p.write_text("# Руководство\n\nAlpha linked text.\n\n## Second\n\nMore text.",encoding="utf-8")
            w=Workspace(p,template="granulex")
            data,ids,texts,locations=render_snapshot(w.snapshot())
            with pdfium.PdfDocument(data) as document:
                glyphs,mapping=map_glyphs(document,ids,texts,locations)
                self.assertTrue(any(block==1 for block,offset in mapping.values()))
            w.apply("h2",[(1,0,5)])
            w.preset(template="business")
            self.assertEqual(w.model.blocks()[1].role,"h2")
            w.undo()
            self.assertEqual(w.model.blocks()[1].role,"p")
            w.redo()
            self.assertEqual(w.model.blocks()[1].role,"h2")
            data=render_snapshot(w.snapshot())[0]
            target=export_bytes(p,data)
            self.assertEqual(target.read_bytes(),data)
            self.assertIn("Alpha linked text.",p.read_text(encoding="utf-8"))
