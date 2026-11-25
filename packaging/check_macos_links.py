"""Reject absolute third-party dylib references in portable bundles."""
import pathlib
import subprocess
import sys
app = pathlib.Path(sys.argv[1])
bad = []
for path in app.rglob("*"):
    if path.is_symlink() or not path.is_file():
        continue
    with path.open("rb") as f:
        magic = f.read(4)
    if magic not in (b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xce", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
        continue
    result = subprocess.run(["otool", "-L", str(path)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    for line in result.stdout.splitlines()[1:]:
        if " (compatibility version " not in line:
            continue
        dep = line.strip().split(" (compatibility version ", 1)[0]
        if dep.startswith("/") and not dep.startswith(("/usr/lib/", "/System/Library/")):
            bad.append((str(path.relative_to(app)), dep))
if bad:
    raise SystemExit("Non-portable dylib dependencies:\n" + "\n".join(f"{p}: {d}" for p,d in bad))
print("No absolute third-party dylib paths")
