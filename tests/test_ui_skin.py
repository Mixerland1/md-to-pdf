import unittest
import hashlib
from PIL import Image
from md_to_pdf.ui_skin import ASSETS

class ArtworkTests(unittest.TestCase):
    def test_selected_artwork_is_packaged(self):
        for name,size,digest in (
            ("welcome.webp",(640,360),"cae90318390c26ac5887297f1d07e4c5d2b59a5b991df08fbc609c7893ce0a9f"),
            ("toolbar.webp",(960,48),"ed08a917e893df75ef3e98757c6919147355fac2fdd0f443f9bb2e733bc21f98"),
        ):
            path=ASSETS/name
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest)
            with Image.open(path) as img:
                self.assertEqual(img.size,size)
                img.load()
