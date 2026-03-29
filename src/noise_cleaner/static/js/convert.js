/**
 * convert.js — Audio Converter page logic
 */
let _mode = 'audio', _fmt = 'wav'

function setMode(m) {
  _mode = m
  setModePills(m)
  const dz = $('dropzone'), isV = m === 'video'
  dz.classList.toggle('video-dz', isV)
  $('dz-icon').textContent  = isV ? '🎬' : '📂'
  $('dz-title').textContent = isV ? 'Drop your video file here' : 'Drop your audio file here'
  $('dz-sub').textContent   = isV ? 'Extract audio from MP4, MOV, MKV, AVI, WebM' : 'Supports WAV, MP3, FLAC, OGG, M4A, AIFF'
  $('dz-tags').innerHTML    = isV
    ? '<span class="fmt-tag">MP4</span><span class="fmt-tag">MOV</span><span class="fmt-tag">MKV</span><span class="fmt-tag">AVI</span><span class="fmt-tag">WebM</span>'
    : '<span class="fmt-tag">WAV</span><span class="fmt-tag">MP3</span><span class="fmt-tag">FLAC</span><span class="fmt-tag">OGG</span><span class="fmt-tag">M4A</span>'
  $('file-input').accept    = isV ? 'video/*,.mp4,.mov,.mkv,.avi,.webm' : 'audio/*,.wav,.flac,.ogg,.aif,.mp3,.m4a'
  $('fmt-grid-title').innerHTML = isV ? '🎵 Extract Audio As' : '🎯 Output Format'
  $('proc-title').textContent   = isV ? 'Extracting audio…' : 'Converting audio…'
  $('proc-sub').textContent     = isV ? 'Demuxing video · encoding audio track…' : 'Reading · resampling · encoding…'
}
window.setMode = setMode

document.querySelectorAll('.fmt-card').forEach(c => {
  c.addEventListener('click', () => {
    document.querySelectorAll('.fmt-card').forEach(x => x.classList.remove('active'))
    c.classList.add('active'); _fmt = c.dataset.fmt
    $('mp3-settings').style.display = _fmt === 'mp3' ? 'block' : 'none'
  })
})
$('s-bitrate').addEventListener('input', () => { $('v-bitrate').textContent = $('s-bitrate').value + ' kbps' })
$('s-sr').addEventListener('change', () => { $('v-sr').textContent = $('s-sr').options[$('s-sr').selectedIndex].text })

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
  fd.append('output_format', _fmt)
  fd.append('bitrate',     $('s-bitrate').value)
  fd.append('sample_rate', $('s-sr').value)
  try {
    const res = await fetch('/api/convert', { method: 'POST', body: fd })
    if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail || 'Failed') }
    const data = await res.json()
    $('r-duration').textContent = data.duration + 's'
    $('r-sr-out').textContent   = (data.samplerate / 1000).toFixed(1) + ' kHz'
    $('r-size-in').textContent  = fmtBytes(data.input_size)
    $('r-size-out').textContent = fmtBytes(data.output_size)
    const dl = $('dl-btn')
    dl.href     = '/api/download/' + data.task_id
    dl.download = file.name.replace(/\.[^/.]+$/, '') + '.' + _fmt
    dl.textContent = '⬇ Download ' + _fmt.toUpperCase() + ' File'
    showView('results'); toast('✅ Converted!', 'success')
  } catch(err) { showView('upload'); toast('❌ ' + err.message, 'error', 5000) }
}

$('reset-btn').addEventListener('click', () => { $('file-input').value = ''; showView('upload') })
