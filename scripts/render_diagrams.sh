#!/usr/bin/env bash
# Render docs/diagrams/*.mmd → docs/diagrams/png/*.png with mermaid-cli.
# Needs Node and a Chrome/Chromium: MMDC=path/to/mmdc CHROME=path/to/chrome ./scripts/render_diagrams.sh
# (default: npx @mermaid-js/mermaid-cli and Google Chrome on macOS).
set -euo pipefail
cd "$(dirname "$0")/../docs/diagrams"
mkdir -p png
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
cfg="$(mktemp)"; printf '{"executablePath": "%s", "args": ["--no-sandbox"]}' "$CHROME" > "$cfg"
MMDC="${MMDC:-npx -y @mermaid-js/mermaid-cli@11}"
for f in *.mmd; do
  $MMDC -q -p "$cfg" -i "$f" -o "png/${f%.mmd}.png" -b white -s 2 -w 1600
  echo "rendered png/${f%.mmd}.png"
done
rm -f "$cfg"
