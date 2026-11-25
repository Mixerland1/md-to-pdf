# MD to PDF 0.3.1 — automatic document metadata

Brand profiles now recognize a leading Markdown H1 followed by a product name with a dotted version and an explicitly labeled last-update date. The name is shown next to the logo, the version and update date on the right, and the H1 below. The matched metadata block is removed from the PDF body only. The source remains unchanged. Existing HTML headers and manual overrides remain supported. Unrecognized text remains untouched. The rule applies to Granulex and custom brand profiles for Markdown input; TXT and DOCX still use manual metadata.

All three desktop builds run frozen PDF smoke tests for this pattern. Windows x64, macOS arm64 and Intel x86_64; macOS 15 is the initial tested target. Windows unsigned, macOS not notarized. Manual GUI acceptance remains pending. Missing document images must be supplied next to the source in their referenced folders.
