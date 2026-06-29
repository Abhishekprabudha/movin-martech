# Movin Marketing Technology OS — Google Colab Video Processor
# Paste this entire file into a Google Colab notebook cell and run it.
# It lets you upload the 4 original Movin recordings, creates <20MB GitHub-safe clips,
# generates assets/video-manifest.json, creates a time-locked narration MP3, and builds a preview MP4.

import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

# =========================
# 1) CONFIGURATION
# =========================
TARGET_CLIP_MB = 18.5       # Keep below GitHub web upload comfort threshold. Do not set above 19.5.
VIDEO_WIDTH = 1280          # 1280 = HD. Use 960 if you want smaller files.
VIDEO_FPS = 18              # Good for screen recordings. Use 15 if files remain large.
VIDEO_CRF = 31              # Higher = smaller/lower quality. Try 33 if any clip remains too large.
BUILD_PREVIEW_MP4 = True    # Creates /content/movin_colab_output/movin_martech_weaved_preview.mp4.

# Edit start_seconds if your best screen appears later in any video.
# The target durations match the 5-minute narration timeline.
SEQUENCE_PLAN = [
    {
        "label": "01_aeo_geo_intelligence",
        "chapter": "AEO + GEO Intelligence / Opportunity Engine",
        "match_any": ["06-04", "12.11.10", "12.11", "screen recording 2026-06-04"],
        "fallback_order": 1,
        "start_seconds": 0,
        "target_duration": 140,
        "narrationSegmentIds": ["opening", "aeo_geo", "prompt_intelligence", "opportunity_engine"],
    },
    {
        "label": "02_lead_generation",
        "chapter": "WarmLead AI / Lead Generation",
        "match_any": ["06-02", "6.26.34", "screen recording 2026-06-02"],
        "fallback_order": 2,
        "start_seconds": 0,
        "target_duration": 40,
        "narrationSegmentIds": ["lead_generation"],
    },
    {
        "label": "03_autonomous_campaigns_syndication",
        "chapter": "Autonomous Campaign Generation + Syndication",
        "match_any": ["elevateos", "demo_elevateos", "campaign"],
        "fallback_order": 3,
        "start_seconds": 0,
        "target_duration": 75,
        "narrationSegmentIds": ["campaign_generation", "syndication"],
    },
    {
        "label": "04_data_monetization",
        "chapter": "B2B Shipment Data Monetization",
        "match_any": ["de3mo", "meeting recording", "20260609", "data"],
        "fallback_order": 4,
        "start_seconds": 0,
        "target_duration": 45,
        "narrationSegmentIds": ["data_monetization", "close"],
    },
]

