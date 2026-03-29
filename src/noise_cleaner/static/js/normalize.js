/**
 * normalize.js — Loudness Normalizer page logic
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
                                  : 'Drag & drop · WAV, MP3, FLAC, OGG, M4A'
  $('dz-tags').innerHTML    = isV
    ? '<span class="fmt-tag">MP4</span><span class="fmt-tag">MOV</span><span class="fmt-tag">MKV</span><span class="fmt-tag">AVI</span><span class="fmt-tag">WebM</span>'
    : '<span class="fmt-tag">WAV</span><span class="fmt-tag">MP3</span><span class="fmt-tag">FLAC</span><span class="fmt-tag">OGG</span><span class="fmt-tag">M4A</span>'
  $('file-input').accept    = isV ? 'video/*,.mp4,.mov,.mkv,.avi,.webm' : 'audio/*,.wav,.flac,.ogg,.aif,.mp3,.m4a'
  const fmtRow = $('audio-fmt-row')
  if (fmtRow) fmtRow.style.display = isV ? 'none' : ''
}
window.setMode = setMode

// Sliders
$('s-lufs').addEventListener('input', () => {
  $('v-lufs').textContent = parseFloat($('s-lufs').value).toFixed(1) + ' LUFS'
})
$('s-peak').addEventListener('input', () => {
  $('v-peak').textContent = parseFloat($('s-peak').value).toFixed(1) + ' dBFS'
})

// Presets
bindPresetBtns('.preset-btn', b => {
  $('s-lufs').value = b.dataset.lufs
  $('v-lufs').textContent = b.dataset.lufs + ' LUFS'
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
  fd.append('target_lufs', $('s-lufs').value)
  fd.append('true_peak_ceiling', $('s-peak').value)
  fd.append('output_format', isVideoFile(file) ? 'wav' : _fmt)
  try {
    const res = await fetch('/api/normalize', { method: 'POST', body: fd })
    if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed') }
    const data = await res.json()
    $('r-lufs-in').textContent  = data.lufs_in + ' LUFS'
    $('r-lufs-out').textContent = data.lufs_out + ' LUFS'
    const g = data.gain_db
    $('r-gain').textContent  = (g >= 0 ? '+' : '') + g + ' dB'
    $('r-peak').textContent  = data.true_peak_db + ' dBFS'
    $('r-banner-lufs').textContent  = data.lufs_out + ' LUFS'
    $('r-banner-label').textContent = 'Normalized from ' + data.lufs_in + ' LUFS — gain ' + (g >= 0 ? '+' : '') + g + ' dB'
    const ext = isVideoFile(file) ? 'wav' : _fmt
    const dl = $('dl-btn')
    dl.href     = '/api/download/' + data.task_id
    dl.download = file.name.replace(/\.[^/.]+$/, '') + '_normalized.' + ext
    dl.textContent = '⬇ Download Normalized ' + (isVideoFile(file) ? 'Audio (WAV)' : ext.toUpperCase())
    showView('results'); toast('✅ Normalized!', 'success')
  } catch(err) { showView('upload'); toast('❌ ' + err.message, 'error', 5000) }
}

$('reset-btn').addEventListener('click', () => { $('file-input').value = ''; showView('upload') })
