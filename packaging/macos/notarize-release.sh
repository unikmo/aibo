#!/usr/bin/env bash
# Distribute AIBO.app only after owner-approved Developer ID signing/notarization.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP="$ROOT/dist/AIBO.app"
OUT="$ROOT/dist/release"
[[ -d "$APP" ]] || { echo "Build AIBO.app first." >&2; exit 2; }
[[ -n "${AIBO_APPLE_SIGN_IDENTITY:-}" ]] || {
  echo "Missing owner-approved Apple Developer ID Application identity." >&2; exit 3;
}
[[ -n "${AIBO_APPLE_NOTARY_PROFILE:-}" ]] || {
  echo "Missing notarization keychain profile. No bypass is available." >&2; exit 3;
}
codesign --verify --deep --strict --verbose=2 "$APP"
if ! codesign -dv "$APP" 2>&1 | grep -q "runtime"; then
  echo "Missing Apple hardened runtime signature." >&2; exit 4
fi
mkdir -p "$OUT"
ZIP="$OUT/AIBO-notary-submission.zip"
ditto -c -k --keepParent "$APP" "$ZIP"
xcrun notarytool submit "$ZIP" --wait --keychain-profile "$AIBO_APPLE_NOTARY_PROFILE"
xcrun stapler staple "$APP"
xcrun stapler validate "$APP"
spctl --assess --type execute --verbose=2 "$APP"
# Standard drag-to-Applications layout. Do not ship unsigned developer builds.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp -R "$APP" "$STAGE/AIBO.app"
ln -s /Applications "$STAGE/Applications"
hdiutil create -volname AIBO -srcfolder "$STAGE" -ov -format UDZO "$OUT/AIBO-Control-Centre-macOS.dmg"
echo "Verified notarized macOS installer: $OUT/AIBO-Control-Centre-macOS.dmg"
