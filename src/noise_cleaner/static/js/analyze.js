/* analyze.js — BPM / key / loudness / spectral analysis */
(function () {
  "use strict";

  const VIEWS = ["drop", "processing", "result"];
  let currentFile = null;

  document.addEventListener("DOMContentLoaded", () => {
    setupDropzone("dz", "fileInput", "browseBtn", (f) => {
      currentFile = f;
      startAnalysis();
    });

    $("resetBtn").addEventListener("click", () => {
      currentFile = null;
      showView("drop", VIEWS);
    });
  });

  async function startAnalysis() {
    showView("processing", VIEWS);
    const t0 = Date.now();
    const tick = setInterval(() => {
      const el = $("procTimer");
      if (el) el.textContent = fmtTime((Date.now() - t0) / 1000);
    }, 500);

    try {
      const fd = new FormData();
      fd.append("file", currentFile);

      const res  = await fetch("/api/analyze", { method: "POST", body: fd });
      const data = await res.json();
      clearInterval(tick);
      if (!res.ok) { toast(data.detail || "Analysis failed", "error"); showView("drop", VIEWS); return; }
      populateResult(data);
    } catch (e) {
      clearInterval(tick);
      toast("Network error: " + e.message, "error");
      showView("drop", VIEWS);
    }
  }

  function populateResult(d) {
    $("resFilename").textContent   = d.filename;
    $("resDuration").textContent   = fmtTime(d.duration);
    $("resSamplerate").textContent = `${d.samplerate} Hz`;
    $("resChannels").textContent   = d.channels === 1 ? "Mono" : `${d.channels}ch`;

    $("resBpm").textContent  = d.bpm ? `${d.bpm} BPM` : "—";
    $("resKey").textContent  = d.key  || "—";

    $("resLufs").textContent        = d.lufs_approx != null    ? `${d.lufs_approx} LUFS` : "—";
    $("resPeak").textContent        = d.peak_db != null         ? `${d.peak_db} dBFS`     : "—";
    $("resDynRange").textContent    = d.dynamic_range_db != null ? `${d.dynamic_range_db} dB` : "—";
    $("resCentroid").textContent    = d.spectral_centroid_hz    ? `${d.spectral_centroid_hz} Hz` : "—";

    $("resProcTime").textContent    = `${d.processing_time}s`;
    $("resLibrosa").textContent     = d.librosa_used ? "librosa ✓" : "fallback (numpy)";

    // Colour-code key mode
    const keyEl = $("resKey");
    if (keyEl) {
      keyEl.style.color = d.key_mode === "major"
        ? "var(--accent)"
        : "var(--warn, #e8a045)";
    }

    showView("result", VIEWS);
  }

  window.setMode = (m) => {};
})();
