# MD to PDF

**Convert Markdown into professional PDF documents without VS Code.** Local desktop app and command-line converter. [Русская инструкция](#русская-инструкция).

## Windows — no Python required

1. Open [Releases](https://github.com/Mixerland1/md-to-pdf/releases).
2. Download `MD-to-PDF-Windows-x64.zip` from a published release.
3. Extract the entire archive (do not move the EXE away from its bundled libraries).
4. Double-click `MD-to-PDF.exe`.
5. Drop Markdown files or folders into the window, select a template and click **Convert to PDF**.

If no release is visible yet, the [Windows build workflow](https://github.com/Mixerland1/md-to-pdf/actions/workflows/windows.yml) has not completed and published a tested bundle. Use the source installation below in the meantime. The portable bundle is unsigned; check its SHA-256 against the release checksum. Windows x64 only.

### Templates

| Template | Intended use |
| --- | --- |
| Technical | User guides, manuals, knowledge bases |
| Business | Reports, proposals, business documents |
| Academic | Course materials, academic reports, long-form reading |

All templates use A4, running headers and numbered pages. Add your own trusted CSS to override styling.

### Desktop workflow

Add or drag multiple .md, .markdown or .mdown files, or whole folders. Enable Subfolders before adding a folder to search recursively. Choose an output folder or leave it blank to write each PDF next to its source. Existing PDFs are protected unless Overwrite is selected. Duplicate target names are reported rather than silently overwritten. Progress and conversion errors appear in the app. The interface uses English and Russian labels. A file picker remains available if native drag and drop is unavailable.

## Install from source — Windows, macOS, Linux

Requires Python 3.10+ and the native WeasyPrint libraries (Pango, etc.). Follow [WeasyPrint installation instructions](https://doc.courtbouillon.org/weasyprint/v68.0/first_steps.html). Windows source installs may require setting WEASYPRINT_DLL_DIRECTORIES to the MSYS2 UCRT64 bin path. Tk must also be installed for the desktop interface (on Debian/Ubuntu: python3-tk).

```sh
git clone https://github.com/Mixerland1/md-to-pdf.git
cd md-to-pdf
python -m pip install ".[gui]"
md-to-pdf-gui
```

For CLI only: `python -m pip install .`. On Windows use `py` instead of `python` if needed; if console scripts are not on PATH, use `python -m md_to_pdf.cli` and `python -m md_to_pdf.gui`.

### CLI examples

```sh
md-to-pdf document.md
md-to-pdf document.md -o result.pdf --template business
md-to-pdf file1.md file2.md --template academic
md-to-pdf docs --recursive --output-dir pdf
md-to-pdf docs --recursive --overwrite
md-to-pdf document.md --css custom.css --title "User guide"
md-to-pdf document.md --html-only
md-to-pdf --help
```

By default existing output is protected; use `--overwrite` to replace it. Use an output directory only when filenames are unique. For CLI, `--date` sets the footer date. `--allow-html` enables raw HTML for trusted files only.

## Русская инструкция

### Windows: запуск без Python и VS Code

1. Откройте [Releases](https://github.com/Mixerland1/md-to-pdf/releases).
2. Скачайте архив **MD-to-PDF-Windows-x64.zip** из опубликованного релиза.
3. Распакуйте архив целиком в удобную папку. Не переносите отдельно EXE из этой папки.
4. Запустите **MD-to-PDF.exe**.
5. Перетащите один или несколько Markdown-файлов или папку в окно программы.
6. Выберите шаблон: **technical** (инструкции), **business** (деловые документы) или **academic** (учебные и научные материалы).
7. При необходимости укажите папку сохранения или CSS. Нажмите **Convert to PDF / Конвертировать**.

Если папка сохранения не указана, PDF появится рядом с исходным Markdown. Существующие файлы защищены от перезаписи. Для обхода вложенных папок включите «Подпапки» перед добавлением папки. Если у файлов одинаковые имена и выбрана общая папка вывода, программа предупредит о конфликте.

Если готового архива пока нет в Releases, проверьте [состояние сборки](https://github.com/Mixerland1/md-to-pdf/actions/workflows/windows.yml). Сборка публикуется только после проверки EXE. Приложение не имеет цифровой подписи; проверяйте контрольную сумму из релиза.

### Установка из исходников

Установите Python 3.10+, Git и [системные библиотеки WeasyPrint](https://doc.courtbouillon.org/weasyprint/v68.0/first_steps.html). В Windows используйте инструкции для Python-библиотеки, а не только отдельного EXE WeasyPrint.

```powershell
git clone https://github.com/Mixerland1/md-to-pdf.git
cd md-to-pdf
py -m pip install ".[gui]"
py -m md_to_pdf.gui
```

Для командной строки:

```powershell
py -m md_to_pdf.cli "C:\Docs\guide.md" --template technical
py -m md_to_pdf.cli "C:\Docs" --recursive --output-dir "C:\PDF"
py -m md_to_pdf.cli --help
```

## Privacy and limitations

PDF conversion uses local assets from the source or custom stylesheet folder and data URIs. Remote images are not fetched; external hyperlinks remain clickable. Raw HTML is disabled by default. HTML exports reference local assets and do not provide the PDF resource restrictions when opened in a browser. Use trusted CSS; this is not a sandbox for untrusted documents. Cyrillic support requires suitable fonts. Mermaid, PlantUML, KaTeX and direct PNG/JPEG export are not implemented.

## Comparison with VS Code Markdown PDF

See [feature comparison, methodology and benchmark instructions](benchmark/README.md). The [comparison workflow](https://github.com/Mixerland1/md-to-pdf/actions/workflows/benchmark.yml) runs the actual yzane.markdown-pdf extension in VS Code and records measurements. Do not interpret the feature matrix as measured superiority.

## Roadmap / Дальнейшее развитие

See [product roadmap](docs/ROADMAP.md) for planned TXT/DOCX input, corporate profiles (Granulex first), and a visual style constructor. These features are under development for 0.3.0; the stable release remains 0.2.0.

## Development branch — Brand Style Studio 0.3.0

The next version supports Markdown, TXT and semantic DOCX import, Granulex branding and a local profile editor with logo import, colors, fonts, page margins, footer and PDF preview. These features are not yet in the stable 0.2.0 Windows release. See [document import](docs/IMPORTS.md), [brand profile instructions / Конструктор стилей](docs/PROFILES.md) and [Granulex visual QA](docs/GRANULEX_QA.md). Run `python scripts/fetch_fonts.py` before installing from this branch to package the verified public fonts.

## Development

```sh
python -m pip install ".[test,gui]"
python -m unittest discover -s tests -v
```

Version 0.2.0. Reconstructed from an incomplete earlier prototype, not a byte-for-byte recovery. License: ISC.

### Planned desktop builds (0.3.0)

Windows x64 and macOS Apple Silicon / Intel test builds are configured in the development branch. See [platform notes](docs/PLATFORMS.md). These are not yet published stable binaries.
