import tempfile
import unittest
from pathlib import Path
from lxml import html
from md_to_pdf.cli import render_html, layout_pdf
from md_to_pdf.profiles import phantom_profile
from md_to_pdf.workspace import Workspace
from md_to_pdf.ui_skin import vector_image

class PhantomTests(unittest.TestCase):
    def test_cover_and_toc(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/"Guide.md"
            source.write_text("""<section class="title-page">
<div class="title-main">Phantom Cross 5.5.2</div>
<div class="title-sub">Установка</div>
<div class="title-footer"><img class="title-logo" src="images/logo.svg" alt="Логотип МДИС">Москва, 2026</div>
</section>

## Оглавление

| Раздел | Стр. |
| --- | ---: |
| <a id="toc-001"></a>[Введение](#sec-001) | 7 |

# <a id="sec-001"></a>[Введение](#toc-001)

Текст.

<img src="images/01.png" alt="Example" style="width:600px">
""",encoding="utf-8")
            markup=render_html(source,template="phantom")
            tree=html.document_fromstring(markup)
            self.assertFalse(tree.xpath('//section[@class="title-page"]'))
            self.assertEqual(tree.xpath('//div[@class="header-left"]/span/text()'),["Phantom Cross"])
            self.assertEqual(tree.xpath('//span[@class="header-right-title"]/text()'),["Версия 5.5.2"])
            self.assertTrue(tree.xpath('//img[@class="brand-logo"]/@src')[0].startswith("data:image/svg+xml;base64,"))
            self.assertEqual(tree.xpath('//h1[@class="phantom-document-heading"]/text()'),["Установка"])
            self.assertTrue(tree.xpath('//a[@class="phantom-toc-page"][@href="#sec-001"]'))
            self.assertTrue(tree.xpath('//img[@src="images/01.png"]'))
            document=layout_pdf(markup,source)
            self.assertIn("toc-001",document.pages[0].anchors)
            self.assertEqual(len(document.pages),2)
            ws=Workspace(source,template="phantom")
            self.assertEqual(ws.model.header_fields()[1],"Версия 5.5.2")
            images=Path(d)/"images"
            images.mkdir()
            (images/"logo.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>',encoding="utf-8")
            local=html.document_fromstring(render_html(source,template="phantom"))
            self.assertEqual(local.xpath('//img[@class="brand-logo"]/@src'),
                             [(images/"logo.svg").resolve().as_uri()])
            self.assertEqual(phantom_profile().base,"phantom")

    def test_icon_transparency(self):
        im=vector_image("format-painter.svg",96,96,True)
        self.assertEqual(im.mode,"RGBA")
        self.assertEqual(im.getpixel((0,0))[3],0)
        self.assertGreater(im.getchannel("A").getextrema()[1],0)
