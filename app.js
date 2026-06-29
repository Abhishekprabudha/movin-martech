const video = document.getElementById('demoVideo');
const narrationAudio = document.getElementById('narrationAudio');
const introAudio = document.getElementById('introAudio');
const transcriptEl = document.getElementById('transcript');
const pauseBtn = document.getElementById('pauseBtn');
const muteBtn = document.getElementById('muteBtn');
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
const NARRATION_MP3 = 'assets/generated/narration.mp3';
const INTRO_MP3 = 'assets/generated/intro.mp3';

let narration = null;
let manifest = null;
let useFinalVideo = false;
let currentClipIndex = 0;
let clipOffsets = [];
let activeSegmentId = null;
let selectedClipIndex = null;
let isIntroActive = true;

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
      <small>Play video + generated MP3 narration</small>
    `;
    option.addEventListener('click', () => playSection(idx));
    sectionOptions.appendChild(option);
  });
}

function activeNarration() {
  return isIntroActive ? introAudio : narrationAudio;
}

function pauseAll() {
  video.pause();
  introAudio.pause();
  narrationAudio.pause();
  updateControlLabels();
}

async function playMedia() {
  const audio = activeNarration();
  const tasks = [audio.play()];
  if (!isIntroActive) tasks.push(video.play());
  await Promise.all(tasks.map((task) => task.catch(() => {})));
  updateControlLabels();
}

function updateControlLabels() {
  const audio = activeNarration();
  const paused = isIntroActive ? audio.paused : (video.paused && audio.paused);
  pauseBtn.textContent = paused ? 'Play' : 'Pause';
  muteBtn.textContent = narrationAudio.muted && introAudio.muted ? 'Unmute' : 'Mute';
}

function syncNarrationToVideo() {
  if (isIntroActive) return;
  const t = globalTime();
  if (Math.abs((narrationAudio.currentTime || 0) - t) > 0.35) {
    narrationAudio.currentTime = t;
  }
}

function showIntro() {
  selectedClipIndex = null;
  isIntroActive = true;
  pauseAll();
  video.removeAttribute('src');
  video.load();
  video.classList.add('is-hidden');
  introStage.classList.remove('is-hidden');
  chapterLabel.textContent = 'Choose an option to learn more';
  timeLabel.textContent = 'Intro';
  progressEl.style.width = '0%';
  introCommentary.textContent = narration.intro.text;
  introAudio.currentTime = 0;
  playMedia();
}

function setActiveSegment(seg) {
  if (!seg || activeSegmentId === seg.id) return;
  activeSegmentId = seg.id;
  document.querySelectorAll('.transcript-item').forEach((node) => node.classList.remove('active'));
  document.getElementById(`transcript-${seg.id}`)?.classList.add('active');
  chapterLabel.textContent = seg.chapter;
  document.getElementById(`transcript-${seg.id}`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

function updateUI() {
  if (isIntroActive) {
    updateControlLabels();
    return;
  }
  const t = globalTime();
  const total = totalDuration();
  const seg = narration.segments.find((item) => t >= item.start && t < item.end) || narration.segments[narration.segments.length - 1];
  setActiveSegment(seg);
  timeLabel.textContent = `${fmt(t)} / ${fmt(total)}`;
  progressEl.style.width = `${Math.min(100, (t / total) * 100)}%`;
  updateControlLabels();
}

function loadClip(index, autoplay = false, atSeconds = 0) {
  const clip = manifest.clips[index];
  if (!clip) return;
  isIntroActive = false;
  currentClipIndex = index;
  introAudio.pause();
  introStage.classList.add('is-hidden');
  video.classList.remove('is-hidden');
  video.src = clip.src;
  video.currentTime = atSeconds;
  narrationAudio.currentTime = (clipOffsets[index] || 0) + atSeconds;
  chapterLabel.textContent = clip.chapter || 'Movin synchronized demo';
  if (autoplay) playMedia();
}

function playSection(index) {
  selectedClipIndex = index;
  isIntroActive = false;
  introAudio.pause();

  if (useFinalVideo) {
    introStage.classList.add('is-hidden');
    video.classList.remove('is-hidden');
    video.src = FINAL_VIDEO;
    video.currentTime = clipOffsets[index] || 0;
    narrationAudio.currentTime = clipOffsets[index] || 0;
    playMedia();
    updateUI();
    return;
  }

  loadClip(index, true, 0);
  updateUI();
}

function seekGlobal(target) {
  isIntroActive = false;
  introAudio.pause();
  narrationAudio.currentTime = target;
  if (useFinalVideo) {
    video.currentTime = target;
    playMedia();
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

function wireMedia() {
  video.addEventListener('timeupdate', () => {
    syncNarrationToVideo();
    updateUI();
  });
  video.addEventListener('loadedmetadata', updateUI);
  video.addEventListener('play', () => {
    syncNarrationToVideo();
    if (!isIntroActive) narrationAudio.play().catch(() => {});
    updateControlLabels();
  });
  video.addEventListener('pause', () => {
    if (!isIntroActive) narrationAudio.pause();
    updateControlLabels();
  });
  video.addEventListener('ended', () => {
    narrationAudio.pause();
    updateControlLabels();
  });
  introAudio.addEventListener('play', updateControlLabels);
  introAudio.addEventListener('pause', updateControlLabels);
  narrationAudio.addEventListener('play', updateControlLabels);
  narrationAudio.addEventListener('pause', updateControlLabels);

  pauseBtn.addEventListener('click', () => {
    const audio = activeNarration();
    const paused = isIntroActive ? audio.paused : (video.paused && audio.paused);
    if (paused) playMedia();
    else pauseAll();
  });

  muteBtn.addEventListener('click', () => {
    const muted = !(narrationAudio.muted && introAudio.muted);
    narrationAudio.muted = muted;
    introAudio.muted = muted;
    video.muted = true;
    updateControlLabels();
  });
}

async function init() {
  narration = await jsonOrNull(NARRATION_PATH);
  manifest = await jsonOrNull(MANIFEST_PATH) || await jsonOrNull(SAMPLE_MANIFEST_PATH);

  if (!narration) throw new Error('Missing data/narration.json');
  if (!manifest) throw new Error('Missing video manifest');

  introAudio.src = INTRO_MP3;
  narrationAudio.src = NARRATION_MP3;
  video.muted = true;

  renderTranscript();
  calculateOffsets();
  renderSectionOptions();

  useFinalVideo = await exists(FINAL_VIDEO);
  const narrationReady = await exists(NARRATION_MP3);
  const introReady = await exists(INTRO_MP3);
  if (useFinalVideo) {
    video.src = FINAL_VIDEO;
    chapterLabel.textContent = 'Movin synchronized master video';
  } else {
    const firstClipExists = manifest.clips?.[0]?.src ? await exists(manifest.clips[0].src) : false;
    chapterLabel.textContent = firstClipExists ? 'Choose an option to learn more' : 'Awaiting Colab-generated clips';
  }
  if (narrationReady && introReady) assetNotice.classList.add('ready');
  else assetNotice.textContent = 'Run scripts/build_narration.py to generate assets/generated/intro.mp3 and assets/generated/narration.mp3.';

  wireMedia();
  showIntro();
}

init().catch((err) => {
  console.error(err);
  chapterLabel.textContent = 'Setup required';
  assetNotice.textContent = `Setup required: ${err.message}`;
});
