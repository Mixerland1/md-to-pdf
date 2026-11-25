import os
import tempfile
import unittest
from pathlib import Path
from pypdf import PdfReader
from md_to_pdf.font_assets import ROOT, bundled_font_css
from md_to_pdf.cli import convert

class FontTests(unittest.TestCase):
    def test_bundled_fonts(self):
        if not (ROOT / "Montserrat.ttf").is_file():
            if os.environ.get("CI"):
                self.fail("CI must provision bundled fonts")
            self.skipTest("Run scripts/fetch_fonts.py first")
        for name in ("Montserrat.ttf", "RobotoMono.ttf", "Montserrat-OFL.txt", "RobotoMono-OFL.txt"):
            self.assertTrue((ROOT / name).is_file(), name)
        self.assertIn("data:font/ttf;base64,", bundled_font_css())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            md = root / "sample.md"
            md.write_text("# Руководство\n\nПример текста **жирный** и \x60код\x60.", encoding="utf-8")
            convert(md, root / "sample.pdf", template="granulex")
            page = PdfReader(root / "sample.pdf").pages[0]
            fonts = page["/Resources"]["/Font"].get_object()
            names = [str(f.get_object().get("/BaseFont")) for f in fonts.values()]
            self.assertTrue(any("Montserrat" in n for n in names), names)
            self.assertTrue(any("RobotoMono" in n.replace("-", "") for n in names), names)
            self.assertIn("Руководство", page.extract_text())
