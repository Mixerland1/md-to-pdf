"""Validate regular and branded PDFs produced by frozen executable."""
from pypdf import PdfReader
import sys
regular, brand = (PdfReader(p) for p in sys.argv[1:])
assert "Руководство" in "".join(p.extract_text() for p in regular.pages)
text = "".join(p.extract_text() for p in brand.pages)
assert "Granulex Example" in text and "Руководство" in text
assert "Версия 1.2.3" in text and "ноябрь 2026" in text
assert text.count("1.2.3") == 1 and text.count("Granulex Example") == 1
fonts = []
for p in brand.pages:
    for f in p["/Resources"]["/Font"].get_object().values():
        fonts.append(str(f.get_object().get("/BaseFont")))
assert any("Montserrat" in n for n in fonts), fonts
assert any("RobotoMono" in n.replace("-", "") for n in fonts), fonts
print("Frozen PDF content and brand font checks passed")
