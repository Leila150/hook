#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
REPO_URL="${HOOK_TERMUX_REPO_URL:-https://leila150.github.io/hook}"
LIST_FILE="$PREFIX/etc/apt/sources.list.d/hook.list"

if [ ! -d "$PREFIX" ]; then
    echo "This script must be run inside Termux." >&2
    exit 1
fi

mkdir -p "$(dirname "$LIST_FILE")"
printf 'deb [trusted=yes] %s stable main\n' "$REPO_URL" > "$LIST_FILE"

echo "HOOK Termux repository added: $REPO_URL"
echo "Run: pkg update"
echo "Then: pkg install hook"
