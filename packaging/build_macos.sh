#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
arch="$(uname -m)"
case "$arch" in arm64|x86_64) ;; *) exit 1;; esac
brew install pango
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix)/lib"
python scripts/fetch_fonts.py
python -m pip install '.[build,test]'
python -m unittest discover -s tests -v
set --
for lib in libgobject-2.0.0.dylib libpango-1.0.0.dylib libpangoft2-1.0.0.dylib libharfbuzz.0.dylib libharfbuzz-subset.0.dylib libfontconfig.1.dylib; do
    path="$(brew --prefix)/lib/$lib"
    test -f "$path"
    set -- "$@" --add-binary "$path:."
done
python -m PyInstaller --noconfirm --clean --onedir --windowed --name MD-to-PDF \
    --osx-bundle-identifier org.md-to-pdf.desktop --target-architecture "$arch" \
    --runtime-hook packaging/macos_native_hook.py \
    --collect-all md_to_pdf --collect-all pypdfium2 --collect-all pypdfium2_raw --collect-all weasyprint --collect-all tkinterdnd2 \
    --collect-all mistune --collect-all mammoth --collect-all bleach --collect-all openpyxl --collect-all xlrd \
    "$@" packaging/desktop.py
app="$PWD/dist/MD-to-PDF.app"
test -d "$app"
stage="$PWD/dist/macos-distribution"
mkdir -p "$stage/native-licenses" "$stage/python-licenses"
cp LICENSE README.md "$stage/"
cp -R docs "$stage/"
cp src/md_to_pdf/fonts/*-OFL.txt "$stage/"
for formula in pango $(brew deps --installed pango); do
    formula_path="$(brew --prefix "$formula")"
    mkdir -p "$stage/native-licenses/$formula"
    find -L "$formula_path/" -maxdepth 2 -type f \( -iname 'license*' -o -iname 'copying*' -o -iname 'notice*' \) -exec cp '{}' "$stage/native-licenses/$formula/" \;
done
python -m pip freeze > "$stage/python-dependencies.txt"
python - "$stage/python-licenses" <<'PY'
import importlib.metadata as m, pathlib, shutil, sys
target = pathlib.Path(sys.argv[1])
for d in m.distributions():
    for f in d.files or []:
        if ".dist-info/" in str(f) and ("license" in str(f).lower() or f.name.lower().startswith(("copying","notice"))):
            src = d.locate_file(f)
            if src.is_file():
                dest = target / str(f)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
PY
unset DYLD_FALLBACK_LIBRARY_PATH DYLD_LIBRARY_PATH
python packaging/check_macos_links.py "$app"
exe="$app/Contents/MacOS/MD-to-PDF"
"$exe" --smoke-test "$PWD/examples/example.md" "$PWD/mac-smoke.pdf"
"$exe" --brand-smoke-test "$PWD/examples/granulex-style-check.md" "$PWD/mac-brand.pdf"
python packaging/check_smoke.py mac-smoke.pdf mac-brand.pdf
codesign --verify --deep --strict "$app"
ditto "$app" "$stage/MD-to-PDF.app"
ditto -c -k --sequesterRsrc --keepParent "$stage" "MD-to-PDF-macOS-$arch.zip"
