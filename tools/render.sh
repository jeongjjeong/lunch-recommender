#!/usr/bin/env bash
# Thin entry point: fetch assets if missing, then render the full
# 652-frame sequence to out/glow_typo_sequence.mp4.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -f "${AG_FONTS_DIR:-$ROOT/assets/fonts}/BebasNeue-Regular.ttf" ]; then
  "$ROOT/tools/fetch_assets.sh"
fi

if [ -f "${AG_AUDIO_DIR:-$ROOT/assets/audio}/source.mp3" ] && [ ! -f "${AG_AUDIO_DIR:-$ROOT/assets/audio}/bgm.wav" ]; then
  python3 "$ROOT/tools/make_bgm.py"
fi

python3 "$ROOT/tools/render_frames.py" "$@"
