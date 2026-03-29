/* repair.js — hum removal + click/pop repair */
(function () {
  "use strict";

  const VIEWS = ["drop", "processing", "result"];

  let currentFile = null;
  let resultTaskId = null;

  /* ── init ──────────────────────────────────────────────────────────────── */
  document.addEventListener("DOMContentLoaded", () => {
    setupDropzone("dz", "fileInput", "browseBtn", (f) => {
      currentFile = f;
      startProcessing();
    });

    $("resetBtn").addEventListener("click", () => {
      currentFile = null;
      resultTaskId = null;
      showView("drop", VIEWS);
    });

    $("downloadBtn").addEventListener("click", () => {
      if (resultTaskId) location.href = `/api/download/${resultTaskId}`;
    });

    // Hum freq toggle
    $("removeHumToggle").addEventListener("change", () => {
      $("humControls").style.display =
        $("removeHumToggle").checked ? "" : "none";
    });

    // Slider labels
    bindSliderLabel("humStrengthSlider", "humStrengthVal", (v) => `${(v * 100).toFixed(0)}%`);
    bindSliderLabel("clickThresholdSlider", "clickThresholdVal", (v) => `${v}σ`);
    bindSliderLabel("humHarmonicsSlider", "humHarmonicsVal", (v) => `${v}`);
  });

  function bindSliderLabel(sliderId, labelId, fmt) {
    const el = $(sliderId);
    if (!el) return;
    const label = $(labelId);
    el.addEventListener("input", () => { if (label) label.textContent = fmt(el.value); });
    if (label) label.textContent = fmt(el.value);
  }

  /* ── processing ─────────────────────────────────────────────────────────── */
  async function startProcessing() {
    showView("processing", VIEWS);
    const t0 = Date.now();
    const tick = setInterval(() => {
      const el = $("procTimer");
      if (el) el.textContent = fmtTime((Date.now() - t0) / 1000);
    }, 500);

    try {
      const fd = buildFormData();
      const res = await fetch("/api/repair", { method: "POST", body: fd });
      const data = await res.json();
      clearInterval(tick);
      if (!res.ok) { toast(data.detail || "Repair failed", "error"); showView("drop", VIEWS); return; }
      populateResult(data);
    } catch (e) {
      clearInterval(tick);
      toast("Network error: " + e.message, "error");
      showView("drop", VIEWS);
    }
  }

  function buildFormData() {
    const fd = new FormData();
    fd.append("file", currentFile);
    fd.append("remove_hum",      $("removeHumToggle").checked);
    fd.append("hum_freq",        $("humFreqSelect").value);
    fd.append("hum_harmonics",   $("humHarmonicsSlider").value);
    fd.append("hum_strength",    $("humStrengthSlider").value);
    fd.append("remove_clicks",   $("removeClicksToggle").checked);
    fd.append("click_threshold", $("clickThresholdSlider").value);
    fd.append("output_format",   $("fmtSelect").value);
    return fd;
  }

  function populateResult(d) {
    resultTaskId = d.task_id;
    $('resFilename').textContent   = d.filename;
    $('resDuration').textContent   = fmtTime(d.duration);
    $('resSamplerate').textContent = `${d.samplerate} Hz`;
    $('resHumFreq').textContent    = d.hum_freq_hz ? `${d.hum_freq_hz} Hz` : '—';
    $('resClicks').textContent     = d.clicks_repaired ?? '—';
    $('resRmsBefore').textContent  = d.rms_before_db != null ? `${d.rms_before_db} dB` : '—';
    $('resRmsAfter').textContent   = d.rms_after_db  != null ? `${d.rms_after_db} dB`  : '—';
    $('resProcTime').textContent   = `${d.processing_time}s`;
    // Audio preview players
    const orig = $('audioOriginal');
    const proc = $('audioProcessed');
    if (orig) { orig.src = `/api/audio/original/${d.task_id}`; orig.load(); }
    if (proc) { proc.src = `/api/audio/output/${d.task_id}`;   proc.load(); }
    showView('result', VIEWS);
  }

  window.setMode = (m) => {};  // no mode switch on this page
})();
