#!/usr/bin/env python3
"""Writes assets/manifest.json: logical name, path, required/substitutable,
provenance, and sha256 for every third-party binary this project uses.
Also doubles as the "matches what's on disk" check when run with --verify.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ag import paths  # noqa: E402


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


ENTRIES = [
    dict(
        name="headline_font",
        path=paths.HEADLINE_FONT,
        required=True,
        substitutable=False,
        source="https://fonts.google.com/specimen/Oswald (OFL, via fonts.gstatic.com)",
        note="condensed sans, weight 200 (ExtraLight) measured stroke/cap-height "
        "ratio ~0.060, matching spec section 7's ~0.06 target. Bebas Neue "
        "(the spec's suggested family) measured ~0.14 and was rejected; "
        "heavier Oswald weights measured ~0.08-0.11.",
    ),
    dict(
        name="caption_font",
        path=paths.CAPTION_FONT,
        required=True,
        substitutable=True,
        source="https://fonts.google.com/specimen/Archivo (OFL, via fonts.gstatic.com)",
        note="target weight 560; Google Fonts CSS2 API only serves static "
        "500/600 instances with format=truetype, so 600 (SemiBold) is used "
        "as the nearest static substitute for the variable-font weight.",
    ),
    dict(
        name="bgm_source",
        path=paths.BGM_SOURCE,
        required=False,
        substitutable=True,
        source="user-supplied CC0 track (AG_BGM_SOURCE_URL)",
        note="every stock CC0-audio host reachable from a normal machine "
        "(archive.org, freesound.org, pixabay, mixkit, soundbible, ...) is "
        "blocked by this session's outbound network allowlist -- only "
        "fonts.googleapis.com/fonts.gstatic.com are reachable here. Section "
        "8 is otherwise fully implemented in tools/make_bgm.py; it just "
        "needs a source file supplied from outside this sandbox.",
    ),
]


def build():
    manifest = []
    for e in ENTRIES:
        p = Path(e["path"])
        manifest.append(
            {
                "name": e["name"],
                "path": str(p.relative_to(paths.ROOT)) if p.is_relative_to(paths.ROOT) else str(p),
                "required": e["required"],
                "substitutable": e["substitutable"],
                "present": p.exists(),
                "source": e["source"],
                "note": e["note"],
                "sha256": sha256(p),
            }
        )
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    manifest = build()

    if args.verify:
        if not paths.ASSET_MANIFEST.exists():
            raise SystemExit("no manifest.json to verify against")
        recorded = {e["name"]: e for e in json.loads(paths.ASSET_MANIFEST.read_text())}
        ok = True
        for e in manifest:
            r = recorded.get(e["name"])
            if r is None:
                print(f"NEW: {e['name']}")
                continue
            if e["present"] and r["sha256"] != e["sha256"]:
                print(f"MISMATCH: {e['name']} sha256 changed")
                ok = False
            elif e["required"] and not e["present"]:
                print(f"MISSING (required): {e['name']}")
                ok = False
        print("OK" if ok else "FAILED")
        raise SystemExit(0 if ok else 1)

    paths.ASSET_MANIFEST.write_text(json.dumps(manifest, indent=2))
    print("wrote", paths.ASSET_MANIFEST)
    for e in manifest:
        flag = "ok" if e["present"] else ("MISSING(required)" if e["required"] else "missing(optional)")
        print(f"  {e['name']:16s} {flag}")


if __name__ == "__main__":
    main()
