const video = document.getElementById('demoVideo');
const transcriptEl = document.getElementById('transcript');
const timelineEl = document.getElementById('timeline');
const playBtn = document.getElementById('playBtn');
const restartBtn = document.getElementById('restartBtn');
const chapterLabel = document.getElementById('chapterLabel');
const timeLabel = document.getElementById('timeLabel');
const progressEl = document.getElementById('storyProgress');
const assetNotice = document.getElementById('assetNotice');
const introStage = document.getElementById('introStage');
const introCommentary = document.getElementById('introCommentary');
const sectionOptions = document.getElementById('sectionOptions');

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
let pendingNarrationTimeout = null;
let selectedClipIndex = null;
let playAllMode = false;

const INTRO_NARRATION = 'Welcome to the Movin Marketing Technology OS. This landing page is an interactive menu. Choose an option to learn more about AI discovery, lead generation, autonomous campaigns, syndication, or shipment data monetization. When you select a section, the matching video and narration will play together.';

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

function renderSectionOptions() {
  sectionOptions.innerHTML = '';
  (manifest.clips || []).forEach((clip, idx) => {
    const option = document.createElement('button');
    option.className = 'section-option';
    option.type = 'button';
    option.innerHTML = `
      <span>${String(idx + 1).padStart(2, '0')}</span>
      <strong>${clip.chapter}</strong>
      <small>Play video + narration</small>
    `;
    option.addEventListener('click', () => playSection(idx));
    sectionOptions.appendChild(option);
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

function speak(text) {
  if (!('speechSynthesis' in window) || !text) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.98;
  utterance.pitch = 1;
  utterance.volume = 1;
  window.speechSynthesis.speak(utterance);
}

function clearPendingNarration() {
  if (pendingNarrationTimeout) window.clearTimeout(pendingNarrationTimeout);
  pendingNarrationTimeout = null;
}

function startClipNarration(index, atSeconds = 0) {
  clearPendingNarration();
  const clipStart = clipOffsets[index] || 0;
  const text = narration.segments
    .filter((segment) => {
      const clipEnd = clipStart + Number(manifest.clips[index]?.duration || 0);
      return segment.end > clipStart && segment.start < clipEnd;
    })
    .map((segment) => segment.text)
    .join(' ');

  if (!text) return;
  pendingNarrationTimeout = window.setTimeout(() => speak(text), Math.max(0, atSeconds) * 1000);
}

function showIntro() {
  selectedClipIndex = null;
  playAllMode = false;
  clearPendingNarration();
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  video.pause();
  video.removeAttribute('src');
  video.load();
  video.classList.add('is-hidden');
  introStage.classList.remove('is-hidden');
  chapterLabel.textContent = 'Choose an option to learn more';
  timeLabel.textContent = 'Intro';
  progressEl.style.width = '0%';
  introCommentary.textContent = INTRO_NARRATION;
  speak(INTRO_NARRATION);
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

function loadClip(index, autoplay = false, atSeconds = 0, narrate = false) {
  const clip = manifest.clips[index];
  if (!clip) return;
  currentClipIndex = index;
  introStage.classList.add('is-hidden');
  video.classList.remove('is-hidden');
  video.src = clip.src;
  video.currentTime = atSeconds;
  chapterLabel.textContent = clip.chapter || 'Movin synchronized demo';
  if (narrate) startClipNarration(index, atSeconds);
  if (autoplay) video.play().catch(() => {});
}

function playSection(index) {
  selectedClipIndex = index;
  playAllMode = false;

  if (useFinalVideo) {
    introStage.classList.add('is-hidden');
    video.classList.remove('is-hidden');
    video.src = FINAL_VIDEO;
    video.currentTime = clipOffsets[index] || 0;
    startClipNarration(index, 0);
    video.play().catch(() => {});
    updateUI();
    return;
  }

  loadClip(index, true, 0, true);
  updateUI();
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
    clearPendingNarration();
    if (!useFinalVideo && playAllMode && currentClipIndex < (manifest.clips.length - 1)) {
      loadClip(currentClipIndex + 1, true, 0, true);
    }
  });

  playBtn.addEventListener('click', () => {
    selectedClipIndex = null;
    playAllMode = true;

    if (useFinalVideo) {
      introStage.classList.add('is-hidden');
      video.classList.remove('is-hidden');
      video.src = FINAL_VIDEO;
      video.currentTime = 0;
      startClipNarration(0, 0);
      video.play().catch(() => {});
      updateUI();
      return;
    }

    loadClip(0, true, 0, true);
  });
  restartBtn.addEventListener('click', showIntro);
}

async function init() {
  narration = await jsonOrNull(NARRATION_PATH);
  manifest = await jsonOrNull(MANIFEST_PATH) || await jsonOrNull(SAMPLE_MANIFEST_PATH);

  if (!narration) throw new Error('Missing data/narration.json');
  if (!manifest) throw new Error('Missing video manifest');

  renderTranscript();
  renderTimeline();
  calculateOffsets();
  renderSectionOptions();

  useFinalVideo = await exists(FINAL_VIDEO);
  if (useFinalVideo) {
    video.src = FINAL_VIDEO;
    assetNotice.classList.add('ready');
    chapterLabel.textContent = 'Movin synchronized master video';
  } else {
    const firstClipExists = manifest.clips?.[0]?.src ? await exists(manifest.clips[0].src) : false;
    if (firstClipExists) {
      assetNotice.classList.add('ready');
      chapterLabel.textContent = 'Choose an option to learn more';
    } else {
      video.removeAttribute('src');
      chapterLabel.textContent = 'Awaiting Colab-generated clips';
    }
  }

  wireVideo();
  showIntro();
}

init().catch((err) => {
  console.error(err);
  chapterLabel.textContent = 'Setup required';
  assetNotice.textContent = `Setup required: ${err.message}`;
});
