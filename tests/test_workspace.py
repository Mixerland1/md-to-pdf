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

    def test_selection_roles_typography_and_save(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"guide.md"
            p.write_text("# Heading\n\nNormal text.",encoding="utf-8")
            w=Workspace(p,template="granulex")
            self.assertEqual(w.model.selection_role([(0,0,3)]),"h1")
            self.assertEqual(w.model.selection_role([(0,0,3),(1,0,3)]),"mixed")
            w.apply(["h2","font:Arial","size:14"],[(1,0,6)])
            self.assertEqual(w.model.selection_role([(1,0,6)]),"h2")
            self.assertIn('font-size: 14pt',w.model.html())
            self.assertTrue(w.undo())
            self.assertEqual(w.model.selection_role([(1,0,6)]),"normal")
            w.redo()
            w.save("Granulex")
            restored=Workspace(p,template="technical")
            self.assertEqual(restored.restore(),"Granulex")
            self.assertEqual(restored.model.selection_role([(1,0,6)]),"h2")
            self.assertIn('font-size: 14pt',restored.model.html())
            self.assertEqual(p.read_text(encoding="utf-8"),"# Heading\n\nNormal text.")
            p.write_text("Changed",encoding="utf-8")
            with self.assertRaises(ValueError):
                Workspace(p,template="granulex").restore()

    def test_clipboard_save_and_export(self):
        from md_to_pdf.workspace import write_pdf_bytes
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            w=Workspace.from_clipboard("# Заголовок\n\nВставленный **текст**.",root,template="granulex")
            self.assertEqual(w.model.blocks()[0].text,"Заголовок")
            self.assertEqual(w.model.blocks()[1].text,"Вставленный текст.")
            w.apply("h2",[(1,0,4)])
            data=render_snapshot(w.snapshot())[0]
            self.assertEqual(write_pdf_bytes(root/"pasted.pdf",data).read_bytes(),data)
            target=root/"saved.md"
            w.save_pasted(target,"Granulex")
            self.assertEqual(target.read_text(encoding="utf-8"),"# Заголовок\n\nВставленный **текст**.")
            reopened=Workspace(target,template="technical")
            self.assertEqual(reopened.restore(),"Granulex")
            self.assertEqual(reopened.model.blocks()[1].role,"h2")
            with self.assertRaises(FileExistsError):
                w.save_pasted(target,"Granulex")
            with self.assertRaises(ValueError):
                Workspace.from_clipboard(" \n",root,template="technical")
