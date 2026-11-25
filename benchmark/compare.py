"""Inspect PDFs without assuming either renderer is the reference."""
import json
import platform
import sys
from pathlib import Path
from pypdf import PdfReader

root = Path(sys.argv[1])
expected = json.loads((root/"expected.json").read_text(encoding="utf-8"))
result = {"environment": platform.platform(), "tools": {}}
for name in ("md","vscode"):
    folder = root/name
    timing = folder/"timings.json"
    result["tools"][name] = {"timings": json.loads(timing.read_text(encoding="utf-8")) if timing.exists() else None, "documents": {}}
    for case, markers in expected.items():
        pdf = folder/(case+".pdf")
        if not pdf.exists():
            result["tools"][name]["documents"][case] = {"error": "missing PDF"}
            continue
        reader = PdfReader(pdf)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        anns = [a.get_object() for page in reader.pages for a in page.get("/Annots", [])]
        result["tools"][name]["documents"][case] = {
            "pages": len(reader.pages), "bytes": pdf.stat().st_size,
            "markers": {m: m in text for m in markers},
            "external_link": any(a.get("/A",{}).get("/URI")=="https://example.com" for a in anns),
            "internal_link": any("/Dest" in a or a.get("/A",{}).get("/S")=="/GoTo" for a in anns),
            "raster_images": sum(len(p.images) for p in reader.pages),
        }
(root/"result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
