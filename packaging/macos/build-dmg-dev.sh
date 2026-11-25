#!/usr/bin/env bash
# Verify macOS DMG creation and mount without implying trusted distribution.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP="$ROOT/dist/AIBO.app"
OUT="$ROOT/dist/AIBO-macOS-UNSIGNED-DEVELOPMENT.dmg"
[[ -d "$APP" ]] || { echo "AIBO.app missing" >&2; exit 2; }
STAGING="$(mktemp -d)"
MOUNT="$(mktemp -d)"
attached=0
cleanup() {
  if [[ "$attached" == "1" ]]; then hdiutil detach "$MOUNT" -quiet || true; fi
  rm -rf "$STAGING" "$MOUNT"
}
trap cleanup EXIT
ditto "$APP" "$STAGING/AIBO.app"
ln -s /Applications "$STAGING/Applications"
hdiutil create -volname AIBO -srcfolder "$STAGING" -ov -format UDZO "$OUT"
hdiutil verify "$OUT"
hdiutil attach "$OUT" -mountpoint "$MOUNT" -nobrowse -readonly -quiet
attached=1
[[ -f "$MOUNT/AIBO.app/Contents/MacOS/AIBO" ]] || {
  echo "Mac application missing from mounted DMG" >&2; exit 1;
}
[[ -L "$MOUNT/Applications" ]] || { echo "Drag-to-Applications shortcut missing" >&2; exit 1; }
echo "macOS unsigned-development DMG build and mount checks passed"
