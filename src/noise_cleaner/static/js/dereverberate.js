/* dereverberate.js — room reverb removal */
(function () {
  "use strict";

  const VIEWS = ["drop", "processing", "result"];
  let currentFile = null;
  let resultTaskId = null;

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

    bindSliderLabel("strengthSlider",  "strengthVal",  (v) => `${(v * 100).toFixed(0)}%`);
    bindSliderLabel("decayMsSlider",   "decayMsVal",   (v) => `${v} ms`);
  });

  function bindSliderLabel(sliderId, labelId, fmt) {
    const el = $(sliderId);
    if (!el) return;
    const label = $(labelId);
    el.addEventListener("input", () => { if (label) label.textContent = fmt(el.value); });
    if (label) label.textContent = fmt(el.value);
  }

  async function startProcessing() {
    showView("processing", VIEWS);
    const t0 = Date.now();
    const tick = setInterval(() => {
      const el = $("procTimer");
      if (el) el.textContent = fmtTime((Date.now() - t0) / 1000);
    }, 500);

    try {
      const fd = new FormData();
      fd.append("file",          currentFile);
      fd.append("strength",      $("strengthSlider").value);
      fd.append("decay_ms",      $("decayMsSlider").value);
      fd.append("output_format", $("fmtSelect").value);

      const res  = await fetch("/api/dereverberate", { method: "POST", body: fd });
      const data = await res.json();
      clearInterval(tick);
      if (!res.ok) { toast(data.detail || "De-reverb failed", "error"); showView("drop", VIEWS); return; }
      populateResult(data);
    } catch (e) {
      clearInterval(tick);
      toast("Network error: " + e.message, "error");
      showView("drop", VIEWS);
    }
  }

  function populateResult(d) {
    resultTaskId = d.task_id;
    $("resFilename").textContent   = d.filename;
    $("resDuration").textContent   = fmtTime(d.duration);
    $("resSamplerate").textContent = `${d.samplerate} Hz`;
    $("resChannels").textContent   = d.channels === 1 ? "Mono" : "Stereo";
    $("resStrength").textContent   = `${(d.strength_used * 100).toFixed(0)}%`;
    $("resProcTime").textContent   = `${d.processing_time}s`;    // Audio preview
    const orig = $('audioOriginal');
    const proc = $('audioProcessed');
    if (orig) { orig.src = `/api/audio/original/${d.task_id}`; orig.load(); }
    if (proc) { proc.src = `/api/audio/output/${d.task_id}`;   proc.load(); }    showView("result", VIEWS);
  }

  window.setMode = (m) => {};
})();
