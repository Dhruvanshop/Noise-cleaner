/* pipeline.js — sequential processing chain (denoise → normalize → trim → …) */
(function () {
  "use strict";

  const VIEWS = ["drop", "processing", "result"];

  // Available pipeline steps
  const ALL_STEPS = [
    { id: "denoise",        label: "Denoise",       icon: "🎙" },
    { id: "repair",         label: "Repair",        icon: "🔧" },
    { id: "dereverberate",  label: "De-Reverb",     icon: "🏠" },
    { id: "normalize",      label: "Normalize",     icon: "📊" },
    { id: "trim",           label: "Trim Silence",  icon: "✂" },
    { id: "convert",        label: "Convert",       icon: "🔄" },
  ];

  // Active steps (ordered list of step IDs the user has enabled)
  let activeSteps  = ["denoise", "normalize"];
  let currentFile  = null;
  let resultTaskId = null;

  document.addEventListener("DOMContentLoaded", () => {
    buildStepPicker();
    renderPipeline();

    setupDropzone("dz", "fileInput", "browseBtn", (f) => {
      currentFile = f;
      runPipeline();
    });

    $("resetBtn").addEventListener("click", () => {
      currentFile = null; resultTaskId = null;
      showView("drop", VIEWS);
    });

    $("downloadBtn").addEventListener("click", () => {
      if (resultTaskId) location.href = `/api/download/${resultTaskId}`;
    });
  });

  /* ── step picker ────────────────────────────────────────────────────────── */
  function buildStepPicker() {
    const container = $("stepPicker");
    if (!container) return;
    ALL_STEPS.forEach(s => {
      const btn = document.createElement("button");
      btn.className = "step-toggle" + (activeSteps.includes(s.id) ? " active" : "");
      btn.dataset.step = s.id;
      btn.innerHTML = `${s.icon} ${s.label}`;
      btn.addEventListener("click", () => toggleStep(s.id, btn));
      container.appendChild(btn);
    });
  }

  function toggleStep(id, btn) {
    if (activeSteps.includes(id)) {
      if (activeSteps.length === 1) { toast("At least one step required", "warn"); return; }
      activeSteps = activeSteps.filter(s => s !== id);
      btn.classList.remove("active");
    } else {
      activeSteps.push(id);
      btn.classList.add("active");
    }
    renderPipeline();
  }

  /* ── pipeline preview ───────────────────────────────────────────────────── */
  function renderPipeline() {
    const track = $("pipelineTrack");
    if (!track) return;
    track.innerHTML = "";
    activeSteps.forEach((id, i) => {
      const s = ALL_STEPS.find(x => x.id === id);
      if (!s) return;
      if (i > 0) {
        const arrow = document.createElement("span");
        arrow.className = "pipe-arrow";
        arrow.textContent = "→";
        track.appendChild(arrow);
      }
      const node = document.createElement("span");
      node.className = "pipe-node";
      node.textContent = `${s.icon} ${s.label}`;
      track.appendChild(node);
    });
    // update run button label
    const btn = $("runBtn");
    if (btn) btn.textContent = `Run ${activeSteps.length}-Step Pipeline`;
  }

  /* ── run pipeline ───────────────────────────────────────────────────────── */
  async function runPipeline() {
    if (!currentFile) return;
    showView("processing", VIEWS);

    const t0   = Date.now();
    const tick = setInterval(() => {
      const el = $("procTimer");
      if (el) el.textContent = fmtTime((Date.now() - t0) / 1000);
    }, 500);

    // Update progress bar / step display
    const stepStatus = $("stepStatus");

    try {
      let taskId = null;
      let curFile = currentFile;

      for (let i = 0; i < activeSteps.length; i++) {
        const stepId = activeSteps[i];
        const s = ALL_STEPS.find(x => x.id === stepId);
        if (stepStatus) stepStatus.textContent = `${i + 1}/${activeSteps.length}: ${s.label}…`;

        const result = await runStep(stepId, curFile, taskId);
        taskId = result.task_id;

        // For next step: we can't re-fetch the file as a File object, so we
        // fetch the output blob and wrap it in a File
        if (i < activeSteps.length - 1) {
          const blob = await fetch(`/api/download/${taskId}`).then(r => r.blob());
          const ext  = result.output_format || "wav";
          curFile    = new File([blob], `step_${i}_output.${ext}`, { type: blob.type });
        } else {
          resultTaskId = taskId;
        }
      }

      clearInterval(tick);
      populateResult({ task_id: resultTaskId, steps: activeSteps });
    } catch (e) {
      clearInterval(tick);
      toast("Pipeline error: " + e.message, "error");
      showView("drop", VIEWS);
    }
  }

  async function runStep(stepId, file, _prevTaskId) {
    const fd = new FormData();
    fd.append("file", file);

    let endpoint = "";
    if (stepId === "denoise") {
      endpoint = "/api/denoise";
      fd.append("mode", "algorithm");
      fd.append("output_format", getFmt());
    } else if (stepId === "normalize") {
      endpoint = "/api/normalize";
      fd.append("output_format", getFmt());
    } else if (stepId === "trim") {
      endpoint = "/api/trim";
      fd.append("output_format", getFmt());
    } else if (stepId === "convert") {
      endpoint = "/api/convert";
      fd.append("output_format", $("pipelineFmtSelect")?.value || "wav");
    } else if (stepId === "repair") {
      endpoint = "/api/repair";
      fd.append("output_format", getFmt());
    } else if (stepId === "dereverberate") {
      endpoint = "/api/dereverberate";
      fd.append("output_format", getFmt());
    }

    const res  = await fetch(endpoint, { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `${stepId} step failed`);
    return data;
  }

  function getFmt() {
    return $("pipelineFmtSelect")?.value || "wav";
  }

  function populateResult(d) {
    $('resSteps').textContent  = (d.steps || activeSteps).map(id => {
      const s = ALL_STEPS.find(x => x.id === id);
      return s ? `${s.icon} ${s.label}` : id;
    }).join(' → ');
    $('resTaskId').textContent = d.task_id;
    const player = $('audioPreview');
    if (player) { player.src = `/api/audio/output/${d.task_id}`; player.load(); }
    showView("result", VIEWS);
  }

  window.setMode = (m) => {};

  // expose runPipeline for optional manual trigger
  window._runPipeline = runPipeline;
})();
