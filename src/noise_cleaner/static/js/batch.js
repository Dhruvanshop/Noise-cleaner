/* batch.js — multi-file batch processing queue */
(function () {
  "use strict";

  const VIEWS = ["drop", "processing", "result"];
  let queuedFiles = [];
  let jobId = null;
  let pollInterval = null;

  document.addEventListener("DOMContentLoaded", () => {
    /* ── file add via browse ────────────────────────────────────────────── */
    $("browseBtn").addEventListener("click", () => $("fileInput").click());
    $("fileInput").addEventListener("change", (e) => {
      addFiles(Array.from(e.target.files));
      e.target.value = "";
    });

    /* ── drag-and-drop on dz ─────────────────────────────────────────────── */
    const dz = $("dz");
    dz.addEventListener("dragover",  (e) => { e.preventDefault(); dz.classList.add("drag-over"); });
    dz.addEventListener("dragleave", ()  => dz.classList.remove("drag-over"));
    dz.addEventListener("drop",      (e) => {
      e.preventDefault();
      dz.classList.remove("drag-over");
      addFiles(Array.from(e.dataTransfer.files).filter(f => isAudioFile(f)));
    });

    $("clearQueueBtn").addEventListener("click", () => {
      queuedFiles = [];
      renderQueue();
    });

    $("processBtn").addEventListener("click", startBatch);

    $("resetBtn").addEventListener("click", () => {
      queuedFiles = [];
      jobId       = null;
      clearInterval(pollInterval);
      renderQueue();
      showView("drop", VIEWS);
    });

    $("downloadBtn").addEventListener("click", () => {
      if (jobId) location.href = `/api/batch/download/${jobId}`;
    });

    /* tool selector → show/hide relevant param panels */
    $("toolSelect").addEventListener("change", updateParamPanel);
    updateParamPanel();
  });

  function addFiles(files) {
    files.filter(f => isAudioFile(f) || isVideoFile(f)).forEach(f => {
      if (!queuedFiles.find(q => q.name === f.name && q.size === f.size))
        queuedFiles.push(f);
    });
    renderQueue();
  }

  function renderQueue() {
    const list = $("queueList");
    const ct   = $("queueCount");
    if (!list) return;
    list.innerHTML = "";
    ct.textContent = queuedFiles.length ? `${queuedFiles.length} file${queuedFiles.length > 1 ? "s" : ""}` : "No files";

    queuedFiles.forEach((f, i) => {
      const li = document.createElement("li");
      li.className = "queue-item";
      li.innerHTML = `<span class="qi-name">${escHtml(f.name)}</span>
        <span class="qi-size">${fmtBytes(f.size)}</span>
        <button class="qi-remove" onclick="window._batchRemove(${i})" title="Remove">&#x2715;</button>`;
      list.appendChild(li);
    });

    $("processBtn").disabled = queuedFiles.length === 0;
  }

  window._batchRemove = (i) => {
    queuedFiles.splice(i, 1);
    renderQueue();
  };

  function updateParamPanel() {
    const tool = $("toolSelect").value;
    document.querySelectorAll(".tool-params").forEach(p => {
      p.style.display = p.dataset.tool === tool ? "" : "none";
    });
  }

  /* ── build JSON params from visible tool panel ───────────────────────────── */
  function buildParams() {
    const tool   = $("toolSelect").value;
    const params = { output_format: $("fmtSelect").value };

    if (tool === "normalize") {
      params.target_lufs       = parseFloat($("batchLufsSlider").value);
      params.true_peak_ceiling = parseFloat($("batchPeakSlider").value);
    } else if (tool === "trim") {
      params.threshold_db   = parseFloat($("batchThreshSlider").value);
      params.min_silence_ms = parseInt($("batchMinSilMs").value, 10);
      params.padding_ms     = parseInt($("batchPadMs").value, 10);
    } else if (tool === "convert") {
      params.bitrate     = $("batchBitrate").value;
      params.sample_rate = parseInt($("batchSampleRate").value, 10);
    } else if (tool === "repair") {
      params.remove_hum    = $("batchRemoveHum").checked;
      params.remove_clicks = $("batchRemoveClicks").checked;
    } else if (tool === "dereverberate") {
      params.strength  = parseFloat($("batchDerevStrength").value);
      params.decay_ms  = parseFloat($("batchDerevDecay").value);
    }
    return params;
  }

  /* ── start ─────────────────────────────────────────────────────────────── */
  async function startBatch() {
    if (!queuedFiles.length) return;
    showView("processing", VIEWS);

    const t0   = Date.now();
    const tick = setInterval(() => {
      const el = $("procTimer");
      if (el) el.textContent = fmtTime((Date.now() - t0) / 1000);
    }, 500);

    try {
      const fd = new FormData();
      queuedFiles.forEach(f => fd.append("files", f));
      fd.append("tool",   $("toolSelect").value);
      fd.append("params", JSON.stringify(buildParams()));

      const res  = await fetch("/api/batch", { method: "POST", body: fd });
      const data = await res.json();
      clearInterval(tick);

      if (!res.ok) { toast(data.detail || "Batch submit failed", "error"); showView("drop", VIEWS); return; }

      jobId = data.job_id;
      pollBatch();
    } catch (e) {
      clearInterval(tick);
      toast("Network error: " + e.message, "error");
      showView("drop", VIEWS);
    }
  }

  function pollBatch() {
    const t0 = Date.now();
    pollInterval = setInterval(async () => {
      try {
        const res  = await fetch(`/api/jobs/${jobId}`);
        const data = await res.json();

        const el = $("procTimer");
        if (el) el.textContent = fmtTime((Date.now() - t0) / 1000);

        if (data.status === "done") {
          clearInterval(pollInterval);
          populateResult(data.result);
        } else if (data.status === "error") {
          clearInterval(pollInterval);
          toast("Batch error: " + (data.error || "unknown"), "error");
          showView("drop", VIEWS);
        }
      } catch { /* keep polling */ }
    }, 2000);
  }

  function populateResult(r) {
    $("resFilesOk").textContent    = r.files_ok;
    $("resFilesError").textContent = r.files_error;

    const errList = $("resErrorList");
    errList.innerHTML = "";
    (r.errors || []).forEach(e => {
      const li = document.createElement("li");
      li.textContent = `${e.file}: ${e.error}`;
      errList.appendChild(li);
    });
    $("resErrors").style.display = r.files_error ? "" : "none";

    showView("result", VIEWS);
  }

  window.setMode = (m) => {};
})();
