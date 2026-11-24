# AIBO desktop release gates

AIBO uses **one local Control Centre/runtime** with Windows and macOS packaging.
The current launcher opens the local UI in the default browser. It is not a standalone native WebView yet. Do not advertise it as one.

## Windows
- Build with `build-windows.ps1` on Windows.
- A reproducible Inno Setup installer definition is at `packaging/windows/AIBO.iss`. It creates Start menu and optional desktop shortcuts.
- Use a trusted publisher Authenticode certificate and sign **both** `AIBO.exe` and the generated installer with an approved signing service and timestamp.
- `build-windows-installer.ps1` refuses unsigned production builds. `-AllowUnsignedDevelopment` is for isolated engineering tests only, **not** a solution to Windows Smart App Control.
- Verify on a clean Windows 11 machine with Smart App Control enabled; CI smoke tests alone do not satisfy this release gate.

## macOS
- Build `AIBO.app` on a macOS runner with `build-macos.sh`.
- For distribution outside the App Store, sign with an Apple Developer ID Application certificate, enable hardened runtime and required entitlements where applicable, notarize with Apple, and staple the notarization ticket.
- Validate with `codesign --verify --deep --strict`, `spctl --assess`, and launch on a fresh macOS installation. No instructions to bypass Gatekeeper.
- Unsigned CI artifacts are **development-only**, not public-ready downloads.

## Release blockers
- Windows publisher certificate or managed signing provider.
- Apple Developer Program membership, Developer ID signing credentials and notarization authorization.
- Manual Smart App Control and Gatekeeper acceptance on clean systems.
- GitHub Actions artifact storage quota currently interferes with ZIP uploads.

Never claim Windows or macOS is security-trusted based solely on passing the functional test suite.
