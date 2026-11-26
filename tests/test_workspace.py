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

    def test_list_style_real_pdf_and_saved_project(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"list.md"
            p.write_text("# Title\n\n4. First\n5. Second\n6. Third\n",encoding="utf-8")
            w=Workspace(p,template="granulex")
            self.assertEqual(w.model.selection_role([(2,0,3)]),"numbered")
            data,ids,texts,locations=render_snapshot(w.snapshot())
            with pdfium.PdfDocument(data) as doc:
                _,mapping=map_glyphs(doc,ids,texts,locations)
                self.assertTrue(any(i==2 for i,_ in mapping.values()))
            w.apply("h2",[(2,0,3)])
            data,ids,texts,locations=render_snapshot(w.snapshot())
            with pdfium.PdfDocument(data) as doc:
                _,mapping=map_glyphs(doc,ids,texts,locations)
                self.assertTrue(any(i==2 for i,_ in mapping.values()))
            self.assertEqual(w.model.selection_role([(2,0,3)]),"h2")
            w.save("Granulex")
            restored=Workspace(p,template="granulex")
            restored.restore()
            self.assertEqual(restored.model.selection_role([(2,0,3)]),"h2")

    def test_metadata_roles_and_table_parameters(self):
        import json
        from lxml import html
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"metadata.md"
            p.write_text("# Title\n\n3.1.0\n\nноябрь 2026\n\n| Name | Value |\n| --- | --- |\n| A | B |\n",encoding="utf-8")
            w=Workspace(p,template="granulex")
            version=w.apply("meta-version",[(1,0,5)])
            self.assertEqual(w.model.selection_role(version),"meta-version")
            updated=w.apply("meta-updated",[(1,0,len("ноябрь 2026"))])
            self.assertEqual(w.model.selection_role(updated),"meta-updated")
            self.assertEqual(w.model.header_fields()[1:],("Версия 3.1.0","Последнее обновление: ноябрь 2026"))
            self.assertEqual(w.model.html().count("3.1.0"),1)
            self.assertEqual(w.model.selection_role([(1,0,4)]),"table-heading")
            w.apply("table-cell",[(1,0,4)])
            self.assertEqual(w.model.selection_role([(1,0,4)]),"table-cell")
            settings={"width":70,"align":"right","grid":"show"}
            w.apply("table-settings:"+json.dumps(settings),[(1,0,4)])
            self.assertEqual(w.model.table_settings([(1,0,4)]),settings)
            doc=html.document_fromstring(w.model.html())
            self.assertEqual(len(doc.xpath("//table//tr")),2)
            self.assertIn("width: 70%",doc.xpath("//table/@style")[0])
            data,ids,texts,locations=render_snapshot(w.snapshot())
            with pdfium.PdfDocument(data) as pdf:
                glyphs,mapping=map_glyphs(pdf,ids,texts,locations)
                self.assertTrue(any(w.model.blocks()[i].role=="meta-version" for i,_ in mapping.values()))
                self.assertTrue(any(w.model.blocks()[i].role=="meta-updated" for i,_ in mapping.values()))
            w.save("Granulex")
            reopened=Workspace(p,template="granulex")
            reopened.restore()
            self.assertEqual(reopened.model.header_fields()[1:],w.model.header_fields()[1:])
            self.assertEqual(reopened.model.table_settings([(1,0,4)]),settings)
            self.assertEqual(reopened.skipped,0)

    def test_table_row_roles_and_preview_mapping(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"table.md"
            p.write_text("# Title\n\n| Parameter | Value |\n| --- | --- |\n| A very long label that wraps in a narrow column | Example text |\n| Last | End |\n",encoding="utf-8")
            w=Workspace(p,template="granulex")
            data,ids,texts,locations=render_snapshot(w.snapshot())
            with pdfium.PdfDocument(data) as doc:
                _,mapping=map_glyphs(doc,ids,texts,locations)
                self.assertTrue(any(i==3 for i,_ in mapping.values()))
            w.apply("table-row-heading",[(3,0,4)])
            self.assertEqual(w.model.selection_role([(3,0,4),(4,0,4)]),"table-heading")
            w.apply("table-cell",[(3,0,4)])
            self.assertEqual(w.model.selection_role([(3,0,4)]),"table-cell")
            self.assertEqual(w.model.selection_role([(4,0,4)]),"table-heading")
            w.undo()
            self.assertEqual(w.model.selection_role([(3,0,4)]),"table-heading")
