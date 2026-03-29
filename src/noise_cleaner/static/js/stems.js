/**
 * stems.js — Stem Splitter page logic
 */
'use strict'

/* ── State ── */
let _mode = 'audio', _fmt = 'wav', _model = 'htdemucs'
const _audioMap = {}   // {stemName: {audio: HTMLAudioElement, url: string}}
let _rafId = null, _pollTimer = null, _procTimer = null, _procStart = 0

/* ── Stem metadata ── */
const STEM_META = {
  vocals: { icon: '🎤', label: 'Vocals', color: 'var(--green)' },
  drums:  { icon: '🥁', label: 'Drums',  color: 'var(--amber)' },
  bass:   { icon: '🎸', label: 'Bass',   color: 'var(--violet)' },
  other:  { icon: '🎹', label: 'Other',  color: 'var(--cyan)' },
  guitar: { icon: '🎸', label: 'Guitar', color: 'var(--pink)' },
  piano:  { icon: '🎹', label: 'Piano',  color: 'var(--blue)' },
}

/* ── AI check ── */
fetch('/api/capabilities').then(r => r.json()).then(d => {
  if (!d.demucs) $('ai-warn').style.display = 'flex'
}).catch(() => {})

/* ── Mode switch ── */
function setMode(m) {
  _mode = m
  setModePills(m)
  const dz = $('dropzone'), isV = m === 'video'
  dz.classList.toggle('video-dz', isV)
  $('dz-icon').textContent  = isV ? '🎬' : '🎵'
  $('dz-title').textContent = isV ? 'Drop your video file here' : 'Drop your audio file here'
  $('dz-sub').textContent   = isV ? 'Extract & separate stems from MP4, MOV, MKV, AVI'
                                  : 'Music, songs, podcasts · WAV, MP3, FLAC, OGG, M4A'
  $('dz-tags').innerHTML    = isV
    ? '<span class="fmt-tag">MP4</span><span class="fmt-tag">MOV</span><span class="fmt-tag">MKV</span><span class="fmt-tag">AVI</span>'
    : '<span class="fmt-tag">WAV</span><span class="fmt-tag">MP3</span><span class="fmt-tag">FLAC</span><span class="fmt-tag">OGG</span><span class="fmt-tag">M4A</span>'
  $('file-input').accept = isV ? 'video/*,.mp4,.mov,.mkv,.avi,.webm' : 'audio/*,.wav,.mp3,.flac,.ogg,.aif,.m4a'
}
window.setMode = setMode

/* ── Model switch ── */
function setModel(m) {
  _model = m
  document.querySelectorAll('.model-btn').forEach(b => b.classList.toggle('active', b.dataset.model === m))
  const extra = ['guitar', 'piano']
  const show6 = m === 'htdemucs_6s'
  extra.forEach(s => {
    const card = document.querySelector(`.stem-card[data-stem="${s}"]`)
    if (card) { card.classList.toggle('hidden', !show6); if (show6) card.classList.add('selected') }
  })
}
window.setModel = setModel

/* ── Stem selector ── */
document.querySelectorAll('.stem-card').forEach(c => c.addEventListener('click', () => c.classList.toggle('selected')))

/* ── Format pills ── */
bindFmtOpts('.fmt-opt', v => { _fmt = v })

/* ── Drop zone ── */
setupDropzone('dropzone', 'file-input', 'browse-btn', handleFile)

/* ── RAF animation loop ── */
function startRaf() {
  if (_rafId) cancelAnimationFrame(_rafId)
  function tick() {
    let any = false
    for (const [name, { audio }] of Object.entries(_audioMap)) {
      const dur = audio.duration || 0, cur = audio.currentTime || 0, pct = dur > 0 ? cur / dur * 100 : 0
      const fill = document.getElementById('fill-' + name), time = document.getElementById('t-' + name)
      if (fill) fill.style.width = pct + '%'
      if (time) time.textContent = fmtTime(cur) + ' / ' + fmtTime(dur)
      if (!audio.paused) any = true
    }
    // Update mix bar
    const audios = Object.values(_audioMap).map(x => x.audio)
    const ref = audios.find(a => !a.paused) || audios[0]
    if (ref) {
      const dur = ref.duration || 0, cur = ref.currentTime || 0, pct = dur > 0 ? cur / dur * 100 : 0
      const mf = $('mix-fill'), mt = $('mix-time-display')
      if (mf) mf.style.width = pct + '%'
      if (mt) mt.textContent = fmtTime(cur) + ' / ' + fmtTime(dur)
    }
    _rafId = any ? requestAnimationFrame(tick) : null
  }
  _rafId = requestAnimationFrame(tick)
}

/* ── Individual play ── */
function togglePlay(name) {
  const { audio } = _audioMap[name]
  const card = document.querySelector(`.stem-player-card[data-stem="${name}"]`)
  const btn = $('play-' + name)
  if (audio.paused) {
    audio.play(); btn.classList.add('playing'); btn.textContent = '⏸'
    if (card) card.classList.add('is-playing')
  } else {
    audio.pause(); btn.classList.remove('playing'); btn.textContent = '▶'
    if (card) card.classList.remove('is-playing')
  }
  startRaf(); syncMixBtn()
}

