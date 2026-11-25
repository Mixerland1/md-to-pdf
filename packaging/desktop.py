"""Frozen desktop entry point; smoke-test mode does not open a window."""
import sys
import os
from pathlib import Path

if getattr(sys, "frozen", False) and os.name == "nt":
    native = Path(sys._MEIPASS) / "native"
    os.environ["WEASYPRINT_DLL_DIRECTORIES"] = str(native)
    os.environ["PATH"] = str(native) + os.pathsep + os.environ.get("PATH", "")
    dll_handle = os.add_dll_directory(str(native)) if os.name == "nt" else None

if len(sys.argv) == 4 and sys.argv[1] in ("--smoke-test", "--brand-smoke-test"):
    from md_to_pdf.cli import convert
    convert(Path(sys.argv[2]), Path(sys.argv[3]), template="granulex" if sys.argv[1] == "--brand-smoke-test" else "business")
else:
    from md_to_pdf.gui import main
    main()
