import json
import sys
import time
from pathlib import Path
from md_to_pdf.cli import convert
from md_to_pdf import __version__

folder = Path(sys.argv[1])
timings = {}
for p in sorted(folder.glob("*.md")):
    values = []
    for _ in range(3):
        t = time.perf_counter()
        convert(p, p.with_suffix(".pdf"))
        values.append(round((time.perf_counter()-t)*1000, 2))
    timings[p.stem] = values
(folder/"timings.json").write_text(json.dumps({"version":__version__, "milliseconds":timings}), encoding="utf-8")
