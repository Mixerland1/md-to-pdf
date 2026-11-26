# Desktop updates

GitHub Releases distributes single ZIPs, one per architecture, without requiring GitHub sign-in. GitHub Actions artifacts are internal and may wrap the ZIP. Public previews are marked prerelease. Stable installs never switch to preview automatically; previews may update to newer previews or stable releases.

On a frozen desktop build, a background release check runs once at startup and does not send any document contents. Click the update button to initiate the download. Windows downloads into a temporary sibling directory on the same volume, verifies the exact size and SHA-256, validates archive paths and extracts only the managed EXE and _internal runtime. A local bundled PowerShell helper waits for the current process to exit, moves the old binaries to a backup, installs the new ones and restarts. On caught replacement/start failures it attempts to restore previous binaries. Backup and update.log remain in .md-to-pdf-update-* beside the app folder. No administrator elevation is requested. Avoid simultaneous instances and keep write permissions on the installation directory. If an update fails, inspect the log and backup. Profiles in ~/.md-to-pdf and all source files remain untouched. Bundled documentation is not replaced by the Windows updater.

macOS currently offers the matching single ZIP download only; automatic .app replacement is not yet enabled. No code-signing certificate or notarization is configured. A checksum published alongside the binary is integrity checking, not a substitute for independent code-signing. Older versions without the updater require one final manual installation.

Acceptance: successful frozen package tests, isolated Windows helper swap test, source unit tests, and manual update from beta 1 to a subsequent build on real Windows hardware. Do not claim that the last acceptance has occurred until verified.

Beta publication policy: a verified Windows archive may be published even if macOS builds fail. Only verified artifacts are included and missing platforms are identified in release notes; stable releases still require all three platforms. Beta 11 recovery uses the original successful Windows artifact and original source commit, not unverified Mac binaries.

Beta 14: Windows Setup.exe installs under Program Files, creates shortcuts and uninstaller. Installed version selects the SHA-256 verified setup asset and starts the installer wizard with normal UAC; portable ZIP continues to use the existing replacement helper. Portable-to-installed migration requires running setup once.
