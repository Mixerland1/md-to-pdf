import tempfile
import unittest
from pathlib import Path
from dataclasses import replace
from PIL import Image
from pypdf import PdfReader
from md_to_pdf.profiles import Profile, granulex_profile, import_logo, load_profile, save_profile
from md_to_pdf.cli import render_html, convert

class ProfileTests(unittest.TestCase):
    def test_roundtrip_and_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            p=replace(granulex_profile(),name="Example",product="Example Corp",footer="Example footer",accent="#123456")
            save_profile(p,root/"style.json")
            q=load_profile(root/"style.json")
            self.assertEqual(p,q)
            md=root/"guide.md"; md.write_text("# Content",encoding="utf-8")
            h=render_html(md,profile=q)
            self.assertIn("#123456",h)
            self.assertIn("Example Corp",h)
            self.assertEqual(h.count('class="brand-logo"'),1)
            convert(md,root/"guide.pdf",profile=q)
            text=PdfReader(root/"guide.pdf").pages[0].extract_text()
            self.assertIn("Example Corp",text)
            self.assertIn("Example footer",text)

    def test_raster_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            logo=root/"logo.png"; Image.new("RGB",(50,30),"red").save(logo)
            kind,data=import_logo(logo)
            profile=replace(Profile(),logo_kind=kind,logo_data=data)
            self.assertTrue(profile.logo_uri().startswith("data:image/svg+xml;base64,"))
            md=root/"guide.md"; md.write_text("# Content",encoding="utf-8")
            convert(md,root/"guide.pdf",profile=profile)
            self.assertGreater(len(PdfReader(root/"guide.pdf").pages[0].images),0)

    def test_validation(self):
        for p in (replace(Profile(),font='x";}'),replace(Profile(),accent="url(x)"),
                  replace(Profile(),margin_top=-5),replace(Profile(),body_pt=float("nan"))):
            with self.assertRaises(ValueError):
                p.validate()
