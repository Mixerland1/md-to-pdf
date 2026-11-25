# Document import (0.3.0 development)

- Markdown: existing Mistune renderer and flags unchanged.
- TXT: UTF-8 (optional BOM), UTF-16 with BOM; literal text, including line breaks and spaces. No automatic heading inference or interpretation as Markdown. Other encodings must first be saved as UTF-8.
- DOCX: semantic conversion using Mammoth, with external file access and embedded style maps disabled. Bleach sanitizes generated HTML. Headings using Word styles, paragraphs, emphasis, lists, basic tables, links and supported embedded raster images are carried into the HTML pipeline; arbitrary Word layout is not replicated. Import warnings go to Python warnings/stderr; richer GUI warning display is still planned. Complex equations, floating objects, Word-specific header/footer, comments and tracked changes are not a fidelity guarantee.
- Mixed batches use existing output collision and overwrite protection. Word temporary lock files are excluded.
- Granulex preset is a development approximation of the supplied print rules, not an official approved corporate style. Montserrat and Roboto Mono use system fonts if installed; no original assets are included. SVG logo extraction and library/constructor are next stages.
- Source install in this branch: `python -m pip install ".[gui,test]"`; `md-to-pdf-gui`; `md-to-pdf a.md b.txt c.docx --template granulex`.

This is not the published Windows release. Verify CI and compare visual output before integration.
