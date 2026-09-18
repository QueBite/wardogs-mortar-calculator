#!/usr/bin/env bash
# Rebuild the exe and publish it as a new GitHub Release.
#
#   ./release.sh 1.0.1 "Fixed the bearing calculation"
#
# Verifies the public download link before reporting success.
set -euo pipefail

VERSION="${1:-}"
NOTES="${2:-}"

if [ -z "$VERSION" ]; then
    echo "usage: ./release.sh <version> \"<what changed>\""
    echo "example: ./release.sh 1.0.1 \"Fixed the bearing calculation\""
    exit 1
fi

TAG="v${VERSION#v}"                      # accept both 1.0.1 and v1.0.1
cd "$(dirname "$0")"
export PATH="$PATH:/c/Program Files/GitHub CLI"

command -v gh >/dev/null || { echo "ERROR: gh CLI not found."; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "ERROR: not logged in. Run: gh auth login --web"; exit 1; }

if gh release view "$TAG" >/dev/null 2>&1; then
    echo "ERROR: release $TAG already exists. Tags cannot be reused - bump the version."
    exit 1
fi

# A running instance holds a file lock and the rebuild would fail or go stale.
powershell -NoProfile -Command \
    "Stop-Process -Name MortarCalculator -Force -ErrorAction SilentlyContinue" >/dev/null 2>&1 || true
sleep 1

echo "==> Rebuilding..."
buildenv/Scripts/python.exe -m PyInstaller MortarCalculator.spec --noconfirm 2>&1 | tail -3
[ -f dist/MortarCalculator.exe ] || { echo "ERROR: build produced no exe."; exit 1; }

echo "==> Committing source..."
git add -A
if git diff --cached --quiet; then
    echo "    (no source changes to commit)"
else
    git commit -q -m "${NOTES:-Release $TAG}"
fi
git push -q

echo "==> Publishing $TAG..."
gh release create "$TAG" \
    "dist/MortarCalculator.exe#MortarCalculator.exe (Windows, no install needed)" \
    --title "$TAG - Mortar Calculator" \
    --notes "${NOTES:-See commit history for changes.}

Download **MortarCalculator.exe** below. No install needed - just double-click.

Windows may warn \"Windows protected your PC\" because the file isn't code-signed. Click **More info** then **Run anyway**."

# Prove the public link works: fetch with NO auth and hash-match the local build.
echo "==> Verifying public download..."
GH_USER=$(gh api user --jq '.login')
REPO=$(basename -s .git "$(git remote get-url origin)")
TMP="${LOCALAPPDATA:-/tmp}/Temp/relcheck_$$.exe"

# GitHub needs a moment after publishing before /releases/latest/ points at
# the new tag; without this the check can still be served the previous release.
sleep 5

HTTP=$(curl -sL -o "$TMP" \
    "https://github.com/$GH_USER/$REPO/releases/latest/download/MortarCalculator.exe" \
    -w '%{http_code}')

# Hash via stdin, NOT `sha256sum <file>`. GNU coreutils prefixes its output
# line with a literal backslash when the filename contains one, and
# $LOCALAPPDATA is C:\Users\... - that stray backslash lands in the captured
# hash and produces a false mismatch. Reading stdin leaves no filename to escape.
REMOTE_HASH=$(sha256sum < "$TMP" | cut -d' ' -f1)
LOCAL_HASH=$(sha256sum < dist/MortarCalculator.exe | cut -d' ' -f1)

if [ "$HTTP" = "200" ] && [ "$REMOTE_HASH" = "$LOCAL_HASH" ]; then
    rm -f "$TMP"
    echo
    echo "SUCCESS - verified live. Share this link:"
    echo "  https://github.com/$GH_USER/$REPO/releases/latest"
else
    rm -f "$TMP"
    echo "WARNING: published, but the public download did not verify."
    echo "  HTTP:   $HTTP (expected 200)"
    echo "  remote: $REMOTE_HASH"
    echo "  local:  $LOCAL_HASH"
    echo "Check: gh release view $TAG"
    exit 1
fi