/* ── Play all / Stop ── */
function playAll() {
  const state = $('mix-playbtn').dataset.state
  if (state === 'playing') {
    for (const [name, { audio }] of Object.entries(_audioMap)) {
      audio.pause()
      const b = $('play-' + name); if (b) { b.classList.remove('playing'); b.textContent = '▶' }
      const c = document.querySelector(`.stem-player-card[data-stem="${name}"]`); if (c) c.classList.remove('is-playing')
    }
    $('mix-playbtn').textContent = '▶ Play All'; $('mix-playbtn').dataset.state = 'stopped'
  } else {
    for (const [name, { audio }] of Object.entries(_audioMap)) {
      audio.play().catch(() => {})
      const b = $('play-' + name); if (b) { b.classList.add('playing'); b.textContent = '⏸' }
      const c = document.querySelector(`.stem-player-card[data-stem="${name}"]`); if (c) c.classList.add('is-playing')
    }
    $('mix-playbtn').textContent = '⏸ Pause All'; $('mix-playbtn').dataset.state = 'playing'; startRaf()
  }
}

function stopAll() {
  for (const [name, { audio }] of Object.entries(_audioMap)) {
    audio.pause(); audio.currentTime = 0
    const b = $('play-' + name); if (b) { b.classList.remove('playing'); b.textContent = '▶' }
    const c = document.querySelector(`.stem-player-card[data-stem="${name}"]`); if (c) c.classList.remove('is-playing')
    const f = document.getElementById('fill-' + name); if (f) f.style.width = '0%'
    const t = document.getElementById('t-' + name); if (t) t.textContent = '0:00 / ' + fmtTime(audio.duration || 0)
  }
  const mf = $('mix-fill'); if (mf) mf.style.width = '0%'
  $('mix-playbtn').textContent = '▶ Play All'; $('mix-playbtn').dataset.state = 'stopped'
}

function syncMixBtn() {
  const any = Object.values(_audioMap).some(({ audio }) => !audio.paused)
  const b = $('mix-playbtn'); if (b) { b.textContent = any ? '⏸ Pause All' : '▶ Play All'; b.dataset.state = any ? 'playing' : 'stopped' }
}

/* ── Seek ── */
function seekTrack(name, e) { const { audio } = _audioMap[name]; const r = e.currentTarget.getBoundingClientRect(); audio.currentTime = (e.clientX - r.left) / r.width * (audio.duration || 0); startRaf() }
function seekMix(e) { const r = $('mix-track').getBoundingClientRect(); const pct = (e.clientX - r.left) / r.width; for (const { audio } of Object.values(_audioMap)) audio.currentTime = pct * (audio.duration || 0); startRaf() }

/* ── Build player card ── */
function buildPlayerCard(name, url, meta) {
  const audio = new Audio(url)
  audio.preload = 'auto'
  _audioMap[name] = { audio, url }
  audio.addEventListener('ended', () => {
    const b = $('play-' + name); if (b) { b.classList.remove('playing'); b.textContent = '▶' }
    const c = document.querySelector(`.stem-player-card[data-stem="${name}"]`); if (c) c.classList.remove('is-playing')
    syncMixBtn()
  })
  const card = document.createElement('div')
  card.className = 'stem-player-card'; card.dataset.stem = name
  card.innerHTML = `
    <div class="spc-header">
      <span class="spc-icon">${meta.icon}</span>
      <span class="spc-name" style="color:${meta.color}">${meta.label}</span>
      <span class="spc-time" id="t-${name}">0:00 / 0:00</span>
      <button class="spc-playbtn" id="play-${name}" title="Play/Pause ${meta.label}">&#9654;</button>
    </div>
    <div class="spc-progress-track" id="track-${name}"><div class="spc-progress-fill" id="fill-${name}"></div></div>
    <div class="spc-bottom">
      <span class="spc-vol-icon" id="volicon-${name}">🔊</span>
      <input type="range" class="spc-vol" id="vol-${name}" min="0" max="1" step="0.02" value="1"/>
      <a href="${url}" download="${name}.${_fmt}" class="btn btn-ghost btn-sm spc-dl">&#11015; Download</a>
    </div>`
  card.querySelector('#play-' + name).addEventListener('click', () => togglePlay(name))
  card.querySelector('#track-' + name).addEventListener('click', e => seekTrack(name, e))
  card.querySelector('#vol-' + name).addEventListener('input', e => {
    audio.volume = parseFloat(e.target.value)
    card.querySelector('#volicon-' + name).textContent = audio.volume === 0 ? '🔇' : audio.volume < 0.5 ? '🔉' : '🔊'
  })
  return card
}

