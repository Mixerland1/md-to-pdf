"""Embed packaged fonts in generated HTML; no runtime font downloads."""
from pathlib import Path
from base64 import b64encode

ROOT = Path(__file__).with_name("fonts")

def bundled_font_css():
    chunks = []
    for family, filename, weights in (
        ("Montserrat", "Montserrat.ttf", "100 900"),
        ("Roboto Mono", "RobotoMono.ttf", "100 700"),
    ):
        path = ROOT / filename
        if path.is_file():
            data = b64encode(path.read_bytes()).decode("ascii")
            chunks.append(f'@font-face {{ font-family:"{family}"; font-weight:{weights}; '
                          f'font-style:normal; src:url("data:font/ttf;base64,{data}") format("truetype"); }}')
    return "\n".join(chunks)
