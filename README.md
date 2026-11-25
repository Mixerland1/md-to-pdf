# MD to PDF

A standalone, local Markdown-to-PDF CLI for technical documents. No VS Code, browser extension or cloud service required.

## Install

Requires Python 3.10+ and WeasyPrint system libraries (Pango). See [platform installation instructions](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) for Windows, macOS and Linux.

```sh
git clone https://github.com/Mixerland1/md-to-pdf.git
cd md-to-pdf
python -m pip install .
md-to-pdf examples/example.md
```

On Windows, use `py -m pip install .` if `python` is unavailable.

```sh
md-to-pdf document.md -o document.pdf --title "User guide" --css custom.css
md-to-pdf document.md --html-only
md-to-pdf --help
```

## Features

A4 pagination, running title, page numbers, date, Cyrillic (with installed fonts), tables, code blocks, local images, external and internal links, custom CSS. Raw HTML is disabled by default; use `--allow-html` only for trusted input. PDF resource loading is limited to local source/stylesheet folders and data URIs. External hyperlinks remain clickable; remote images are not fetched. HTML exports reference local assets and are not self-contained; opening them in a browser is outside the PDF resource restrictions.

## Русский

Самостоятельный локальный конвертер Markdown в PDF для технической документации. VS Code не нужен. Установите Python и системные зависимости WeasyPrint по ссылке выше, затем выполните `python -m pip install .` в папке проекта. Для конвертации: `md-to-pdf document.md`. PDF появится рядом с исходником. Параметр `--css` подключает собственные стили, `--title` задаёт колонтитул, `--date` — дату, `-o` — путь результата. Для кириллицы установите подходящие системные шрифты.

## Development

```sh
python -m pip install '.[test]'
python -m unittest discover -s tests -v
```

This initial version reconstructs the Markdown → HTML → PDF approach from an incomplete earlier prototype; it is not a byte-for-byte recovery. The original stylesheet was unavailable. The default stylesheet and CLI are newly implemented. No comparison benchmark against VS Code extensions has been performed.

License: ISC.