/* ── Master volume ── */
$('mix-vol').addEventListener('input', e => {
  const v = parseFloat(e.target.value)
  for (const { audio } of Object.values(_audioMap)) audio.volume = v
  for (const name of Object.keys(_audioMap)) {
    const ve = $('vol-' + name); if (ve) ve.value = v
    const ie = $('volicon-' + name); if (ie) ie.textContent = v === 0 ? '🔇' : v < 0.5 ? '🔉' : '🔊'
  }
})

/* ── Mix bar events ── */
$('mix-playbtn').dataset.state = 'stopped'
$('mix-playbtn').addEventListener('click', playAll)
$('mix-stopbtn').addEventListener('click', stopAll)
$('mix-track').addEventListener('click', seekMix)

/* ── Processing timer ── */
function startProcTimer() {
  _procStart = Date.now(); clearInterval(_procTimer)
  _procTimer = setInterval(() => { $('proc-timer').textContent = fmtTime(Math.floor((Date.now() - _procStart) / 1000)) }, 1000)
}
function stopProcTimer() { clearInterval(_procTimer); _procTimer = null }

/* ── Job polling ── */
async function pollJob(jobId) {
  const stages = ['Queued — waiting for worker…', 'Loading AI model…', 'Processing audio…', 'Separating stems…', 'Writing output files…']
  let stageIdx = 0
  clearInterval(_pollTimer)
  return new Promise((resolve, reject) => {
    _pollTimer = setInterval(async () => {
      try {
        const res = await fetch(`/api/jobs/${jobId}`)
        if (!res.ok) { clearInterval(_pollTimer); reject(new Error('Poll failed: ' + res.status)); return }
        const job = await res.json()
        if (job.status === 'processing') $('proc-stage').textContent = stages[Math.min(stageIdx++, stages.length - 1)]
        if (job.status === 'done')  { clearInterval(_pollTimer); resolve(job.result) }
        else if (job.status === 'error') { clearInterval(_pollTimer); reject(new Error(job.error || 'Job failed')) }
      } catch (e) { clearInterval(_pollTimer); reject(e) }
    }, 2000)
  })
}

/* ── Main file handler ── */
async function handleFile(file) {
  const isVideo = isVideoFile(file)
  if (isVideo && _mode === 'audio') setMode('video')
  else if (!isVideo && _mode === 'video') setMode('audio')

  const selected = [...document.querySelectorAll('.stem-card.selected:not(.hidden)')].map(c => c.dataset.stem)
  if (!selected.length) { toast('⚠ Select at least one stem to extract', 'warning'); return }

  for (const { audio } of Object.values(_audioMap)) { audio.pause(); audio.src = '' }
  Object.keys(_audioMap).forEach(k => delete _audioMap[k])

  showView('processing')
  $('proc-stage').textContent = 'Uploading & queuing job…'
  startProcTimer()

  const fd = new FormData()
  fd.append('file', file); fd.append('stems', selected.join(','))
  fd.append('output_format', _fmt); fd.append('model_name', _model)

  let jobId
  try {
    const res = await fetch('/api/stems', { method: 'POST', body: fd })
    if (!res.ok) { const e = await res.json().catch(() => ({ detail: 'Upload failed' })); throw new Error(e.detail || 'Upload failed') }
    jobId = (await res.json()).job_id
    $('proc-stage').textContent = 'Job queued — processing…'
  } catch (err) { stopProcTimer(); showView('upload'); toast('❌ ' + err.message, 'error', 5000); return }

  try {
    const data = await pollJob(jobId)
    stopProcTimer()
    $('r-duration').textContent   = Math.round(data.duration) + 's'
    $('r-samplerate').textContent = ((data.samplerate || 44100) / 1000).toFixed(1) + ' kHz'
    $('r-stems-count').textContent = Object.keys(data.stems).length
    $('r-model').textContent = data.model === 'htdemucs_6s' ? '6-Stem' : '4-Stem'

    const grid = $('stem-player-grid'); grid.innerHTML = ''
    for (const [name, url] of Object.entries(data.stems)) {
      const meta = STEM_META[name] || { icon: '🎵', label: name, color: 'var(--text)' }
      grid.appendChild(buildPlayerCard(name, url, meta))
    }
    $('mix-fill').style.width = '0%'; $('mix-time-display').textContent = '0:00 / 0:00'
    $('mix-playbtn').textContent = '▶ Play All'; $('mix-playbtn').dataset.state = 'stopped'

    // Show job ID for use in Remixer
    const jobIdEl = $('stems-job-id')
    if (jobIdEl) jobIdEl.textContent = jobId
    window._copyJobId = () => {
      navigator.clipboard.writeText(jobId).then(
        () => toast('✅ Job ID copied to clipboard', 'success', 2500),
        () => { prompt('Copy this Job ID:', jobId) }
      )
    }

    showView('results'); toast('✅ Stems ready! Click ▶ to preview.', 'success')
  } catch (err) { stopProcTimer(); showView('upload'); toast('❌ ' + err.message, 'error', 5000) }
}

$('reset-btn').addEventListener('click', () => { stopAll(); $('file-input').value = ''; showView('upload') })
