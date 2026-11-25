# Visual document editor — 0.4.0

## Product requirement
One interaction: select visible text with the mouse, choose an existing style, see the result. No Markdown syntax, raw HTML or CSS is required. The selected brand profile defines appearance. Keep the existing one-click batch converter as a separate fast path.

## Interaction
- Select any text range; inline styles (bold, italic, inline code, accent) affect exactly those characters, including selections spanning existing emphasis and links.
- Paragraph roles (normal, heading levels 1–3, quote, note, warning, code block) affect the paragraphs touched by the selection, as in Word. Do not silently turn a table or list into a heading; keep its structure. A future explicit split-paragraph operation can turn a portion into an independent block.
- Show only a compact style toolbar; no general-purpose formatting ribbon, CSS panel or raw markup. Keep selection visible while applying a style. Undo and redo must work.
- Source MD/TXT/DOCX is never changed. Export an edited PDF separately. Project saving/reopening, metadata role assignment, richer table/image actions and in-place real page preview are later milestones, not current guarantees.
- Use the shared semantic HTML importer and existing renderer; preserve links, images, tables, lists and headers. Do not reconstruct a document from its visible plain text. Do not fetch remote resources.
- Desktop first on Windows and both Mac architectures. Offline processing. No new background server.

## Implementation stages
1. Range-based semantic editing model: retain original DOM; expose readable blocks and safe allowed styles, exact inline ranges, paragraph role changes, undo/redo snapshots; regression tests.
2. Native desktop text selection editor and PDF export using the same resource policy as normal conversion. Text view is an editable-style approximation, not paginated WYSIWYG; actual PDF preview validates output. 
3. Project persistence (versioned local format, no implicit overwrite), document metadata assignment, reusable detection rules.
4. Full page preview, table/image and pagination controls, manual UI acceptance, frozen builds and release.

## Acceptance
Select a word in a linked sentence and apply accent; link and remaining text survive. Select multiple paragraphs and choose heading or quote; list/table semantics survive. One undo restores previous output. Apply identical operations to Markdown, TXT, and semantic DOCX. Keep source bytes unchanged. Preview/export must preserve embedded logos and local relative resources. Unsupported structural changes must be explained, never silently flatten content.
