import unittest
from md_to_pdf.ui_skin import ASSETS, vector_image

class ArtworkTests(unittest.TestCase):
    def test_vector_artwork_is_packaged_and_rendered(self):
        for name,size in (("welcome.svg",(1920,1080)),("toolbar.svg",(1920,96))):
            self.assertTrue((ASSETS/name).is_file())
            img=vector_image(name,*size)
            self.assertEqual(img.size,size)
            self.assertTrue(any(lo!=hi for lo,hi in img.getextrema()))
