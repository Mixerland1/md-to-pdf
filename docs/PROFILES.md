# Brand Style Studio (development)

Select Granulex or a generic base in the desktop app, then choose **Edit / Стиль** to create a local editable copy. **Copy / Копировать** saves a separate profile; **New / Новый** starts with a neutral style; **Import / Импорт** opens a portable JSON profile for inspection and saving locally. Saved profiles appear in the template dropdown. Use **Предпросмотр PDF** to generate a real sample PDF to a chosen location and open it in the system viewer. **Экспорт JSON** exports all settings and the embedded logo, without the source document.

Profiles are stored in `~/.md-to-pdf/profiles`. Built-in styles remain unchanged. Local profiles override the selected base and can be used from CLI:

`md-to-pdf document.docx --profile my-brand.json --brand-version 1.0`

Schema 1: name, base, product, seven colors, two installed font family names, body size, line height, four page margins, logo height, footer text and page numbering. Logos: self-contained SVG path-only marks are preserved as vector; PNG/JPEG are normalized and embedded in an SVG container (still raster). No arbitrary CSS or external URLs are permitted in imported profiles. Advanced SVG elements and true raster-to-vector tracing are not supported yet. Existing matching Granulex source header is stripped when applying a custom profile so the selected brand wins. Use the built-in Granulex preset to preserve embedded source metadata; use command-line or GUI fields for explicit custom profile metadata.

Fonts are system-installed; missing fonts fall back. Exact rendering of original corporate reference, additional corporate presets, live in-window preview, faithful DOCX layout and Windows portable build remain pending. User confirmed redistribution rights for the supplied Granulex mark only. 

## Краткая инструкция

1. Выберите granulex или другой базовый шаблон и нажмите «Стиль». Для отдельного профиля без логотипа нажмите «Новый».
2. Укажите название компании, загрузите SVG/PNG/JPEG, задайте шрифты, цвета, поля и колонтитул.
3. Нажмите «Предпросмотр PDF», выберите путь для пробного документа и откройте его в просмотрщике.
4. Сохраните профиль в библиотеку. Выберите его в списке шаблонов, добавьте MD/TXT/DOCX и запустите конвертацию.
5. Для обмена нажмите «Экспорт JSON». Получатель может импортировать этот файл через «Импорт» и сохранить его в своей библиотеке. Логотип включён в JSON, но шрифты должны быть установлены отдельно.
