# Desktop platforms (0.3.0 development)

Three native builds: Windows x64, macOS arm64 (Apple Silicon), and macOS x86_64 (Intel). macOS builds run on macOS 15 runners and use PyInstaller .app bundles with Pango native libraries, Python runtime, fonts and redistribution notices. Minimum supported macOS version is not yet verified; initial target is macOS 15. Build-time Homebrew is not intended as a runtime requirement. The portability check rejects absolute third-party dylib references and runs both normal and Granulex PDF smoke tests without a custom loader environment. Archives use ditto to preserve bundle symlinks.

## Installation (after verified release)
Windows: extract the whole ZIP and launch MD-to-PDF.exe. macOS: download the architecture-specific ZIP, extract it and move MD-to-PDF.app into Applications if desired. Development builds are ad-hoc signed, not Apple Developer ID signed or notarized; Gatekeeper may prevent launch. Do not disable Gatekeeper globally. A properly signed/notarized release needs an Apple Developer ID and notarization credentials. Validate the artifact and publisher before opening.

## Release gate
Granulex visual preview approved by project owner. All prior unit tests passed. Development branch artifacts are for testing, not automatically published to Releases. Verify Windows and both macOS frozen builds, embedded brand fonts, license notices, and GUI/drag-and-drop on target devices. Then integrate a stable version and publish tested assets. Existing 0.2.0 release remains unchanged.
