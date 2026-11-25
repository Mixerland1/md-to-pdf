# 0.4.0 beta 7 — style replacement and editable clipboard

Ordinary list items can now become paragraphs or headings, and paragraphs can become bulleted or numbered items. Preserve neighboring list entries, ordered-list starts, links and text. Simple quote paragraphs can change roles. Table cells and complex nested list structures remain protected from destructive retagging. The toolbar reports the current list type.

Open Paste text from welcome or the editor, inspect and edit clipboard text, clear it or refill it, then explicitly open it. For unsaved pasted documents the editor button is Edit text. Replacing content creates a new layout; confirmation protects existing formatting edits. Escape cancels the dialog. Clipboard stays local.

Format by sample has a compact paintbrush icon, tooltip, active highlight, Escape cancellation, and one-shot application of semantic role, actual font, size, inline weight/slant and PDF fill color. Role-dependent spacing/alignment comes from the current preset, not arbitrary copied paragraph geometry. Complex mixed samples are rejected rather than guessed. Source documents unchanged. Manual Windows/Mac visual verification remains pending.
Follow-up: ensure Format by sample returns to its inactive appearance after application; keep the export/save controls visible at narrow window sizes by moving formatting tools to a second line only when necessary.
