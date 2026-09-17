"""Environment-driven paths + the numpy/BLAS sanity guard.

Every other module reaches the filesystem through this module. No
absolute paths are hard-coded anywhere else in the codebase; every
constant here can be overridden with an environment variable.
"""
from __future__ import annotations

import os
from pathlib import Path


def _env_path(name: str, default: Path) -> Path:
    v = os.environ.get(name)
    return Path(v).resolve() if v else default.resolve()


ROOT = Path(__file__).resolve().parent.parent

ASSETS_DIR = _env_path("AG_ASSETS_DIR", ROOT / "assets")
FONTS_DIR = _env_path("AG_FONTS_DIR", ASSETS_DIR / "fonts")
AUDIO_DIR = _env_path("AG_AUDIO_DIR", ASSETS_DIR / "audio")
DATA_DIR = _env_path("AG_DATA_DIR", ROOT / "data")
CACHE_DIR = _env_path("AG_CACHE_DIR", ROOT / "cache")
OUT_DIR = _env_path("AG_OUT_DIR", ROOT / "out")
CONTENT_JSON = _env_path("AG_CONTENT_JSON", ROOT / "content.json")

HEADLINE_FONT = FONTS_DIR / "Oswald-ExtraLight.ttf"
CAPTION_FONT = FONTS_DIR / "Archivo-SemiBold.ttf"
BGM_SOURCE = AUDIO_DIR / "source.mp3"
BGM_OUT = AUDIO_DIR / "bgm.wav"
ASSET_MANIFEST = ASSETS_DIR / "manifest.json"

for d in (ASSETS_DIR, FONTS_DIR, AUDIO_DIR, DATA_DIR, CACHE_DIR, OUT_DIR):
    d.mkdir(parents=True, exist_ok=True)


def check_numpy_blas() -> None:
    """Guard against the Apple-Accelerate + numpy-2.2.x silent-corruption trap.

    On macOS, numpy 2.2.x wheels built against Apple's Accelerate BLAS
    have been observed to silently miscompute plain elementwise
    arithmetic on large arrays (no exception, no warning -- frames just
    render hundreds of times too dark, or writes from two different
    arrays bleed into each other). That combination must never be used
    for this renderer's full-frame array math.
    """
    import numpy as np

    version = tuple(int(p) for p in np.__version__.split(".")[:2])
    try:
        blas_name = (
            np.show_config("dicts")
            .get("Build Dependencies", {})
            .get("blas", {})
            .get("name", "")
        )
    except Exception:
        blas_name = ""

    if "accelerate" in blas_name.lower() and version < (2, 3):
        raise RuntimeError(
            "numpy %s is linked against Apple Accelerate BLAS. This "
            "combination is known to silently corrupt full-frame array "
            "arithmetic (no exception raised). Upgrade to a numpy build "
            "linked against scipy-openblas (numpy>=2.3, or reinstall the "
            "manylinux/PyPI wheel instead of a conda/Accelerate build) "
            "before rendering." % np.__version__
        )
