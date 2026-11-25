# Granulex visual QA

Reference: supplied docstyle.css, settings.json and logo.md. The original CSS uses 8px / 12px body, 18px / 24px H1, 16px / 22px H2, 14px / 20px H3, 10px / 16px H4, 8px / 12px H5 and scale 1.33333. WeasyPrint uses the scaled values; margins are 32/56/72/56 CSS px as supplied. The browser global reset and inherited default styles are not copied literally: explicit rules preserve page breaks, table headers and readable document flow. Footer page numbers are intentionally gray rather than whitesmoke; copyright is configurable instead of hard-coded. SVG geometry is unchanged. Font sourcing uses the pinned Google Fonts repository commit and Git blob hashes in scripts/fetch_fonts.py; both licenses travel with the fonts. They are public variable fonts, not byte-identical copies of the supplied static font files. No runtime network request is required.

Run from source:
```
python scripts/fetch_fonts.py
python -m pip install ".[gui,test]"
md-to-pdf examples/granulex-style-check.md --template granulex --brand-name "Granulex Recovery" --brand-version 3.0.0 --brand-updated "декабрь 2026"
```

Check A4, headings, nested lists, table, quote, inline code, code block, link, first-page header, footer, and embedded font names. CI checks actual embedded font families. Exact Chromium reference PDF has not been supplied; pixel-for-pixel comparison cannot be claimed. Font bundle and Windows build require successful CI before release.

Local visual check: WeasyPrint 68.0, supplied static Montserrat 9.000 regular/bold and Roboto Mono 3.001. One-page A4 synthetic fixture rendered and inspected at 1200 px; correct logo, text, headings, nested lists, table, quote, code and page number; pdffonts confirmed embedded Montserrat and Roboto Mono. This is a local CSS preview with reference fonts, not a frozen EXE or exact upstream-variable-font render. The supplied logo.md has a stray quote before the third path closing tag; the legacy-header adapter now normalizes that specific malformed ending before strict SVG validation. Original logo path geometry unchanged.

The project owner approved the supplied local visual preview. Frozen build checks remain required.
