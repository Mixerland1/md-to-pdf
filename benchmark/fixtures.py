"""Generate identical public synthetic fixtures for each converter."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw
import json

root = Path(sys.argv[1])
# Generate a real, visible local image (no opaque base64 fixture).
image = Image.new("RGB", (480, 100), "white")
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((8, 8, 220, 92), radius=10, fill="#dbe9f1", outline="#17344a", width=2)
draw.rounded_rectangle((260, 8, 472, 92), radius=10, fill="#e9efe0", outline="#35542e", width=2)
draw.text((55, 40), "Markdown", fill="#17344a")
draw.text((325, 40), "PDF", fill="#35542e")
draw.line((222, 50, 258, 50), fill="#17344a", width=3)
cases = {
    "guide": "# Руководство\n\nMARKER-GUIDE\n\n[External](https://example.com) · [Jump](#table)\n\n## Table\n\n| Key | Value |\n|---|---|\n| Alpha | Бета |\n\n![Image](pixel.png)\n\n```python\nprint('MARKER-CODE')\n```\n",
    "long": "# Long document\n\nMARKER-START\n\n" + "\n\n".join("## Section "+str(i)+"\n\n" + ("Readable paragraph. " * 18) for i in range(1,31))+"\n\nMARKER-END\n",
    "unicode": "# Unicode\n\nMARKER-UNICODE\n\nКириллица — русский текст. English. Ελληνικά.\n\n- First\n- Second\n",
}
expected = {"guide": ["MARKER-GUIDE","MARKER-CODE","Бета"], "long":["MARKER-START","MARKER-END"], "unicode":["MARKER-UNICODE","Кириллица"]}
for name in ("md","vscode"):
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    image.save(folder/"pixel.png")
    for case, data in cases.items():
        (folder/(case+".md")).write_text(data, encoding="utf-8")
(root/"expected.json").write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")
