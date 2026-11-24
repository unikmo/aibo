#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
# Build on macOS, so the binary and Apple frameworks match the target OS.
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "AIBO .app must be built on macOS" >&2; exit 2
fi
python3 -m pip install "pypdf>=5,<8"
python3 -m PyInstaller --noconfirm --clean --onedir --windowed --name AIBO \
  --specpath build \
  --add-data "$ROOT/Control-Centre:Control-Centre" \
  --add-data "$ROOT/System:System" \
  --add-data "$ROOT/Industry-Packs:Industry-Packs" \
  --add-data "$ROOT/runtime/agents.json:runtime" \
  --add-data "$ROOT/runtime/connectors.json:runtime" \
  --collect-all playwright \
  runtime/macos_app.py

APP="$ROOT/dist/AIBO.app"
if [[ ! -d "$APP" ]]; then
  echo "PyInstaller did not produce AIBO.app" >&2; exit 1
fi
# Signing is not optional for a public release. CI builds are test artifacts only.
if [[ -n "${AIBO_APPLE_SIGN_IDENTITY:-}" ]]; then
  codesign --force --deep --options runtime --timestamp \
    --sign "$AIBO_APPLE_SIGN_IDENTITY" "$APP"
  codesign --verify --deep --strict --verbose=2 "$APP"
fi
echo "Built: $APP"
