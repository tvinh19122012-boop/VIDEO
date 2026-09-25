/* ===== Web Chữ Chạy Cho Video — logic phía trình duyệt ===== */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const video = $("video");
  const otext = $("overlay-text");

  const POS_TOP = { top: "17%", middle: "50%", bottom: "83%" };
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const easeOut = (p) => 1 - Math.pow(1 - p, 3);
  const esc = (s) =>
    s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  const state = {
    file: null,
    preset: "pop",
    font: "Be Vietnam Pro",
    size: 6.5,
    duration: 3,
    color: "#FFFFFF",
    highlight: "#FFE933",
    position: "middle",
  };

  const show = (el) => el.classList.remove("hidden");
  const hide = (el) => el.classList.add("hidden");

  /* ------------------------------------------------------------------ */
  /* 1. Chọn / kéo-thả video                                            */
  /* ------------------------------------------------------------------ */
  const drop = $("drop");
  const fileInput = $("file");

  drop.addEventListener("click", () => fileInput.click());
  ["dragenter", "dragover"].forEach((ev) =>
    drop.addEventListener(ev, (e) => {
      e.preventDefault();
      drop.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((ev) =>
    drop.addEventListener(ev, () => drop.classList.remove("dragover"))
  );
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) setFile(f);
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
  });

  function setFile(f) {
    const okExt = /\.(mp4|mov|webm|mkv|avi|m4v|3gp|ts|flv|wmv|mpg|mpeg)$/i.test(f.name);
    if (!f.type.startsWith("video/") && !okExt) {
      alert("Đây không phải file video. Hãy chọn mp4/mov/webm…");
      return;
    }
    state.file = f;
    video.src = URL.createObjectURL(f);
    hide($("step-upload"));
    show($("step-edit"));
    $("stage-badge").style.display = "";
  }

  /* ------------------------------------------------------------------ */
  /* 2. Các điều khiển soạn chữ                                         */
  /* ------------------------------------------------------------------ */
  document.querySelectorAll(".preset").forEach((btn) =>
    btn.addEventListener("click", () => {
      document.querySelectorAll(".preset").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.preset = btn.dataset.preset;
      $("hl-wrap").style.display = state.preset === "words" ? "" : "none";
      staticDraw();
    })
  );

  const bind = (id, key, fn) => {
    const el = $(id);
    const ev = el.tagName === "SELECT" || el.type === "color" ? "change" : "input";
    el.addEventListener(ev, () => {
      state[key] = fn ? fn(el.value) : el.value;
      staticDraw();
    });
  };
  bind("font", "font");
  bind("position", "position");
  bind("size", "size", parseFloat);
  bind("duration", "duration", parseFloat);
  bind("color", "color");
  bind("highlight", "highlight");
  $("text").addEventListener("input", staticDraw);

  $("size").addEventListener("input", (e) => ($("size-val").textContent = e.target.value));
  $("duration").addEventListener("input", (e) => ($("dur-val").textContent = parseFloat(e.target.value).toFixed(1) + "s"));

  video.addEventListener("loadedmetadata", staticDraw);
  video.addEventListener("seeked", () => { if (!previewing) staticDraw(); });

  /* ------------------------------------------------------------------ */
  /* 3. Bộ xem thử: mô phỏng đúng timing của preset render trên server  */
  /* ------------------------------------------------------------------ */
  let previewing = false;

  function staticDraw() {
    drawOverlay(clamp(state.duration * 0.5, 0.05, state.duration - 0.02));
  }

  function drawOverlay(t) {
    const dur = state.duration;
    const lines = $("text")
      .value.split("\n")
      .map((s) => s.trim())
      .filter(Boolean);

    otext.style.fontFamily = `"${state.font}", system-ui, sans-serif`;
    otext.style.fontSize = (state.size / 100) * (video.clientHeight || 480) + "px";
    otext.style.top = POS_TOP[state.position] || "50%";
    otext.style.color = state.color;

    if (!lines.length || t < 0 || t >= dur) {
      otext.style.opacity = 0;
      otext.innerHTML = "";
      return;
    }
    const per = dur / lines.length;
    const li = clamp(Math.floor(t / per), 0, lines.length - 1);
    const r = lineAnim(lines[li], t - li * per, per);

    otext.innerHTML = r.html;
    otext.style.opacity = r.opacity;
    otext.style.transform = `translate(-50%, -50%) ${r.transform}`;
    otext.style.filter = r.filter;
  }

  function lineAnim(line, t, per) {
    const H = video.clientHeight || 480;
    const fadeOut = Math.min(0.25, per * 0.35);
    const opacity =
      clamp(t / 0.12, 0, 1) * clamp((per - t) / fadeOut, 0, 1);
    const base = { html: esc(line), opacity, transform: "", filter: "none" };

    switch (state.preset) {
      case "pop": {
        const T = Math.min(0.45, per * 0.8);
        const p = clamp(t / T, 0, 1);
        const s = p < 0.48 ? 0.3 + 0.85 * (p / 0.48) : 1.15 - 0.15 * ((p - 0.48) / 0.52);
        return { ...base, transform: `scale(${s.toFixed(3)})` };
      }
      case "zoom": {
        const T = Math.min(0.54, per * 0.9);
        const p = clamp(t / T, 0, 1);
        const s = p < 0.55 ? 0.55 + 0.53 * (p / 0.55) : 1.08 - 0.08 * ((p - 0.55) / 0.45);
        return { ...base, transform: `scale(${s.toFixed(3)})` };
      }
      case "spin": {
        const p = clamp(t / Math.min(0.64, per), 0, 1);
        const ang = -20 * (1 - easeOut(clamp(t / 0.4, 0, 1)));
        const s = p < 0.55 ? 0.4 + 0.72 * (p / 0.55) : 1.12 - 0.12 * ((p - 0.55) / 0.45);
        return { ...base, transform: `rotate(${ang.toFixed(2)}deg) scale(${s.toFixed(3)})` };
      }
      case "slide": {
        const p = easeOut(clamp(t / Math.min(0.42, per), 0, 1));
        return { ...base, transform: `translateY(${((1 - p) * H * 0.16).toFixed(1)}px)` };
      }
      case "glow": {
        const p = clamp(t / Math.min(0.52, per), 0, 1);
        return { ...base, filter: `blur(${((1 - p) * 0.9).toFixed(2)}em)` };
      }
      case "type": {
        const n = line.length;
        const delay = clamp((per * 0.5) / Math.max(n, 1), 0.035, 0.11);
        const count = clamp(Math.floor(t / delay) + 1, 1, n);
        const cur = count < n ? '<span class="cursor">▕</span>' : "";
        return { ...base, html: esc(line.slice(0, count)) + cur };
      }
      case "words": {
        const words = line.split(/\s+/);
        const step = clamp((per * 0.6) / words.length, 0.18, 0.65);
        const idx = clamp(Math.floor(t / step), 0, words.length - 1);
        const local = t - idx * step;
        const pop = local < 0.15 ? 1.25 - 0.25 * (local / 0.15) : 1;
        let html = "";
        for (let i = 0; i <= idx; i++) {
          if (i) html += " ";
          html +=
            i === idx
              ? `<span class="hl" style="transform:scale(${pop.toFixed(3)});color:${state.highlight}">${esc(words[i])}</span>`
              : esc(words[i]);
        }
        return { ...base, html };
      }
    }
    return base;
  }

  $("btn-preview").addEventListener("click", () => {
    if (previewing) return stopPreview();
    if (!$("text").value.trim()) return alert("Nhập nội dung chữ trước đã nhé!");
    previewing = true;
    $("btn-preview").textContent = "⏸ Dừng xem thử";
    $("stage-badge").style.display = "none";
    video.currentTime = 0;
    video.play().catch(() => {});
    tick();
  });

  function tick() {
    if (!previewing) return;
    drawOverlay(video.currentTime);
    if (video.currentTime >= state.duration || video.ended) return stopPreview();
    requestAnimationFrame(tick);
  }

  function stopPreview() {
    previewing = false;
    $("btn-preview").textContent = "▶ Xem thử hoạt ảnh";
    video.pause();
    staticDraw();
  }
  video.addEventListener("pause", () => { if (previewing) stopPreview(); });

  /* ------------------------------------------------------------------ */
  /* 4. Gửi render lên server + theo dõi tiến độ                        */
  /* ------------------------------------------------------------------ */
  let pollTimer = null;

  $("btn-render").addEventListener("click", async () => {
    const text = $("text").value.trim();
    if (!state.file) return alert("Bạn chưa chọn video!");
    if (!text) return alert("Bạn chưa nhập nội dung chữ!");

    const fd = new FormData();
    fd.append("video", state.file);
    fd.append("text", text);
    fd.append("preset", state.preset);
    fd.append("font", state.font);
    fd.append("size", state.size);
    fd.append("duration", state.duration);
    fd.append("color", state.color);
    fd.append("highlight", state.highlight);
    fd.append("position", state.position);

    hide($("step-result"));
    show($("step-progress"));
    $("bar-fill").style.width = "0%";
    $("p-sub").textContent = "Đang tải video lên server…";
    $("step-edit").scrollIntoView({ behavior: "smooth", block: "start" });

    try {
      const r = await fetch("/api/render", { method: "POST", body: fd });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(j.error || "Server không nhận được yêu cầu");
      poll(j.job_id);
    } catch (e) {
      fail(e.message || String(e));
    }
  });

  function poll(jobId) {
    clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
      let j;
      try {
        const r = await fetch("/api/status/" + jobId);
        j = await r.json();
        if (!r.ok) throw new Error(j.error);
      } catch (e) {
        return; // mất mạng tạm thời -> thử lại sau
      }
      if (j.status === "done") {
        clearInterval(pollTimer);
        success(j.download_url);
      } else if (j.status === "error") {
        clearInterval(pollTimer);
        fail(j.error);
      } else {
        const p = Math.round(j.progress || 0);
        $("bar-fill").style.width = p + "%";
        $("p-sub").textContent =
          j.status === "queued" ? "Đang chờ tới lượt trên server…" : `Đang render: ${p}%`;
      }
    }, 1200);
  }

  function success(url) {
    hide($("step-progress"));
    show($("step-result"));
    $("result").src = url;
    $("btn-download").href = url;
    $("step-result").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function fail(msg) {
    clearInterval(pollTimer);
    hide($("step-progress"));
    show($("step-edit"));
    let box = $("step-edit").querySelector(".err");
    if (!box) {
      box = document.createElement("div");
      box.className = "err";
      $("step-edit").prepend(box);
    }
    box.innerHTML = "⚠️ " + esc(msg) + "<br>Bạn thử lại, hoặc chọn video ngắn hơn / giảm cỡ chữ.";
    box.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  $("btn-again").addEventListener("click", () => {
    hide($("step-result"));
    show($("step-upload"));
    const box = $("step-edit").querySelector(".err");
    if (box) box.remove();
    if (state.file) URL.revokeObjectURL(video.src);
    state.file = null;
    video.src = "";
    fileInput.value = "";
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
})();
