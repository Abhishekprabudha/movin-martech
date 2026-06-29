const video = document.getElementById('demoVideo');
const transcriptEl = document.getElementById('transcript');
const timelineEl = document.getElementById('timeline');
const playBtn = document.getElementById('playBtn');
const restartBtn = document.getElementById('restartBtn');
const chapterLabel = document.getElementById('chapterLabel');
const timeLabel = document.getElementById('timeLabel');
const progressEl = document.getElementById('storyProgress');
const assetNotice = document.getElementById('assetNotice');

const FINAL_VIDEO = 'assets/generated/movin_martech_weaved.mp4';
const MANIFEST_PATH = 'assets/video-manifest.json';
const SAMPLE_MANIFEST_PATH = 'assets/video-manifest.sample.json';
const NARRATION_PATH = 'data/narration.json';

let narration = null;
let manifest = null;
let useFinalVideo = false;
let currentClipIndex = 0;
let clipOffsets = [];
let activeSegmentId = null;

function fmt(sec) {
  sec = Math.max(0, Math.floor(sec || 0));
  const m = String(Math.floor(sec / 60)).padStart(2, '0');
  const s = String(sec % 60).padStart(2, '0');
  return `${m}:${s}`;
}

async function jsonOrNull(path) {
  try {
    const res = await fetch(path, { cache: 'no-store' });
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    return null;
  }
}

async function exists(path) {
  try {
    const res = await fetch(path, { method: 'HEAD', cache: 'no-store' });
    return res.ok;
  } catch (err) {
    return false;
  }
}

function calculateOffsets() {
  clipOffsets = [];
  let cursor = 0;
  (manifest?.clips || []).forEach((clip) => {
    clipOffsets.push(cursor);
    cursor += Number(clip.duration || 0);
  });
}

function totalDuration() {
  return narration?.durationSeconds || (manifest?.clips || []).reduce((sum, clip) => sum + Number(clip.duration || 0), 0) || 300;
}

function globalTime() {
  if (useFinalVideo) return video.currentTime || 0;
  return (clipOffsets[currentClipIndex] || 0) + (video.currentTime || 0);
}

function renderTranscript() {
  transcriptEl.innerHTML = '';
  narration.segments.forEach((seg) => {
    const item = document.createElement('article');
    item.className = 'transcript-item';
    item.id = `transcript-${seg.id}`;
    item.innerHTML = `
      <span class="transcript-time">${fmt(seg.start)} → ${fmt(seg.end)} · ${seg.chapter}</span>
      <h3>${seg.headline}</h3>
      <p>${seg.text}</p>
    `;
    item.addEventListener('click', () => seekGlobal(seg.start));
    transcriptEl.appendChild(item);
  });
}

function renderTimeline() {
  timelineEl.innerHTML = '';
  narration.segments.forEach((seg, idx) => {
    const step = document.createElement('button');
    step.className = 'timeline-step';
    step.id = `timeline-${seg.id}`;
    step.type = 'button';
    step.innerHTML = `<span>${String(idx + 1).padStart(2, '0')} · ${fmt(seg.start)}</span><strong>${seg.chapter}</strong>`;
    step.addEventListener('click', () => seekGlobal(seg.start));
    timelineEl.appendChild(step);
  });
}

function setActiveSegment(seg) {
  if (!seg || activeSegmentId === seg.id) return;
  activeSegmentId = seg.id;
  document.querySelectorAll('.transcript-item, .timeline-step').forEach((node) => node.classList.remove('active'));
  document.getElementById(`transcript-${seg.id}`)?.classList.add('active');
  document.getElementById(`timeline-${seg.id}`)?.classList.add('active');
  chapterLabel.textContent = seg.chapter;
  document.getElementById(`transcript-${seg.id}`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

function updateUI() {
  const t = globalTime();
  const total = totalDuration();
  const seg = narration.segments.find((item) => t >= item.start && t < item.end) || narration.segments[narration.segments.length - 1];
  setActiveSegment(seg);
  timeLabel.textContent = `${fmt(t)} / ${fmt(total)}`;
  progressEl.style.width = `${Math.min(100, (t / total) * 100)}%`;
}

function loadClip(index, autoplay = false, atSeconds = 0) {
  const clip = manifest.clips[index];
  if (!clip) return;
  currentClipIndex = index;
  video.src = clip.src;
  video.currentTime = atSeconds;
  chapterLabel.textContent = clip.chapter || 'Movin synchronized demo';
  if (autoplay) video.play().catch(() => {});
}

function seekGlobal(target) {
  if (useFinalVideo) {
    video.currentTime = target;
    video.play().catch(() => {});
    updateUI();
    return;
  }

  let index = 0;
  for (let i = 0; i < clipOffsets.length; i++) {
    const start = clipOffsets[i];
    const end = start + Number(manifest.clips[i].duration || 0);
    if (target >= start && target <= end) {
      index = i;
      break;
    }
  }
  const localTarget = Math.max(0, target - (clipOffsets[index] || 0));
  loadClip(index, true, localTarget);
}

function wireVideo() {
  video.addEventListener('timeupdate', updateUI);
  video.addEventListener('loadedmetadata', updateUI);
  video.addEventListener('ended', () => {
    if (!useFinalVideo && currentClipIndex < (manifest.clips.length - 1)) {
      loadClip(currentClipIndex + 1, true, 0);
    }
  });

  playBtn.addEventListener('click', () => {
    if (!video.src) loadClip(0, false, 0);
    video.play().catch(() => {});
  });
  restartBtn.addEventListener('click', () => seekGlobal(0));
}

async function init() {
  narration = await jsonOrNull(NARRATION_PATH);
  manifest = await jsonOrNull(MANIFEST_PATH) || await jsonOrNull(SAMPLE_MANIFEST_PATH);

  if (!narration) throw new Error('Missing data/narration.json');
  if (!manifest) throw new Error('Missing video manifest');

  renderTranscript();
  renderTimeline();
  calculateOffsets();

  useFinalVideo = await exists(FINAL_VIDEO);
  if (useFinalVideo) {
    video.src = FINAL_VIDEO;
    assetNotice.classList.add('ready');
    chapterLabel.textContent = 'Movin synchronized master video';
  } else {
    const firstClipExists = manifest.clips?.[0]?.src ? await exists(manifest.clips[0].src) : false;
    if (firstClipExists) {
      assetNotice.classList.add('ready');
      loadClip(0, false, 0);
    } else {
      video.removeAttribute('src');
      chapterLabel.textContent = 'Awaiting Colab-generated clips';
    }
  }

  wireVideo();
  updateUI();
}

init().catch((err) => {
  console.error(err);
  chapterLabel.textContent = 'Setup required';
  assetNotice.textContent = `Setup required: ${err.message}`;
});
