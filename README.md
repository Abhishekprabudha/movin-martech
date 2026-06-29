# Movin Marketing Technology OS — GitHub-safe synchronized demo

This repo creates a high-impact Movin demo site where the narration, transcript and videos run in sync.

It is designed for the GitHub web upload limitation problem:

- You do **not** upload the original 80MB–150MB recordings to GitHub.
- You run the included Colab processor, upload the 4 original videos into Colab, and Colab produces small clips under 20MB each.
- You upload only those small clips and the generated manifest into this repo.
- GitHub Actions generates the narration MP3 and weaves the clips into one final synchronized MP4 for GitHub Pages.

## What the demo shows

1. AEO / GEO intelligence
2. Prompt and customer-intent intelligence
3. Opportunity engine
4. WarmLead AI lead generation
5. Autonomous campaign generation
6. Campaign syndication into content, media and CRM
7. B2B shipment data monetization
8. Movin growth operating system close

## Folder structure

```text
.
├── index.html
├── styles.css
├── app.js
├── data/
│   └── narration.json
├── assets/
│   ├── clips/                    # Upload Colab-generated clips here
│   ├── generated/                # GitHub Actions creates narration.mp3 and final MP4 here
│   └── video-manifest.sample.json
├── scripts/
│   ├── colab_movin_video_processor.py
│   ├── build_narration.py
│   ├── build_weaved_video.py
│   └── validate_assets.py
├── COLAB_VIDEO_PROCESSOR.ipynb
└── .github/workflows/build-and-deploy.yml
```

## Step 1 — Upload this repo to GitHub

Upload the contents of this zip to a new GitHub repository.

Do not upload the original 4 videos directly.

## Step 2 — Run the Colab processor

Open Google Colab, upload `COLAB_VIDEO_PROCESSOR.ipynb`, and run the notebook.

When prompted, upload the 4 original recordings:

- `Screen Recording 2026-06-04 at 12.11.10 PM 2.mov`
- `Screen Recording 2026-06-02 at 6.26.34 PM.mov`
- `Demo_ElevateOS 1.mp4`
- `de3mo-20260609_174126-Meeting Recording.mp4`

The notebook will create:

```text
movin_github_assets_under_20mb.zip
```

This asset zip contains:

```text
assets/clips/*.mp4
assets/video-manifest.json
data/narration.json
```

Every `assets/clips/*.mp4` file is kept below 20MB.

## Step 3 — Upload Colab-generated assets to GitHub

Unzip `movin_github_assets_under_20mb.zip`.

Upload the unzipped files into your GitHub repository root so that the paths are exactly:

```text
assets/clips/01_aeo_geo_intelligence_part_001.mp4
assets/clips/...
assets/video-manifest.json
data/narration.json
```

Important: the GitHub site and workflow read the names from `assets/video-manifest.json`. Do not rename the clips after Colab creates them.

## Step 4 — Enable GitHub Pages

Go to:

```text
Settings → Pages → Build and deployment → Source → GitHub Actions
```

Then run:

```text
Actions → Build Movin Synced Demo and Deploy Pages → Run workflow
```

The workflow will:

1. Validate that every clip exists and is below 20MB.
2. Create a time-locked narration MP3 from `data/narration.json`.
3. Stitch the uploaded clips into `assets/generated/movin_martech_weaved.mp4`.
4. Deploy the finished HTML demo to GitHub Pages.

## How the synchronization works

- The transcript timing lives in `data/narration.json`.
- The video sequence and exact clip names live in `assets/video-manifest.json`.
- The browser highlights narration text based on video time.
- If `assets/generated/movin_martech_weaved.mp4` exists, the site plays the final master video.
- If the final video has not been generated yet, the site can play the Colab clips as a sequential fallback.

## Customizing the clip selection

In `COLAB_VIDEO_PROCESSOR.ipynb`, edit `SEQUENCE_PLAN` if the best screen appears later in any video:

```python
"start_seconds": 0,
"target_duration": 140,
```

The default 5-minute sequence is:

| Sequence | Capability | Duration |
|---|---:|---:|
| 1 | AEO / GEO + opportunity engine | 140 sec |
| 2 | Lead generation | 40 sec |
| 3 | Autonomous campaigns + syndication | 75 sec |
| 4 | Data monetization | 45 sec |

Total: 300 seconds.

## If any clip is still above 20MB

In the Colab notebook, change:

```python
VIDEO_CRF = 33
VIDEO_WIDTH = 960
VIDEO_FPS = 15
```

Then re-run the notebook and re-upload the generated asset zip.
