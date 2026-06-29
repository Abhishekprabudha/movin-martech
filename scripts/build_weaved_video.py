#!/usr/bin/env python3
"""Stitch Colab-generated clips into a final synchronized Movin demo MP4.

Expected inputs:
  assets/video-manifest.json
  assets/clips/*.mp4          # each clip < 20 MB, created by Colab processor
  assets/generated/narration.mp3

Output:
  assets/generated/movin_martech_weaved.mp4
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets" / "video-manifest.json"
SAMPLE_MANIFEST = ROOT / "assets" / "video-manifest.sample.json"
OUT_DIR = ROOT / "assets" / "generated"
CONCAT_FILE = OUT_DIR / "concat.txt"
SILENT_STITCH = OUT_DIR / "movin_martech_silent_stitch.mp4"
NARRATION = OUT_DIR / "narration.mp3"
FINAL = OUT_DIR / "movin_martech_weaved.mp4"
MAX_CLIP_MB = 20.0


def run(cmd: list[str]) -> None:
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def ensure_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is required to build the final video.")


def load_manifest() -> dict:
    manifest_path = MANIFEST if MANIFEST.exists() else SAMPLE_MANIFEST
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    clips = data.get("clips", [])
    if not clips:
        raise SystemExit("No clips found in video manifest.")
    return data


def validate_clips(clips: list[dict]) -> list[Path]:
    paths: list[Path] = []
    missing: list[str] = []
    too_large: list[str] = []
    for clip in clips:
        p = ROOT / clip["src"]
        if not p.exists():
            missing.append(str(p.relative_to(ROOT)))
            continue
        mb = p.stat().st_size / (1024 * 1024)
        if mb > MAX_CLIP_MB + 0.3:
            too_large.append(f"{p.relative_to(ROOT)} ({mb:.1f} MB)")
        paths.append(p)
    if missing:
        raise SystemExit("Missing clip files. Run the Colab processor and upload these paths:\n" + "\n".join(missing))
    if too_large:
        raise SystemExit("These clips are over 20 MB. Re-run Colab with a lower target size or higher CRF:\n" + "\n".join(too_large))
    return paths


def write_concat(paths: list[Path]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    for p in paths:
        lines.append(f"file '{p.as_posix()}'")
    CONCAT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def stitch_video() -> None:
    # Re-encode for maximum compatibility across clips created from different source videos.
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(CONCAT_FILE),
        "-vf", "scale=1280:-2,fps=24,format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "28",
        "-an", "-movflags", "+faststart", str(SILENT_STITCH)
    ])


def add_narration() -> None:
    if not NARRATION.exists():
        raise SystemExit("Narration MP3 missing. Run scripts/build_narration.py first.")
    # If video is shorter than narration, freeze the last frame. If it is longer, shortest keeps the demo tight.
    run([
        "ffmpeg", "-y", "-i", str(SILENT_STITCH), "-i", str(NARRATION),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-shortest", "-movflags", "+faststart", str(FINAL)
    ])


def main() -> None:
    ensure_ffmpeg()
    data = load_manifest()
    paths = validate_clips(data["clips"])
    write_concat(paths)
    stitch_video()
    add_narration()
    size_mb = FINAL.stat().st_size / (1024 * 1024)
    print(f"Created {FINAL.relative_to(ROOT)} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
