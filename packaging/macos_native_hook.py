"""Resolve CFFI native libraries inside the frozen macOS application."""
import sys
from pathlib import Path
import cffi
if getattr(sys, "frozen", False) and sys.platform == "darwin":
    root = Path(sys._MEIPASS)
    original = cffi.FFI.dlopen
    aliases = {
        "gobject-2.0": "libgobject-2.0.0.dylib",
        "pango-1.0": "libpango-1.0.0.dylib",
        "pangoft2-1.0": "libpangoft2-1.0.0.dylib",
        "harfbuzz-subset": "libharfbuzz-subset.0.dylib",
        "harfbuzz": "libharfbuzz.0.dylib",
        "fontconfig": "libfontconfig.1.dylib",
    }
    def bundled_dlopen(self, name, *args, **kwargs):
        if isinstance(name, str):
            for prefix, filename in aliases.items():
                if name.startswith((prefix, "lib" + prefix)):
                    candidate = root / filename
                    if candidate.is_file():
                        return original(self, str(candidate), *args, **kwargs)
        return original(self, name, *args, **kwargs)
    cffi.FFI.dlopen = bundled_dlopen
