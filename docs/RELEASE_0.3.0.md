# MD to PDF 0.3.0 — Brand Style Studio

- Convert Markdown, plain text (UTF-8/UTF-16 BOM), and DOCX into styled PDF; mixed batch conversion.
- Granulex preset with authorized original vector mark, configurable product name, version and update date.
- Create, copy, import and export local brand profiles with colors, fonts, logos, page margins, footer and PDF preview.
- Built-in Montserrat and Roboto Mono fonts (SIL OFL).
- Native portable packages for Windows x64, macOS Apple Silicon (arm64) and Intel (x86_64).

## Downloads
Download the ZIP for your architecture, verify SHA256SUMS.txt and extract the whole archive. On Windows run MD-to-PDF.exe; on Mac open MD-to-PDF.app. No separate Python or Homebrew installation is intended.

## Known limitations
The app is unsigned on Windows and ad-hoc signed, not notarized, on Mac; Gatekeeper may prevent first launch. Initial macOS target is macOS 15; older versions are not validated. Automated frozen PDF checks run on all three platforms; manual GUI and drag-and-drop acceptance on end-user hardware is still pending. DOCX import is semantic re-styling, not exact Word layout. SVG import supports self-contained path-only marks; raster logos stay raster in an SVG wrapper. More corporate styles and exact Word layout mode are planned. 
