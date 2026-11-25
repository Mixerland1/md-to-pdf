# Desktop UX — 0.4.0

Main screen: drop files/folders, choose a document style, optionally edit one document, create PDF. Russian labels; no duplicate English translations. Folder import includes subfolders. PDF output always defaults to the same folder and basename as its source. Existing PDFs are replaced automatically, only after a successful render. Source documents are protected; conflicting target paths in a batch are rejected. CLI keeps its explicit --overwrite, --output-dir and --css options for scripting.

Main screen hides technical CSS, output paths, overwrite toggles and per-document product/version/date fields. Recognized Markdown metadata is automatic; edit the actual header using the optional Шапка button in the document editor. Do not apply one product/version/date to an entire unrelated batch. No fictitious dates.

One Настроить стили entry opens the style library. Select a built-in or saved style, configure fonts using installed-font dropdowns (including packaged families), colors via visible swatches, page settings and real PDF preview. Built-ins are not overwritten: edits save a named copy. Create/import actions live inside the library, not the conversion screen. JSON export remains inside the profile editor.

Native text editor prototype has a style toolbar, mouse selection, undo/redo and direct PDF export beside source. It is not a real page-layout view yet. Manual visual and keyboard testing on Windows and Mac remains required.

Preview build: branch develop/v0.4.0 triggers Windows and both macOS artifacts, without publishing a stable release. Font and page controls use bounded spinboxes; the style editor has separate Fonts, Colors, Page and Logo/Brand tabs. Source GUI smoke tests run under Xvfb in Linux CI. This is not manual desktop acceptance.

## Beta 2 supersedes the queue UI
Single document only: open/drop, inline preset selector and contextual style selection, actual PDF pages, export. No file list, folder/remove buttons or persistent output instructions. Export writes the preview's exact PDF bytes next to the source, replacing the existing PDF. CLI batch remains. Unexported changes are protected when opening another file or closing. Complex unmapped text is not silently modified. No project persistence yet. Profile customization is available through one gear icon; updater button appears only when a release is available.

## Beta 3 selection
Click selects semantic block; drag selects characters with adjustable endpoints; merged blue line highlights. Current role, font, size shown; mixed state per control. Reflow restores selection. Font and point size overrides; one-shot brush for a uniform style. Save persists source-bound sidecar, Export PDF remains separate. No extra formatting ribbon. Manual visual acceptance pending.

## Beta 5 — welcome artwork and paste
The welcome screen uses the selected first blue/white wave artwork; the header uses a crop of the approved toolbar mockup without its fake controls. Both assets are bundled in compressed WebP; the title bar remains native. Welcome offers Open and Paste text, and drag/drop. Ctrl+V (Command+V on Mac) imports clipboard text as Markdown unless editing a text input. Pasted documents use a private temporary workspace; initial export chooses PDF, initial save writes a new Markdown source plus sidecar. Existing source documents never get overwritten. No extra update button: only show an available update detected at startup.

## Beta 6
Paste dialog supports inspection, editing, refilling, cancellation and reopening from the editor. Ordinary list entries and simple quote paragraphs can change roles. Format by sample icon, tooltip and Esc cancellation; copy uniform role, font, size, weight/slant and color; role-dependent geometry comes from preset. Complex nested lists and table cells remain protected. No additional update button.

Beta 7: format-by-sample mode clears after application; toolbar adapts to width without hiding export/save.

Beta 8: Version and Last updated are explicit fragment roles; branded presets assign complete paragraphs to empty right header fields. Existing table cells expose Cell and Table heading roles; contextual Table parameters provides width, position, and borders. No permanent extra toolbar button.
