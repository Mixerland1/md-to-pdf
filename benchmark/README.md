# MD to PDF vs Markdown PDF for VS Code

Comparison target: [yzane.markdown-pdf](https://github.com/yzane/vscode-markdown-pdf), extension 2.2.0 (pinned in the benchmark). Feature claims below are based on the upstream README and package manifest, not runtime measurements.

| Capability | MD to PDF 0.2.0 | VS Code Markdown PDF |
|---|---|---|
| Host application | Standalone GUI / CLI | VS Code |
| PDF engine | WeasyPrint | Chromium |
| PDF, HTML | Yes | Yes |
| PNG / JPEG export | No | Yes |
| Local file images, tables, links | Supported | Documented |
| Header/footer, page numbers, custom CSS | Supported | Documented |
| Built-in document templates | Three named presets | Default styles and configurable CSS |
| Multi-file/folder batch | CLI / GUI | Auto-convert and editor export; identical folder workflow not assumed |
| Mermaid / PlantUML / math | Not implemented | Documented (check version/configuration) |
| Remote images | Blocked by default | Depends on extension configuration and input |

## Reproducible benchmark

The GitHub Actions comparison job installs the real VS Code extension (not a mock or a separate Chromium renderer), uses the same UTF-8 fixtures for both products, records the PDF outputs and runs a neutral pypdf inspection script. Extension version, VS Code version and environment are recorded in the artifact. The VS Code command is extension.markdown-pdf.pdf. Timings cover conversion only (not install), with one cold and two subsequent runs. This is a small functional sample, not a statistically representative performance study.

Download the artifact named comparison-results from the [workflow runs](https://github.com/Mixerland1/md-to-pdf/actions/workflows/benchmark.yml). It contains result.json plus both PDF sets. For visual review compare page breaks, overflow, image placement, code wrapping, table readability and overall typography manually. Default typography and headers intentionally differ; do not treat page count differences alone as errors.

Manual reproduction with VS Code 1.110.0 and extension 2.2.0:
1. Generate identical fixtures: `python benchmark/fixtures.py work`.
2. Run `md-to-pdf work/md --overwrite` and export each .md in work/vscode using Markdown PDF: Export (pdf) with default settings (A4).
3. Run `python benchmark/compare.py work`. Optional timing JSON may be supplied in each directory as timings.json.

The script measures extracted-text markers, external link annotation, internal destination, page count, PDF file size and raster image count. Embedded SVGs may be vector graphics and are not covered by the raster-image count. Visual review remains necessary. The script does not assign an overall winner.

## Measured results — 2026-11-25

[Successful run and logs](https://github.com/Mixerland1/md-to-pdf/actions/runs/45614647919), commit `e9e125c11f7e7b09ad1c43ef88d250fc97296dd1`. Linux x86-64, MD to PDF 0.2.0, VS Code 1.110.0, Markdown PDF 2.2.0. Median of three conversions (one cold and two subsequent).

| Fixture | MD to PDF (ms) | VS Code (ms) | Speed ratio | MD to PDF (bytes) | VS Code (bytes) |
|---|---:|---:|---:|---:|---:|
| guide | 388.38 | 2601.97 | 6.70x | 15321 | 36845 |
| long | 473.01 | 3042.46 | 6.43x | 14726 | 33767 |
| unicode | 332.05 | 3053.31 | 9.20x | 10602 | 20006 |

Both preserved all seven expected text markers. Both preserved the tested internal link and one raster image in guide. The inspection found the expected external URI in MD to PDF but not in the extension output; this is a fixture-specific observation, not proof that the extension cannot export external links. Page counts were 1/6/1 versus 1/5/1. Visual layout has not yet been independently scored.

[Download the original result JSON and PDFs](https://github.com/Mixerland1/md-to-pdf/actions/runs/45614647919/artifacts/15022335275) (GitHub login may be required; temporary artifact). These results reflect only the tested fixtures, settings, and runner, not general superiority or Windows performance.

