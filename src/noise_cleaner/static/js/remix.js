/* remix.js — load stems from a job + mix with per-stem volume/mute */
(function () {
  "use strict";

  const VIEWS = ["load", "mixer", "processing", "result"];
  let stemsJobId   = null;
  let stemsList    = [];
  let resultTaskId = null;

  const VOL_DEFAULTS = {};   // stem → 1.0

  document.addEventListener("DOMContentLoaded", () => {
    $("loadBtn").addEventListener("click", loadStems);
    $("jobIdInput").addEventListener("keydown", (e) => {
      if (e.key === "Enter") loadStems();
    });

    $("mixBtn").addEventListener("click", startRemix);
    $("resetBtn").addEventListener("click", () => {
      stemsJobId = null; stemsList = [];
      $("jobIdInput").value = "";
      showView("load", VIEWS);
    });
    $("downloadBtn").addEventListener("click", () => {
      if (resultTaskId) location.href = `/api/download/${resultTaskId}`;
    });
  });

  /* ── load stems list ──────────────────────────────────────────────────── */
  async function loadStems() {
    const id = ($("jobIdInput").value || "").trim();
    if (!id) { toast("Enter a Stems job ID", "warn"); return; }

    try {
      const res  = await fetch(`/api/remix/stems_info/${id}`);
      const data = await res.json();
      if (!res.ok) { toast(data.detail || "Job not found", "error"); return; }
      stemsJobId = id;
      stemsList  = data.stems;
      buildMixerUI();
      showView("mixer", VIEWS);
    } catch (e) {
      toast("Error: " + e.message, "error");
    }
  }

  /* ── build per-stem sliders ─────────────────────────────────────────────── */
  const STEM_ICONS = { vocals:"🎤", drums:"🥁", bass:"🎸", other:"🎵", guitar:"🎸", piano:"🎹" };
  const STEM_COLORS = { vocals:"#6c8fff", drums:"#e85d75", bass:"#ffd166", other:"#81d4a0", guitar:"#f4a261", piano:"#bb86fc" };

  function buildMixerUI() {
    const grid = $("stemGrid");
    grid.innerHTML = "";

    stemsList.forEach(name => {
      VOL_DEFAULTS[name] = VOL_DEFAULTS[name] ?? 1.0;
      const color  = STEM_COLORS[name] || "#aaa";
      const icon   = STEM_ICONS[name]  || "🎵";
      const div    = document.createElement("div");
      div.className = "stem-mix-card";
      div.style.setProperty("--sc", color);
      div.innerHTML = `
        <div class="smc-header">
          <span class="smc-icon">${icon}</span>
          <span class="smc-name">${escHtml(name)}</span>
          <button class="smc-mute" id="mute_${name}" onclick="window._toggleMute('${name}')" title="Mute">M</button>
        </div>
        <input type="range" class="smc-vol" id="vol_${name}"
          min="0" max="2" step="0.01" value="1"
          oninput="window._updateVol('${name}', this.value)">
        <span class="smc-vol-label" id="vlbl_${name}">100%</span>`;
      grid.appendChild(div);
    });

    $("jobIdLabel").textContent = stemsJobId;
  }

  window._toggleMute = (name) => {
    const btn = $(`mute_${name}`);
    const row = btn.closest(".stem-mix-card");
    const isMuted = row.classList.toggle("muted");
    btn.classList.toggle("active", isMuted);
  };

  window._updateVol = (name, val) => {
    const label = $(`vlbl_${name}`);
    if (label) label.textContent = `${(val * 100).toFixed(0)}%`;
  };

  /* ── start remix ──────────────────────────────────────────────────────── */
  async function startRemix() {
    showView("processing", VIEWS);
    const t0   = Date.now();
    const tick = setInterval(() => {
      const el = $("procTimer");
      if (el) el.textContent = fmtTime((Date.now() - t0) / 1000);
    }, 500);

    // Gather volumes + muted from DOM
    const volumes = {}, mutedArr = [];
    stemsList.forEach(name => {
      const card   = $(`mute_${name}`)?.closest(".stem-mix-card");
      const isMuted = card?.classList.contains("muted");
      if (isMuted) { mutedArr.push(name); }
      else {
        const vol = parseFloat($(`vol_${name}`)?.value ?? 1);
        volumes[name] = vol;
      }
    });

    try {
      const fd = new FormData();
      fd.append("stems_job_id",  stemsJobId);
      fd.append("volumes",       JSON.stringify(volumes));
      fd.append("muted",         JSON.stringify(mutedArr));
      fd.append("output_format", $("fmtSelect").value);
      fd.append("normalize",     $("normalizeToggle").checked);

      const res  = await fetch("/api/remix", { method: "POST", body: fd });
      const data = await res.json();
      clearInterval(tick);
      if (!res.ok) { toast(data.detail || "Remix failed", "error"); showView("mixer", VIEWS); return; }
      resultTaskId = data.task_id;
      populateResult(data);
    } catch (e) {
      clearInterval(tick);
      toast("Error: " + e.message, "error");
      showView("mixer", VIEWS);
    }
  }

  function populateResult(d) {
    $("resStemsMixed").textContent = (d.stems_mixed || []).join(", ") || "—";
    $("resStemsMuted").textContent = (d.stems_muted || []).join(", ") || "none";
    $("resDuration").textContent   = fmtTime(d.duration);
    $("resProcTime").textContent   = `${d.processing_time}s`;    const player = $('audioPreview');
    if (player) { player.src = `/api/audio/output/${resultTaskId}`; player.load(); }    showView("result", VIEWS);
  }

  window.setMode = (m) => {};
})();
