#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "assets" / "video-manifest.json"
CLIPS_DIR = ROOT / "assets" / "clips"
MAX_MB = 20.3


def main() -> None:
    if not MANIFEST.exists():
        raise SystemExit(
            "assets/video-manifest.json is missing. Run COLAB_VIDEO_PROCESSOR.ipynb, download movin_github_assets_under_20mb.zip, and unzip it into the repo root."
        )
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    clips = data.get("clips", [])
    if not clips:
        raise SystemExit("video-manifest.json has no clips.")

    missing = []
    too_large = []
    for clip in clips:
        p = ROOT / clip["src"]
        if not p.exists():
            missing.append(clip["src"])
            continue
        mb = p.stat().st_size / (1024 * 1024)
        if mb > MAX_MB:
            too_large.append(f"{clip['src']} ({mb:.1f} MB)")
    if missing:
        raise SystemExit("Missing clips:\n" + "\n".join(missing))
    if too_large:
        raise SystemExit("Clips above 20MB:\n" + "\n".join(too_large))

    total = sum(float(c.get("duration", 0)) for c in clips)
    print(f"Validated {len(clips)} clips. Total stitched duration from manifest: {total:.1f}s")
    print("Largest clip:", max((ROOT / c["src"]).stat().st_size / (1024*1024) for c in clips), "MB")


if __name__ == "__main__":
    main()
