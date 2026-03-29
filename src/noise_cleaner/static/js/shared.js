/**
 * shared.js — Noise Cleaner shared utilities
 * Loaded before every page-specific script.
 * Exposes globals: $, toast, showView, setupDropzone,
 *   fmtBytes, fmtTime, escHtml, isAudioFile, isVideoFile
 */

// ── Element selector ────────────────────────────────────────────────────────
window.$ = id => document.getElementById(id)

// ── Theme ────────────────────────────────────────────────────────────────────
const THEME_KEY = 'nc_theme'
function applyTheme(t) {
  document.documentElement.dataset.theme = t
  const btn = $('theme-toggle')
  if (btn) btn.textContent = t === 'dark' ? '🌙' : '☀️'
  localStorage.setItem(THEME_KEY, t)
}
applyTheme(localStorage.getItem(THEME_KEY) || 'dark')
document.addEventListener('DOMContentLoaded', () => {
  const btn = $('theme-toggle')
  if (btn) btn.addEventListener('click', () =>
    applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'))
})

// ── Toast ────────────────────────────────────────────────────────────────────
let _toastTimer
window.toast = function(msg, type = 'info', ms = 3500) {
  const el = $('toast')
  if (!el) return
  el.textContent = msg
  el.className = `show ${type}`
  clearTimeout(_toastTimer)
  _toastTimer = setTimeout(() => { el.className = '' }, ms)
}

// ── View switcher ────────────────────────────────────────────────────────────
window.showView = function(name, views = ['upload', 'processing', 'results']) {
  views.forEach(k => {
    const el = $('view-' + k)
    if (el) el.classList.toggle('active', k === name)
  })
}

// ── File type helpers ────────────────────────────────────────────────────────
const AUDIO_RE = /\.(wav|flac|ogg|aif|aiff|mp3|m4a|aac)$/i
const VIDEO_RE = /\.(mp4|mov|mkv|avi|webm|m4v)$/i
window.isAudioFile = f => f.type.startsWith('audio/') || AUDIO_RE.test(f.name)
window.isVideoFile = f => f.type.startsWith('video/') || VIDEO_RE.test(f.name)

// ── Formatters ───────────────────────────────────────────────────────────────
window.fmtBytes = function(b) {
  if (b < 1024) return b + ' B'
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB'
  return (b / 1048576).toFixed(2) + ' MB'
}
window.fmtTime = function(s) {
  const m = Math.floor(s / 60)
  return `${m}:${Math.floor(s % 60).toString().padStart(2, '0')}`
}
window.escHtml = function(s) {
  return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))
}
window.fmtDuration = function(s) {
  if (s < 60) return s.toFixed(1) + 's'
  const m = Math.floor(s / 60), sec = Math.round(s % 60)
  return `${m}m ${sec}s`
}

// ── Drag & drop setup ────────────────────────────────────────────────────────
window.setupDropzone = function(dzId, fileInputId, browseBtnId, onFile) {
  const dz = $(dzId), fi = $(fileInputId), btn = $(browseBtnId)
  if (!dz || !fi) return
  dz.addEventListener('dragenter', e => { e.preventDefault(); dz.classList.add('over') })
  dz.addEventListener('dragover',  e => { e.preventDefault(); dz.classList.add('over') })
  dz.addEventListener('dragleave', () => dz.classList.remove('over'))
  dz.addEventListener('drop', e => {
    e.preventDefault(); dz.classList.remove('over')
    if (e.dataTransfer.files[0]) onFile(e.dataTransfer.files[0])
  })
  dz.addEventListener('click', e => {
    if (btn && btn.contains(e.target)) return
    fi.click()
  })
  if (btn) btn.addEventListener('click', e => { e.stopPropagation(); fi.click() })
  fi.addEventListener('change', () => { if (fi.files[0]) onFile(fi.files[0]) })
}

// ── Mode pill toggle helper ──────────────────────────────────────────────────
window.setModePills = function(mode) {
  const audio = $('pill-audio'), video = $('pill-video')
  if (audio) audio.className = 'mode-pill' + (mode === 'audio' ? ' active audio' : '')
  if (video) video.className = 'mode-pill' + (mode === 'video' ? ' active video' : '')
}

// ── Format option buttons ────────────────────────────────────────────────────
window.bindFmtOpts = function(selector, onChange) {
  document.querySelectorAll(selector).forEach(b => {
    b.addEventListener('click', () => {
      document.querySelectorAll(selector).forEach(x => x.classList.remove('active'))
      b.classList.add('active')
      if (onChange) onChange(b.dataset.fmt || b.dataset.value || b.textContent)
    })
  })
}

// ── Preset button group helper ───────────────────────────────────────────────
window.bindPresetBtns = function(selector, onChange) {
  document.querySelectorAll(selector).forEach(b => {
    b.addEventListener('click', () => {
      document.querySelectorAll(selector).forEach(x => x.classList.remove('active'))
      b.classList.add('active')
      if (onChange) onChange(b)
    })
  })
}
