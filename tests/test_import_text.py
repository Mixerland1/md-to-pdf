import unittest
import tempfile
from pathlib import Path
from docx import Document
from openpyxl import Workbook
from md_to_pdf.import_text import copy_document
from md_to_pdf.cli import convert

class ImportTextTests(unittest.TestCase):
    def test_word_and_excel(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            word=root/"sample.docx"
            doc=Document()
            doc.add_heading("Title",level=1)
            doc.add_paragraph("Hello")
            doc.add_table(rows=1,cols=2).rows[0].cells[0].text="Value"
            doc.save(word)
            original=word.read_bytes()
            value=copy_document(word)
            self.assertIn("# Title",value)
            self.assertIn("Hello",value)
            self.assertIn("Value",value)
            self.assertEqual(original,word.read_bytes())
            xlsx=root/"sample.xlsx"
            book=Workbook()
            sheet=book.active
            sheet.title="First"
            sheet.append(["Name","Count"])
            sheet.append(["A",17])
            book.create_sheet("Second").append(["B",23])
            book.save(xlsx)
            value=copy_document(xlsx)
            for expected in ("## First","## Second","| Name | Count |","| A | 17 |","| B | 23 |"):
                self.assertIn(expected,value)
    def test_pdf(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"source.md"
            p.write_text("# Imported text\n\nHello PDF",encoding="utf-8")
            out=p.with_suffix(".pdf")
            convert(p,out)
            original=out.read_bytes()
            self.assertIn("Hello PDF",copy_document(out))
            self.assertEqual(original,out.read_bytes())
    def test_csv(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"source.csv"
            p.write_text("Name;Count\nA;3\n",encoding="utf-8")
            self.assertIn("| A | 3 |",copy_document(p))
