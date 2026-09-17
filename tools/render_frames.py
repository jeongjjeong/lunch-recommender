#!/usr/bin/env python3
"""Renders all 652 frames and pipes them straight into ffmpeg -- no
intermediate PNG sequence on disk, spec section 0's h264 CRF16 preset
slow yuv420p faststart + AAC 192k, muxed with the (optional) mastered
BGM from tools/make_bgm.py.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ag import paths, scenes  # noqa: E402

paths.check_numpy_blas()

from ag.render import render_frame, W, H  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(paths.OUT_DIR / "glow_typo_sequence.mp4"))
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=scenes.FRAME_COUNT)
    ap.add_argument("--audio", default=str(paths.BGM_OUT))
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    has_audio = Path(args.audio).exists()

    video_tmp = out_path.with_suffix(".video.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
        "-r", str(scenes.FPS), "-i", "-",
        "-an",
        "-c:v", "libx264", "-crf", "16", "-preset", "slow",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(video_tmp),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    t0 = time.time()
    n = args.end - args.start
    for i, f in enumerate(range(args.start, args.end)):
        frame = render_frame(f)
        proc.stdin.write(frame.tobytes())
        if i % 25 == 0 or i == n - 1:
            elapsed = time.time() - t0
            rate = (i + 1) / max(elapsed, 1e-6)
            eta = (n - i - 1) / max(rate, 1e-6)
            print(f"frame {f} ({i+1}/{n})  {rate:.2f} fps  eta {eta:.0f}s", flush=True)

    proc.stdin.close()
    ret = proc.wait()
    if ret != 0:
        raise SystemExit(f"ffmpeg video pass failed: {ret}")

    if has_audio:
        mux_cmd = [
            "ffmpeg", "-y",
            "-i", str(video_tmp), "-i", str(args.audio),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart",
            str(out_path),
        ]
        subprocess.run(mux_cmd, check=True)
        video_tmp.unlink()
    else:
        video_tmp.rename(out_path)
        print("NOTE: no mastered BGM found at", args.audio,
              "-- shipped video-only. Run tools/make_bgm.py once a CC0 "
              "source track is available at assets/audio/source.mp3.")

    print("done ->", out_path)


if __name__ == "__main__":
    main()
