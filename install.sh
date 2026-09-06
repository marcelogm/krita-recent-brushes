#!/usr/bin/env bash
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
pykrita="$HOME/.local/share/krita/pykrita"

mkdir -p "$pykrita"
ln -sfn "$repo/recent_brushes" "$pykrita/recent_brushes"
ln -sf "$repo/kritapykrita_recent_brushes.desktop" \
       "$pykrita/kritapykrita_recent_brushes.desktop"

echo "Installed into $pykrita"
echo "Now: Krita > Settings > Configure Krita > Python Plugin Manager >"
echo "tick 'Recent Brushes', click OK and restart Krita."
