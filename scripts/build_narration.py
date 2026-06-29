#!/usr/bin/env python3
"""Build a time-locked narration MP3 for the Movin demo.

The script creates one audio file per narration segment, then pads or speed-adjusts
that segment so it exactly matches the start/end timestamps in data/narration.json.
This keeps the spoken narration, transcript highlighting and final MP4 aligned.
"""
from __future__ import annotations

import json
import asyncio
import math
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NARRATION_JSON = ROOT / "data" / "narration.json"
OUT_DIR = ROOT / "assets" / "generated"
TMP_DIR = OUT_DIR / "narration_parts"
TXT_OUT = OUT_DIR / "narration_script.txt"
CONCAT_FILE = TMP_DIR / "audio_concat.txt"
MP3_OUT = OUT_DIR / "narration.mp3"
INTRO_MP3_OUT = OUT_DIR / "intro.mp3"
EDGE_VOICE = "en-GB-RyanNeural"
EDGE_RATE = "+0%"


def run(cmd: list[str]) -> None:
    print("+", " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True)


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path)
    ], text=True).strip()
    return float(out)


def atempo_chain(factor: float) -> str:
    """ffmpeg atempo supports 0.5-100, but chaining around 0.5-2 is safer."""
    parts: list[float] = []
    while factor > 2.0:
        parts.append(2.0)
        factor /= 2.0
    while factor < 0.5:
        parts.append(0.5)
        factor /= 0.5
    parts.append(factor)
    return ",".join(f"atempo={p:.6f}" for p in parts)


async def synthesize_edge_tts(text: str, out_mp3: Path) -> None:
    import edge_tts  # type: ignore

    communicate = edge_tts.Communicate(text, voice=EDGE_VOICE, rate=EDGE_RATE)
    await communicate.save(str(out_mp3))


def synthesize_espeak(text: str, out_wav: Path) -> None:
    espeak = shutil.which("espeak-ng") or shutil.which("espeak")
    if not espeak:
        raise RuntimeError("espeak-ng/espeak not found")
    run([espeak, "-v", "en-gb", "-s", "145", "-p", "35", "-a", "165", "-w", str(out_wav), text.replace("—", ", ")])


def synthesize_gtts(text: str, out_mp3: Path) -> None:
    from gtts import gTTS  # type: ignore
    tts = gTTS(text, lang="en", tld="co.uk", slow=False)
    tts.save(str(out_mp3))


def synthesize_segment(text: str, raw_path: Path) -> None:
    try:
        asyncio.run(synthesize_edge_tts(text, raw_path.with_suffix(".mp3")))
        return
    except ImportError:
        print("edge-tts is not installed; falling back to local British English TTS.")
    except Exception as exc:
        print(f"{EDGE_VOICE} synthesis failed ({exc}); falling back to local British English TTS.")

    if shutil.which("espeak-ng") or shutil.which("espeak"):
        synthesize_espeak(text, raw_path.with_suffix(".wav"))
        return
    try:
        synthesize_gtts(text, raw_path.with_suffix(".mp3"))
        return
    except Exception as exc:
        raise SystemExit("Unable to create narration. Install ffmpeg plus edge-tts, espeak-ng, or gTTS.") from exc


def existing_raw(raw_base: Path) -> Path:
    for suffix in (".wav", ".mp3"):
        p = raw_base.with_suffix(suffix)
        if p.exists():
            return p
    raise FileNotFoundError(raw_base)


def fit_to_duration(src: Path, dest: Path, target: float) -> None:
    actual = max(0.1, ffprobe_duration(src))
    filters: list[str] = []
    if actual > target:
        speed = actual / target
        filters.append(atempo_chain(speed))
    else:
        silence = target - actual
        filters.append(f"apad=pad_dur={silence:.3f}")
    filters.append(f"atrim=0:{target:.3f}")
    filters.append("asetpts=N/SR/TB")
    run(["ffmpeg", "-y", "-i", str(src), "-af", ",".join(filters), "-ar", "44100", "-ac", "2", str(dest)])


def main() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("ffmpeg and ffprobe are required.")

    data = json.loads(NARRATION_JSON.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    TXT_OUT.write_text("\n\n".join([data.get("intro", {}).get("text", "")] + [seg["text"] for seg in data["segments"]]), encoding="utf-8")

    intro = data.get("intro")
    if intro and intro.get("text"):
        intro_raw_base = TMP_DIR / "00_intro_raw"
        intro_fitted = TMP_DIR / "00_intro_fitted.wav"
        synthesize_segment(intro["text"], intro_raw_base)
        intro_raw = existing_raw(intro_raw_base)
        intro_duration = math.ceil(ffprobe_duration(intro_raw) * 1000) / 1000
        fit_to_duration(intro_raw, intro_fitted, intro_duration)
        run(["ffmpeg", "-y", "-i", str(intro_fitted), "-codec:a", "libmp3lame", "-q:a", "3", str(INTRO_MP3_OUT)])
        print(f"Created {INTRO_MP3_OUT.relative_to(ROOT)} ({ffprobe_duration(INTRO_MP3_OUT):.2f}s)")

    fitted_paths: list[Path] = []
    for idx, seg in enumerate(data["segments"], start=1):
        target = float(seg["end"] - seg["start"])
        safe_id = seg["id"].replace("/", "_")
        raw_base = TMP_DIR / f"{idx:02d}_{safe_id}_raw"
        fitted = TMP_DIR / f"{idx:02d}_{safe_id}_fitted.wav"
        synthesize_segment(seg["text"], raw_base)
        raw = existing_raw(raw_base)
        fit_to_duration(raw, fitted, target)
        fitted_paths.append(fitted)

    CONCAT_FILE.write_text("".join(f"file '{p.as_posix()}'\n" for p in fitted_paths), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(CONCAT_FILE), "-codec:a", "libmp3lame", "-q:a", "3", str(MP3_OUT)])
    print(f"Created {MP3_OUT.relative_to(ROOT)} ({ffprobe_duration(MP3_OUT):.2f}s)")


if __name__ == "__main__":
    main()