NARRATION_DATA = {
  "title": "Movin Marketing Technology OS — From AI Discovery to Monetized Growth",
  "durationSeconds": 300,
  "segments": [
    {"id":"opening","start":0,"end":25,"chapter":"Opening","headline":"A full-funnel AI growth engine for Movin","text":"Today, Movin is not just looking at marketing as campaigns. Movin is building an intelligent growth engine — one that understands how customers discover logistics providers, what they ask AI engines, which accounts are showing intent, which campaigns should be launched, and how shipment data itself can become a monetizable business asset. This is the end-to-end Movin Marketing Technology Operating System."},
    {"id":"aeo_geo","start":25,"end":65,"chapter":"AEO + GEO Intelligence","headline":"Move from search visibility to AI answer ownership","text":"We start with the Movin AI Command Center. Buyers are no longer discovering logistics partners only through Google search or sales outreach. They are asking AI engines: ChatGPT, Perplexity, Gemini, Copilot and Google AI Overviews. That is why Movin needs AEO — Answer Engine Optimization — and GEO — Generative Engine Optimization. The platform tracks whether Movin appears in AI-generated answers, whether Movin is cited, which pages are referenced, which prompts trigger visibility, and where competitors are being recommended instead."},
    {"id":"prompt_intelligence","start":65,"end":105,"chapter":"Prompt + Intent Intelligence","headline":"Turn customer questions into demand signals","text":"Next, the system moves from visibility to intent. The Prompt Intelligence view shows what customers are actually asking: best logistics partner for India to UAE, real-time freight tracking, last-mile SLA for enterprise, warehouse fulfilment comparison, cross-border e-commerce logistics, reverse logistics and freight pricing. These are not keywords. These are buying questions. The platform groups these prompts by customer intent, volume, quality of Movin’s response and next best action."},
    {"id":"opportunity_engine","start":105,"end":140,"chapter":"Opportunity Engine","headline":"Convert AI visibility gaps into execution priorities","text":"The Opportunity Engine converts intelligence into action. It rank-orders the highest-value plays by visibility gap, business impact, effort and priority. For Movin, this can mean shipment tracking prompts, India to UAE logistics comparisons, last-mile SLA queries, reverse logistics and pricing transparency. Marketing teams often know there is a visibility gap, but not what to do next. Here, the system turns that gap into a clear quarterly execution plan."},
    {"id":"lead_generation","start":140,"end":180,"chapter":"Lead Generation","headline":"Warm accounts before outreach begins","text":"Once demand is understood, the system moves into lead generation. The WarmLead AI layer scans external and internal signals: LinkedIn, news, procurement activity, company websites, public announcements, forums and funding signals. It identifies warm accounts, scores intent and fit, enriches contacts and creates segmented lists. Instead of cold outreach, Movin’s sales and marketing teams now work from a live revenue signal graph."},
    {"id":"campaign_generation","start":180,"end":225,"chapter":"Autonomous Campaign Generation","headline":"Agents create and optimize the campaign factory","text":"Now the platform becomes autonomous. Based on the opportunity, the campaign agent generates the audience, objective, platform, budget, creative tone and campaign duration. Then multiple agents run in sequence: competitive analysis, social listening, market opportunity analysis, strategy synthesis, creative generation, budget optimization, pixel and conversion setup, and launch. For Movin, this can create campaigns around real-time freight tracking, India to UAE shipping, last-mile SLA assurance, reverse logistics and cross-border logistics for growing businesses."},
    {"id":"syndication","start":225,"end":255,"chapter":"Campaign Syndication","headline":"Push the same intelligence across content, CRM and media","text":"Once campaigns are generated, the system syndicates them across channels. Some assets go into AEO and GEO content pages. Some go into paid media. Some become landing pages, calculators, comparison pages, sales emails, WhatsApp nudges or CRM sequences. A high-intent prompt becomes a page. A page becomes a lead. A lead becomes a CRM record. A CRM record becomes sales follow-up."},
    {"id":"data_monetization","start":255,"end":290,"chapter":"Data Monetization","headline":"Every shipment becomes a monetizable signal","text":"The final layer is what makes this uniquely powerful for Movin: data monetization. Every shipment creates structured metadata: origin, destination, weight, dimensions, category, service level and procurement context. That data becomes an intent signal. The platform can recommend supplier offers, packaging, labels, procurement discounts and freight unlocks. Movin does not only move shipments. Movin monetizes the intelligence around shipments."},
    {"id":"close","start":290,"end":300,"chapter":"Close","headline":"Movin’s AI-powered growth operating system","text":"The complete Movin marketing-tech flow is clear: discover demand, understand intent, generate leads, launch campaigns, syndicate content, convert accounts and monetize shipment data. This is not a campaign platform. This is Movin’s AI-powered growth operating system."}
  ]
}

# =========================
# 2) INSTALL + HELPERS
# =========================
def run(cmd, check=True, quiet=False):
    print("+", " ".join(map(str, cmd)) if isinstance(cmd, (list, tuple)) else cmd)
    return subprocess.run(cmd, shell=isinstance(cmd, str), check=check, stdout=subprocess.DEVNULL if quiet else None, stderr=subprocess.STDOUT if quiet else None)

run("apt-get -qq update && apt-get -qq install -y ffmpeg", quiet=False)
run([sys.executable, "-m", "pip", "install", "-q", "edge-tts", "gTTS"], quiet=False)

ROOT = Path("/content/movin_colab_output")
RAW_DIR = ROOT / "raw_uploads"
WORK_DIR = ROOT / "work"
ASSET_DIR = ROOT / "github_assets"
CLIPS_DIR = ASSET_DIR / "assets" / "clips"
GEN_DIR = ASSET_DIR / "assets" / "generated"
DATA_DIR = ASSET_DIR / "data"
for d in [RAW_DIR, WORK_DIR, CLIPS_DIR, GEN_DIR, DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def ffprobe_duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], text=True).strip()
    return float(out)


def size_mb(path):
    return Path(path).stat().st_size / (1024 * 1024)


def slug_name(name):
    return re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()


def fit_atempo_chain(factor):
    parts = []
    while factor > 2.0:
        parts.append(2.0)
        factor /= 2.0
    while factor < 0.5:
        parts.append(0.5)
        factor /= 0.5
    parts.append(factor)
    return ",".join(f"atempo={p:.6f}" for p in parts)

# =========================
# 3) UPLOAD THE 4 VIDEOS
# =========================
try:
    from google.colab import files
    print("Upload the 4 original Movin videos now. You can select all four together.")
    uploaded = files.upload()
    for name, content in uploaded.items():
        out = RAW_DIR / name
        out.write_bytes(content)
except Exception:
    print("Not running inside Colab upload UI. Put your 4 videos in:", RAW_DIR)

