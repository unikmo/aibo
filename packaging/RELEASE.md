# AIBO desktop release gates

AIBO uses **one local Control Centre/runtime** with Windows and macOS packaging.
The default launcher embeds the local Control Centre in a native **WebView window** (Windows WebView2/macOS Cocoa WebKit). The HTTP server remains on loopback; UI runs in the application window, not an external browser.

## Windows
- Build with `build-windows.ps1` on Windows. The executable bundles the runtime and native WebView and does not require customer-installed Python.
- Inno Setup is defined at `packaging/windows/AIBO.iss`. It creates Start menu and optional desktop shortcuts; Windows CI must compile, install and uninstall the isolated development installer.
- Use a trusted publisher Authenticode certificate and sign **both** `AIBO.exe` and the generated installer with an approved signing service and timestamp.
- `build-windows-installer.ps1` refuses unsigned production builds. Owner-controlled Windows signing uses `AIBO_WINDOWS_SIGNING_THUMBPRINT` and SignTool with an authorized certificate in the certificate store; private keys do not belong in GitHub. `-AllowUnsignedDevelopment` is only for isolated CI and does not bypass Smart App Control.
- Verify on a clean Windows 11 machine with Smart App Control enabled; CI smoke tests alone do not satisfy this release gate.

## macOS
- Build `AIBO.app` with `build-macos.sh` on macOS. It runs inside a native Cocoa/WebKit window with the same Control Centre and user data.
- Distribution outside the App Store requires Apple Developer ID Application signing, hardened runtime, notarization and stapling. With an approved Apple signing identity and `notarytool` keychain profile, use `packaging/macos/notarize-release.sh` to produce a signed and notarized drag-install `.dmg`.
- Validate with `codesign --verify --deep --strict`, `spctl --assess`, and launch on a fresh macOS installation. No instructions to bypass Gatekeeper.
- Unsigned CI artifacts are **development-only**, not public-ready downloads.

## Release blockers
- Windows individual-publisher Authenticode certificate or managed signing provider, plus verified Smart App Control reputation.
- Apple Developer Program enrollment under the owner's **individual legal name**, verified Developer ID credentials and notarization authorization. The repository never invents publisher legal identity.
- Manual Smart App Control and Gatekeeper acceptance on clean systems.
- GitHub Actions artifact storage quota currently interferes with ZIP uploads.

Never claim Windows or macOS is security-trusted based solely on passing the functional test suite.

## Native desktop release acceptance
- Desktop-shell unit tests cover window URL and loopback-server lifecycle including GUI failure cleanup.
- Both platform builds verify packaged WebView availability, local APIs and per-user data persistence.
- Windows CI compiles, installs and uninstalls a development-only installer.
- Shipping requires manual verification on protected Windows 11 (Smart App Control) and macOS (Gatekeeper) machines. Signing does not imply automatic Smart App Control reputation.

## Individual-publisher Windows Store route (preferred in Germany)

For a verified **individual** publisher based in Germany, Microsoft Artifact Signing Public Trust currently supports individual developers only in the USA and Canada. Do not initiate an ineligible Azure Artifact Signing identity-verification request. The alternative for a new Windows app is **Microsoft Store MSIX**: Microsoft re-signs an accepted MSIX package during Store submission, so a commercial Authenticode certificate is not required for that channel. This does **not** sign an independent EXE/installer downloaded outside the Store.

- The Store manifest template is `packaging/windows/AppxManifest.xml`; build with `build-windows-msix.ps1` **only after** reserving the app's official Partner Center identity and publisher certificate subject.
- Set `AIBO_MSIX_IDENTITY`, `AIBO_MSIX_PUBLISHER`, and `AIBO_MSIX_PUBLISHER_DISPLAY` to the exact Store-issued values. Never invent the individual's legal name or publisher subject.
- CI's `-Development` build packs and unpacks an unsigned synthetic-identity MSIX for structural validation only. It cannot be installed on protected customer machines or sent to the Store as production.
- Production publishing requires the owner's individual Store account, acceptance of legal terms, reservation of AIBO product identity, submission, Microsoft certification, and verification on Windows 11 with Smart App Control enabled.
- An independent Windows installer (outside Microsoft Store) still requires an individually validated code-signing certificate or a supported commercial service, appropriate costs, and verified reputation.
