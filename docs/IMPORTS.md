# Document import (0.3.0 development)

- Markdown: existing Mistune renderer and flags unchanged.
- TXT: UTF-8 (optional BOM), UTF-16 with BOM; literal text, including line breaks and spaces. No automatic heading inference or interpretation as Markdown. Other encodings must first be saved as UTF-8.
- DOCX: semantic conversion using Mammoth, with external file access and embedded style maps disabled. Bleach sanitizes generated HTML. Headings using Word styles, paragraphs, emphasis, lists, basic tables, links and supported embedded raster images are carried into the HTML pipeline; arbitrary Word layout is not replicated. Import warnings go to Python warnings/stderr; richer GUI warning display is still planned. Complex equations, floating objects, Word-specific header/footer, comments and tracked changes are not a fidelity guarantee.
- Mixed batches use existing output collision and overwrite protection. Word temporary lock files are excluded.
- Granulex preset is a development approximation of the supplied print rules, not an official approved corporate style. Montserrat and Roboto Mono use system fonts if installed; original fonts are not included. The original Granulex vector mark is included as a built-in logo supplied for this project; the existing leading HTML header can be parsed without enabling arbitrary HTML. The local library and profile editor are now implemented in the development branch; see PROFILES.md.
- Source install in this branch: `python -m pip install ".[gui,test]"`; `md-to-pdf-gui`; `md-to-pdf a.md b.txt c.docx --template granulex`.

This is not the published Windows release. Verify CI and compare visual output before integration.

## Granulex header

The supplied logo.md contains a first-page header (not a repeating page header): a 42×42 SVG mark, product name, version and updated text. When a Markdown source starts with this exact doc-header/header-left/header-right structure, the importer extracts the safe path-only SVG and text, removes the original block and renders a single styled header. Otherwise the built-in mark is inserted automatically for MD/TXT/DOCX. Existing metadata is retained unless overridden. Without metadata, version and update are blank; no product release details are invented.

Example: `md-to-pdf guide.md --template granulex --brand-name "Granulex Recovery" --brand-version 3.0.0 --brand-updated "декабрь 2026"`. The GUI exposes equivalent fields for the Granulex preset. The current SVG allowlist is intentionally narrow (SVG root and paths only); it is not a general SVG import constructor. Logos remain vector via SVG in PDF. The Granulex mark is a third-party brand asset, not relicensed under ISC; use does not imply endorsement. The project owner confirmed redistribution rights for the supplied mark.
