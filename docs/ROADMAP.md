# Product roadmap — Document Converter & Brand Style Studio

## Product direction
MD to PDF remains the product name. The goal is local conversion of documents into consistent, professional PDFs without VS Code or a mandatory cloud service. Preserve CLI and batch workflows, and support portable Windows builds. Keep the stable 0.2.0 release available while developing 0.3.0 on a separate branch.

## Delivery stages
- [x] A — Input adapter tests passed in CI. Input adapters: Markdown, TXT, DOCX; common semantic HTML pipeline; mixed-format batch and desktop file selection.
- [ ] B — Initial Granulex typography preset committed; exact fidelity and fonts pending; logo tests passed. Brand profile schema and built-in Granulex preset, based on supplied CSS/settings. Preserve layout, typography, palette, tables, lists, code and quotes; document renderer differences.
- [ ] C — Granulex-specific leading header extraction and built-in SVG implemented; local profile persistence, path-only SVG and raster import now implemented; advanced SVG support and CI pending. SVG logo extraction/import, duplicate prevention, and local profile persistence; PNG/JPEG embedded in SVG is raster, not vector tracing. Keep vector paths for original SVG. Sanitize SVG, disallow scripts, external assets and unsafe references.
- [ ] D — Initial editable profile library and desktop editor committed; automated tests and visual acceptance pending. Visual brand constructor: name, logo, colors, fonts, spacing, margins, header/footer, page numbering, table styles, preview, export/import profiles. Never require company docs to be published.
- [ ] E — Additional corporate presets after verification of branding and redistribution rights; distinguish official from unofficial profiles. Do not distribute proprietary fonts/logos without permission.
- [ ] F — DOCX faithful-layout mode as separate backend (evaluate LibreOffice or Word); do not confuse semantic re-styling with pixel-identical Word rendering.
- [ ] G — Regression tests, example PDFs, GUI review, Windows frozen EXE tests and release 0.3.0.

## Acceptance criteria
- MD output remains compatible with 0.2.0; TXT content is escaped and line breaks preserved; DOCX semantic mode preserves supported headings, paragraphs, emphasis, lists, tables, internal/external hyperlinks, embedded raster images and reports import warnings.
- The same profile applies consistently regardless of source type; mixed batches protect existing output and detect identical target names.
- No external file access from DOCX imports; no scripts or unsafe URL schemes in sanitized output; local resource restrictions remain in effect.
- Granulex reference: A4; original settings margins top 32px, bottom 72px, left/right 56px; original scale 1.33333 (adapt and visually validate for WeasyPrint rather than silently assume equivalence); Montserrat regular/bold, Roboto Mono; accent #E2112E, text #1F2937, dark red #B50E25 and gray palette. Original copyright footer is company-specific; use configurable footer, not a hard-coded assertion of ownership.
- Actual reference archive inspected: .vscode/docstyle.css, settings.json, three font files, and a sample Markdown guide. No literal inline SVG element found in that sample. A separate logo.md was subsequently supplied with the exact vector mark and first-page header; this is used for the Granulex development preset. Do not publish the guide, local paths, or supplied fonts by default.
- No claim of exact Word pagination, fidelity for floating objects, tracked changes, equations, or advanced layout until independently tested.
- Keep existing release intact; no release claim until CI and frozen executable checks pass.

## Workflow
Separate development branch; review and test changes before integration. Record exact test evidence and known limitations. Use synthetic public fixtures only.