videos = sorted([p for p in RAW_DIR.iterdir() if p.suffix.lower() in [".mp4", ".mov", ".m4v", ".webm", ".mkv"]])
if len(videos) < 4:
    raise SystemExit(f"Expected 4 videos, found {len(videos)} in {RAW_DIR}. Upload all 4 recordings and re-run.")

print("\nUploaded videos:")
for p in videos:
    print(f"- {p.name} | {ffprobe_duration(p):.1f}s | {size_mb(p):.1f} MB")

# =========================
# 4) MAP VIDEOS TO MOVIN STORY SEQUENCE
# =========================
def match_video(plan_item, remaining):
    keys = [k.lower() for k in plan_item["match_any"]]
    for p in remaining:
        name = p.name.lower()
        if any(k in name for k in keys):
            return p
    return None

remaining = videos[:]
assignments = []
for plan in SEQUENCE_PLAN:
    found = match_video(plan, remaining)
    if found is None:
        # fallback by upload order after filename matching fails
        found = remaining[0]
    remaining.remove(found)
    assignments.append((plan, found))

print("\nStory mapping:")
for plan, src in assignments:
    print(f"- {plan['label']}  <=  {src.name}")

# =========================
# 5) CREATE 5-MINUTE HIGHLIGHT VIDEO CLIPS
# =========================
def build_highlight_clip(src, plan):
    source_duration = ffprobe_duration(src)
    start = float(plan.get("start_seconds", 0))
    target = float(plan["target_duration"])
    available = max(1.0, source_duration - start)
    capture_duration = min(target, available)
    speed_ratio = target / capture_duration
    # speed_ratio > 1 slows video down to fill target; speed_ratio = 1 normal speed
    vf = f"scale='min({VIDEO_WIDTH},iw)':-2,fps={VIDEO_FPS},setpts={speed_ratio:.6f}*PTS,trim=duration={target:.3f},format=yuv420p"
    out = WORK_DIR / f"{plan['label']}_highlight.mp4"
    cmd = [
        "ffmpeg", "-y", "-ss", str(start), "-i", str(src),
        "-t", str(capture_duration), "-vf", vf,
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", str(VIDEO_CRF),
        "-movflags", "+faststart", str(out)
    ]
    run(cmd)
    print(f"Created highlight: {out.name} | {ffprobe_duration(out):.1f}s | {size_mb(out):.1f} MB")
    return out


def segment_file(src, label):
    duration = ffprobe_duration(src)
    total_mb = size_mb(src)
    if total_mb <= TARGET_CLIP_MB:
        dest = CLIPS_DIR / f"{label}_part_001.mp4"
        shutil.copy2(src, dest)
        return [dest]

    # Calculate an initial segment duration based on bitrate, then reduce until all parts are under target.
    segment_time = max(8.0, duration * (TARGET_CLIP_MB / total_mb) * 0.88)
    for attempt in range(8):
        pattern = CLIPS_DIR / f"{label}_part_%03d.mp4"
        for old in CLIPS_DIR.glob(f"{label}_part_*.mp4"):
            old.unlink()
        cmd = [
            "ffmpeg", "-y", "-i", str(src), "-c", "copy", "-map", "0",
            "-f", "segment", "-segment_time", f"{segment_time:.2f}",
            "-reset_timestamps", "1", "-segment_format", "mp4",
            "-segment_format_options", "movflags=+faststart", str(pattern)
        ]
        run(cmd)
        parts = sorted(CLIPS_DIR.glob(f"{label}_part_*.mp4"))
        max_mb = max(size_mb(p) for p in parts) if parts else 0
        print(f"Segmentation attempt {attempt+1}: {len(parts)} parts, largest {max_mb:.1f} MB, segment_time {segment_time:.1f}s")
        if parts and max_mb <= TARGET_CLIP_MB:
            return parts
        segment_time *= 0.72

    raise SystemExit(f"Could not split {src.name} below {TARGET_CLIP_MB} MB. Increase VIDEO_CRF or reduce VIDEO_WIDTH/FPS.")

manifest = {
    "version": "1.0",
    "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "clipTargetMB": TARGET_CLIP_MB,
    "videoWidth": VIDEO_WIDTH,
    "videoFPS": VIDEO_FPS,
    "videoCRF": VIDEO_CRF,
    "clips": []
}

cumulative = 0.0
for order, (plan, src) in enumerate(assignments, start=1):
    highlight = build_highlight_clip(src, plan)
    parts = segment_file(highlight, plan["label"])
    for part_index, part in enumerate(parts, start=1):
        part_duration = ffprobe_duration(part)
        manifest["clips"].append({
            "sequence": len(manifest["clips"]) + 1,
            "src": f"assets/clips/{part.name}",
            "chapter": plan["chapter"],
            "sourceOriginal": src.name,
            "sourceStartSeconds": plan.get("start_seconds", 0),
            "parentLabel": plan["label"],
            "part": part_index,
            "duration": round(part_duration, 3),
            "globalStart": round(cumulative, 3),
            "globalEnd": round(cumulative + part_duration, 3),
            "narrationSegmentIds": plan["narrationSegmentIds"],
            "sizeMB": round(size_mb(part), 2)
        })
        cumulative += part_duration

