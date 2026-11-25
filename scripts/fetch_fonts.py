"""Fetch pinned, OFL-licensed public font assets for offline PDF generation."""
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import quote
import hashlib

COMMIT = "6ebe737e44fd64ee736bbc6feed6136a6dbfd222"
ASSETS = (
    ("ofl/montserrat/Montserrat[wght].ttf", "Montserrat.ttf", "c97aca18592834d8706549c279cb8d5ac5d85f69"),
    ("ofl/robotomono/RobotoMono[wght].ttf", "RobotoMono.ttf", "f21d1d716bce3cc756bc618d32be71ce6f733f81"),
    ("ofl/montserrat/OFL.txt", "Montserrat-OFL.txt", "fe576a2ee1f96353b05d030c0b7620d525cc53a8"),
    ("ofl/robotomono/OFL.txt", "RobotoMono-OFL.txt", "8e7df338d36eb52c49548ecc58afcb7eb3f73898"),
)
DEST = Path(__file__).resolve().parents[1] / "src/md_to_pdf/fonts"

def git_blob_hash(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for source, filename, expected in ASSETS:
        target = DEST / filename
        if target.exists() and git_blob_hash(target.read_bytes()) == expected:
            continue
        url = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}/{quote(source)}"
        with urlopen(url, timeout=60) as response:
            data = response.read(5_000_001)
        if len(data) > 5_000_000 or git_blob_hash(data) != expected:
            raise RuntimeError(f"Unexpected asset hash: {filename}")
        target.write_bytes(data)
        print(f"Verified {filename}")

if __name__ == "__main__":
    main()
