# Desktop platforms (0.3.0)

Three native builds: Windows x64, macOS arm64 (Apple Silicon), and macOS x86_64 (Intel). macOS builds run on macOS 15 runners and use PyInstaller .app bundles with Pango native libraries, Python runtime, fonts and redistribution notices. Minimum supported macOS version is not yet verified; initial target is macOS 15. Build-time Homebrew is not intended as a runtime requirement. The portability check rejects absolute third-party dylib references and runs both normal and Granulex PDF smoke tests without a custom loader environment. Archives use ditto to preserve bundle symlinks.

## Installation
Windows: extract the whole ZIP and launch MD-to-PDF.exe. macOS: download the architecture-specific ZIP, extract it and move MD-to-PDF.app into Applications if desired. Development builds are ad-hoc signed, not Apple Developer ID signed or notarized; Gatekeeper may prevent launch. Do not disable Gatekeeper globally. A properly signed/notarized release needs an Apple Developer ID and notarization credentials. Validate the artifact and publisher before opening.

## Release verification
Granulex visual preview approved by project owner. Windows x64, macOS arm64 and macOS x86_64 development frozen builds and unit tests all passed at commit 8bbfb232. The combined workflow rebuilds all three from the release commit and publishes them together only on success. End-user hardware GUI/drag-and-drop acceptance is still pending; do not claim this has been performed. Existing 0.2.0 release remains unchanged.
