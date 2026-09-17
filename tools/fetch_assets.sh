#!/usr/bin/env bash
# Fetches every third-party binary asset this project needs. Nothing
# large is ever committed to the repo -- re-running this script must
# deterministically reproduce assets/ from scratch.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FONTS_DIR="${AG_FONTS_DIR:-$ROOT/assets/fonts}"
AUDIO_DIR="${AG_AUDIO_DIR:-$ROOT/assets/audio}"
mkdir -p "$FONTS_DIR" "$AUDIO_DIR"

UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"

echo "== fonts =="
# Oswald ExtraLight (200): condensed uppercase-friendly sans measuring
# stroke/cap-height ~0.06 (spec 7's threshold -- Bebas Neue measured
# ~0.14 and was rejected; heavier Oswald weights measured ~0.08-0.11).
curl -sSL -A "$UA" -o "$FONTS_DIR/Oswald-ExtraLight.ttf" \
  "https://fonts.gstatic.com/s/oswald/v57/TK3_WkUHHAIjg75cFRf3bXL8LICs13FvgUE.ttf"

# Archivo weight 560 target: Google Fonts CSS2 API only serves static
# instances (500/600) with format=truetype, not the exact variable
# weight. 600 (SemiBold) is the nearest static instance and is used as
# a documented substitution -- see assets/manifest.json substitutable flag.
curl -sSL -A "$UA" -o "$FONTS_DIR/Archivo-SemiBold.ttf" \
  "https://fonts.gstatic.com/s/archivo/v25/k3k6o8UDI-1M0wlSV9XAw6lQkqWY8Q82sJaRE-NWIDdgffTT6jRp8A.ttf"

echo "== audio =="
if [ -n "${AG_BGM_SOURCE_URL:-}" ]; then
  curl -sSL -A "$UA" -o "$AUDIO_DIR/source.mp3" "$AG_BGM_SOURCE_URL"
else
  cat >&2 <<'EOF'
No AG_BGM_SOURCE_URL set, and every stock-CC0-audio host tried from this
session (archive.org, freesound.org, pixabay, mixkit, soundbible, ...) is
blocked by the outbound network policy here -- only fonts.googleapis.com /
fonts.gstatic.com are reachable. Per the agent-proxy runbook, blocked hosts
are reported, not routed around.

To finish spec section 8, supply a CC0 track yourself:
  AG_BGM_SOURCE_URL=https://.../track.mp3 tools/fetch_assets.sh
or drop a file directly at assets/audio/source.mp3.
tools/make_bgm.py will then time-stretch/filter/master it as specified.
EOF
fi

python3 "$ROOT/tools/make_manifest.py"
echo "done."
