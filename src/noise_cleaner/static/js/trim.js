/**
 * trim.js — Silence Remover page logic
 */
let _mode = 'audio', _fmt = 'wav'

function setMode(m) {
  _mode = m
  setModePills(m)
  const dz = $('dropzone'), isV = m === 'video'
  dz.classList.toggle('video-dz', isV)
  $('dz-icon').textContent  = isV ? '🎬' : '📂'
  $('dz-title').textContent = isV ? 'Drop your video file here' : 'Drop your audio file here'
  $('dz-sub').textContent   = isV ? 'Drag & drop · MP4, MOV, MKV, AVI, WebM'
                                  : 'Podcast recordings, interviews, voice memos'
  $('dz-tags').innerHTML    = isV
    ? '<span class="fmt-tag">MP4</span><span class="fmt-tag">MOV</span><span class="fmt-tag">MKV</span><span class="fmt-tag">AVI</span><span class="fmt-tag">WebM</span>'
    : '<span class="fmt-tag">WAV</span><span class="fmt-tag">MP3</span><span class="fmt-tag">FLAC</span><span class="fmt-tag">OGG</span>'
  $('file-input').accept    = isV ? 'video/*,.mp4,.mov,.mkv,.avi,.webm' : 'audio/*,.wav,.mp3,.flac,.ogg,.aif,.m4a'
  const fmtRow = $('audio-fmt-row')
  if (fmtRow) fmtRow.style.display = isV ? 'none' : ''
}
window.setMode = setMode

// Sliders
$('s-min').addEventListener('input', () => { $('v-min').textContent = $('s-min').value + ' ms' })
$('s-db').addEventListener('input',  () => { $('v-db').textContent  = $('s-db').value + ' dB' })
$('s-pad').addEventListener('input', () => { $('v-pad').textContent = $('s-pad').value + ' ms' })

// Presets
bindPresetBtns('.preset-btn', b => {
  $('s-min').value = b.dataset.min; $('v-min').textContent = b.dataset.min + ' ms'
  $('s-db').value  = b.dataset.db;  $('v-db').textContent  = b.dataset.db + ' dB'
})

// Format options
bindFmtOpts('.fmt-opt', v => { _fmt = v })

// Drop zone
setupDropzone('dropzone', 'file-input', 'browse-btn', handleFile)

async function handleFile(file) {
  if (isVideoFile(file) && _mode === 'audio') setMode('video')
  else if (isAudioFile(file) && _mode === 'video') setMode('audio')
  if (!isAudioFile(file) && !isVideoFile(file)) {
    toast('⚠ Please upload an audio or video file', 'warning'); return
  }
  showView('processing')
  const fd = new FormData()
  fd.append('file', file)
  fd.append('min_silence_ms', $('s-min').value)
  fd.append('threshold_db',   $('s-db').value)
  fd.append('keep_padding_ms',$('s-pad').value)
  fd.append('output_format',  isVideoFile(file) ? 'wav' : _fmt)
  try {
    const res = await fetch('/api/trim', { method: 'POST', body: fd })
    if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed') }
    const data = await res.json()
    $('r-dur-in').textContent   = data.duration_in + 's'
    $('r-dur-out').textContent  = data.duration_out + 's'
    $('r-removed').textContent  = data.removed_seconds + 's'
    $('r-runs').textContent     = data.silence_runs
    $('r-banner-pct').textContent   = data.pct_removed + '%'
    $('r-banner-label').textContent = 'removed · ' + data.silence_runs + ' silence run' + (data.silence_runs !== 1 ? 's' : '') + ' cut'
    const ext = isVideoFile(file) ? 'wav' : _fmt
    const dl = $('dl-btn')
    dl.href     = '/api/download/' + data.task_id
    dl.download = file.name.replace(/\.[^/.]+$/, '') + '_trimmed.' + ext
    dl.textContent = '⬇ Download Trimmed ' + (isVideoFile(file) ? 'Audio (WAV)' : ext.toUpperCase())
    showView('results'); toast('✅ Silence removed!', 'success')
  } catch(err) { showView('upload'); toast('❌ ' + err.message, 'error', 5000) }
}

$('reset-btn').addEventListener('click', () => { $('file-input').value = ''; showView('upload') })
