import unittest
from md_to_pdf.ui_skin import ASSETS, vector_image

class ArtworkTests(unittest.TestCase):
    def test_vector_artwork_is_packaged_and_rendered(self):
        for name,size in (("welcome.svg",(1920,1080)),("toolbar.svg",(1920,96))):
            self.assertTrue((ASSETS/name).is_file())
            img=vector_image(name,*size)
            self.assertEqual(img.size,size)
            self.assertTrue(any(lo!=hi for lo,hi in img.getextrema()))

    def test_rounded_cards_have_transparent_corners(self):
        from md_to_pdf.ui_skin import rounded_art
        for shadow in (False,True):
            img=rounded_art(500,300,18,shadow)
            self.assertEqual(img.size,(500,300))
            self.assertEqual(img.mode,"RGBA")
            self.assertLess(img.getpixel((0,0))[3],20)
            self.assertEqual(img.getpixel((250,150)),(255,255,255,255))
