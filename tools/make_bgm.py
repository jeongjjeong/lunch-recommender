#!/usr/bin/env python3
"""Section 8: turns one CC0 source track into the mastered BGM bed.

1. Measure the source's BPM, time-stretch to 96.6 BPM (librosa phase
   vocoder -- handles an arbitrary ratio in one shot, no ffmpeg atempo
   chaining needed).
2. Auto-pick the densest 24s window (highest mean RMS energy).
3. Cutoff/gain follows the picture via data/tones.json's per-scene
   markers: muffled (~800Hz) while letters are still being typed on,
   opens up (~11.8kHz) at ignition, closes again through outfade.
   Implemented as an ffmpeg lowpass with a `sendcmd` automation script
   instead of a single static filter.
4. A sub-boom (58->30Hz exponential sweep + short click) is layered in
   at every scene cut and ignition point.
5. Mastering is a single linear-gain loudnorm pass using *measured*
   parameters from an explicit first analysis pass -- never the 1-pass
   dynamic-gain mode, whose time-varying gain shifts with the ffmpeg
   version and would re-pump the fade sections on every rebuild.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ag import paths, scenes  # noqa: E402

TARGET_BPM = 96.6
WINDOW_SECONDS = 24.0
SR = 48000


def measure_bpm_and_stretch(src_path: Path, out_path: Path):
    import librosa
    import numpy as np
    import soundfile as sf

    y, sr = librosa.load(str(src_path), sr=SR, mono=False)
    y_mono = y if y.ndim == 1 else y.mean(axis=0)

    tempo, _ = librosa.beat.beat_track(y=y_mono, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])
    if tempo <= 0:
        tempo = TARGET_BPM

    ratio = tempo / TARGET_BPM  # time_stretch rate>1 speeds up (shortens)
    if y.ndim == 1:
        stretched = librosa.effects.time_stretch(y, rate=ratio)
    else:
        stretched = np.stack([librosa.effects.time_stretch(ch, rate=ratio) for ch in y])

    sf.write(str(out_path), stretched.T if stretched.ndim > 1 else stretched, sr)
    return tempo, ratio


def pick_densest_window(path: Path, window_s: float = WINDOW_SECONDS) -> float:
    import librosa
    import numpy as np

    y, sr = librosa.load(str(path), sr=SR, mono=True)
    hop = 2048
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    frames_per_window = int(window_s * sr / hop)
    if len(rms) <= frames_per_window:
        return 0.0
    csum = np.cumsum(np.insert(rms, 0, 0))
    windowed = csum[frames_per_window:] - csum[:-frames_per_window]
    best = int(np.argmax(windowed))
    return best * hop / sr


def scene_local_times():
    """Where each scene's audio-relevant local timeline sits within the
    24s window, assuming the 5 scenes play back-to-back starting at 0."""
    scene_dur = scenes.SCENE_LEN / scenes.FPS
    return {s.id: i * scene_dur for i, s in enumerate(scenes.SCENES)}


def main():
    if not paths.BGM_SOURCE.exists():
        print(f"no source track at {paths.BGM_SOURCE} -- nothing to master.", file=sys.stderr)
        print("supply one via AG_BGM_SOURCE_URL to tools/fetch_assets.sh, "
              "or drop a CC0 file there directly.", file=sys.stderr)
        raise SystemExit(1)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        stretched_path = tmp_dir / "stretched.wav"
        tempo, ratio = measure_bpm_and_stretch(paths.BGM_SOURCE, stretched_path)
        print(f"measured BPM {tempo:.1f} -> stretched by {ratio:.4f} to {TARGET_BPM} BPM")

        window_start = pick_densest_window(stretched_path)
        print(f"densest {WINDOW_SECONDS}s window starts at {window_start:.2f}s")

        window_path = tmp_dir / "window.wav"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(stretched_path), "-ss", f"{window_start:.3f}",
             "-t", str(WINDOW_SECONDS), str(window_path)],
            check=True,
        )

        tones = json.loads((paths.DATA_DIR / "tones.json").read_text())
        local_times = scene_local_times()

        # merge every scene's cue lines into one automation script
        cue_lines = []
        for s in scenes.SCENES:
            cfg = tones["scenes"][s.id]
            base = local_times[s.id]
            cue_lines.append(f"{base:.3f} tone f {tones['letters_lpf_hz']};\n")
            cue_lines.append(f"{base + cfg['ignite_at']:.3f} tone f {tones['ignite_lpf_hz']};\n")
            if cfg.get("outfade_at") is not None:
                cue_lines.append(f"{base + cfg['outfade_at']:.3f} tone f {tones['outfade_lpf_hz']};\n")
        cue_path = tmp_dir / "cues.txt"
        cue_path.write_text("".join(sorted(cue_lines, key=lambda l: float(l.split()[0]))))

        toned_path = tmp_dir / "toned.wav"
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(window_path),
                "-af",
                f"asendcmd=f='{cue_path}',lowpass@tone=f={tones['letters_lpf_hz']}:width_type=h:width=200",
                str(toned_path),
            ],
            check=True,
        )

        # sub-booms at scene cuts + ignition points
        boom_times = []
        for s in scenes.SCENES:
            cfg = tones["scenes"][s.id]
            boom_times.append(local_times[s.id])
            boom_times.append(local_times[s.id] + cfg["ignite_at"])
        boom_times = [t for t in boom_times if 0 <= t < WINDOW_SECONDS]

        boomed_path = tmp_dir / "boomed.wav"
        filter_parts = []
        amix_inputs = ["[base]"]
        pre = "[0:a]asplit=1[base];"
        for i, t in enumerate(boom_times):
            filter_parts.append(
                f"aevalsrc='0.9*sin(2*PI*(58-28*min(t/0.3\\,1))*t)*exp(-4*t)':"
                f"d=0.4:s={SR}[boom{i}];"
                f"[boom{i}]adelay={int(t*1000)}|{int(t*1000)}[boomd{i}]"
            )
            amix_inputs.append(f"[boomd{i}]")
        filtergraph = pre + ";".join(filter_parts) + ";" + "".join(amix_inputs) + \
            f"amix=inputs={len(amix_inputs)}:normalize=0[mixed]"

        subprocess.run(
            ["ffmpeg", "-y", "-i", str(toned_path), "-filter_complex", filtergraph,
             "-map", "[mixed]", str(boomed_path)],
            check=True,
        )

        # 2-pass linear loudnorm: measure, then apply with fixed gain
        measure = subprocess.run(
            ["ffmpeg", "-i", str(boomed_path), "-af",
             "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
            capture_output=True, text=True,
        )
        stderr = measure.stderr
        json_start = stderr.rfind("{")
        measured = json.loads(stderr[json_start:])

        paths.BGM_OUT.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(boomed_path), "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11:linear=true:"
                f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
                f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}",
                "-ar", "48000", str(paths.BGM_OUT),
            ],
            check=True,
        )

    print("wrote", paths.BGM_OUT)


if __name__ == "__main__":
    main()
