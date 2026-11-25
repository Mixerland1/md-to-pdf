"""Generate identical public synthetic fixtures for each converter."""
import sys
from pathlib import Path
import base64
import json

root = Path(sys.argv[1])
# A small embedded PNG used as a local relative file.
png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jA90AAAAASUVORK5CYII=")
cases = {
    "guide": "# Руководство\n\nMARKER-GUIDE\n\n[External](https://example.com) · [Jump](#table)\n\n## Table\n\n| Key | Value |\n|---|---|\n| Alpha | Бета |\n\n![Image](pixel.png)\n\n```python\nprint('MARKER-CODE')\n```\n",
    "long": "# Long document\n\nMARKER-START\n\n" + "\n\n".join("## Section "+str(i)+"\n\n" + ("Readable paragraph. " * 18) for i in range(1,31))+"\n\nMARKER-END\n",
    "unicode": "# Unicode\n\nMARKER-UNICODE\n\nКириллица — русский текст. English. Ελληνικά.\n\n- First\n- Second\n",
}
expected = {"guide": ["MARKER-GUIDE","MARKER-CODE","Бета"], "long":["MARKER-START","MARKER-END"], "unicode":["MARKER-UNICODE","Кириллица"]}
for name in ("md","vscode"):
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder/"pixel.png").write_bytes(png)
    for case, data in cases.items():
        (folder/(case+".md")).write_text(data, encoding="utf-8")
(root/"expected.json").write_text(json.dumps(expected, ensure_ascii=False), encoding="utf-8")