(ASSET_DIR / "assets" / "video-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
DATA_DIR.mkdir(exist_ok=True, parents=True)
(DATA_DIR / "narration.json").write_text(json.dumps(NARRATION_DATA, indent=2), encoding="utf-8")

print("\nGenerated clip manifest:")
for c in manifest["clips"]:
    print(f"{c['sequence']:02d}. {c['src']} | {c['duration']:.1f}s | {c['sizeMB']:.1f} MB | {c['chapter']}")
print(f"Total story video duration: {cumulative:.1f}s")

# =========================
# 6) CREATE TIME-LOCKED NARRATION MP3 IN COLAB
# =========================
def make_narration_mp3():
    import asyncio
    import edge_tts

    async def synthesize_edge(text, out):
        communicate = edge_tts.Communicate(text, voice="en-GB-RyanNeural", rate="+0%")
        await communicate.save(str(out))

    parts_dir = GEN_DIR / "narration_parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    fitted = []
    for idx, seg in enumerate(NARRATION_DATA["segments"], start=1):
        target = float(seg["end"] - seg["start"])
        raw = parts_dir / f"{idx:02d}_{seg['id']}_raw.mp3"
        wav = parts_dir / f"{idx:02d}_{seg['id']}_fitted.wav"
        asyncio.run(synthesize_edge(seg["text"], raw))
        actual = ffprobe_duration(raw)
        if actual > target:
            filter_audio = f"{fit_atempo_chain(actual / target)},atrim=0:{target:.3f},asetpts=N/SR/TB"
        else:
            filter_audio = f"apad=pad_dur={target-actual:.3f},atrim=0:{target:.3f},asetpts=N/SR/TB"
        run(["ffmpeg", "-y", "-i", str(raw), "-af", filter_audio, "-ar", "44100", "-ac", "2", str(wav)])
        fitted.append(wav)
    concat = parts_dir / "concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in fitted), encoding="utf-8")
    out = GEN_DIR / "narration.mp3"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-codec:a", "libmp3lame", "-q:a", "3", str(out)])
    print(f"Narration created: {out} | {ffprobe_duration(out):.1f}s")
    return out

narration_mp3 = make_narration_mp3()

# =========================
# 7) OPTIONAL PREVIEW MP4
# =========================
def make_preview_mp4():
    concat = GEN_DIR / "video_concat.txt"
    concat.write_text("".join(f"file '{(ASSET_DIR / c['src']).as_posix()}'\n" for c in manifest["clips"]), encoding="utf-8")
    silent = GEN_DIR / "movin_martech_silent_stitch.mp4"
    final = ROOT / "movin_martech_weaved_preview.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-vf", "scale=1280:-2,fps=24,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "28", "-an", "-movflags", "+faststart", str(silent)])
    video_duration = ffprobe_duration(silent)
    narration_duration = ffprobe_duration(narration_mp3)
    delta = narration_duration - video_duration
    filters = []
    if delta > 0.05:
        filters.append(f"tpad=stop_mode=clone:stop_duration={delta:.3f}")
    filters.append(f"trim=duration={narration_duration:.3f}")
    filters.append("setpts=PTS-STARTPTS")
    run(["ffmpeg", "-y", "-i", str(silent), "-i", str(narration_mp3), "-filter:v", ",".join(filters), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "medium", "-crf", "28", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(final)])
    print(f"Preview MP4 created: {final} | {size_mb(final):.1f} MB")
    return final

if BUILD_PREVIEW_MP4:
    make_preview_mp4()

# =========================
# 8) ZIP GITHUB ASSETS FOR UPLOAD
# =========================
assets_zip = ROOT / "movin_github_assets_under_20mb.zip"
with zipfile.ZipFile(assets_zip, "w", zipfile.ZIP_DEFLATED) as z:
    for p in (ASSET_DIR / "assets" / "clips").glob("*.mp4"):
        z.write(p, p.relative_to(ASSET_DIR))
    z.write(ASSET_DIR / "assets" / "video-manifest.json", Path("assets/video-manifest.json"))
    z.write(DATA_DIR / "narration.json", Path("data/narration.json"))

print("\nDONE")
print(f"Download this and unzip it into your GitHub repo root: {assets_zip}")
print("Every individual clip is below the target size. GitHub Actions will create assets/generated/narration.mp3 and assets/generated/movin_martech_weaved.mp4 during deployment.")

try:
    from google.colab import files
    files.download(str(assets_zip))
except Exception:
    pass
