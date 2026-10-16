/* Shot Director UI: vanilla JS, no bundler, no CDN. */
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const h = (tag, attrs = {}, ...kids) => {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) el.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kids.flat()) if (k != null) el.append(k.nodeType ? k : document.createTextNode(k));
  return el;
};

const S = {
  config: null, engines: [], presets: [], options: null, samples: [],
  source: null, presetId: "dolly-in", lens: null, mood: null, duration: 5, resolution: "720p",
  angle: { azimuth: 0, elevation: 0, distance: "medium" }, useAngle: false,
  engineId: "demo", model: null, cat: "all",
  view: "still", stillUrl: null, reframedUrl: null, result: null, busy: false,
  timeline: [], estimate: null, gallery: [],
};

async function api(path, opts = {}) {
  const init = { method: opts.method || "GET", headers: {} };
  if (opts.json) { init.method = opts.method || "POST"; init.headers["Content-Type"] = "application/json"; init.body = JSON.stringify(opts.json); }
  if (opts.form) { init.method = "POST"; init.body = opts.form; }
  let r;
  try { r = await fetch(path, init); } catch (e) { throw { message: "Can't reach the Shot Director server.", hint: "Is it still running?" }; }
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw { status: r.status, ...(body.detail && typeof body.detail === "object" ? body.detail : body), message: body.message || (body.detail && body.detail.message) || `Request failed (${r.status})` };
  return body;
}

/* ---------- toast / errors ---------- */
let toastT;
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove("show"), 2200); }
function showError(e) {
  const box = $("#errorBox");
  box.replaceChildren(h("b", {}, e.message || "Something went wrong"), e.hint ? h("span", {}, e.hint) : "", ...(e.needs && e.needs.length ? [h("br"), h("span", {}, "Needs: " + e.needs.join(" · "))] : []));
  box.classList.remove("hidden");
}
const clearError = () => $("#errorBox").classList.add("hidden");

/* ---------- init ---------- */
async function init() {
  const [cfg, eng, pre, sam, gal] = await Promise.all([api("/api/config"), api("/api/engines"), api("/api/presets"), api("/api/samples"), api("/api/gallery").catch(() => ({ items: [] }))]);
  S.config = cfg; S.engines = eng.engines; S.engineId = eng.default; S.presets = pre.presets; S.options = pre.options;
  S.samples = sam.samples; S.gallery = gal.items || [];
  S.lens = null; S.mood = null; S.duration = (S.options.durations || [5]).includes(5) ? 5 : S.options.durations[0];
  S.badge = cfg.badge;
  if (cfg.demo && (S.options.resolutions || []).includes("480p")) S.resolution = "480p";  // live simulated renders are quicker at 480p
  renderTop(); renderSamples(); renderCats(); renderMoves(); renderChips(); renderEngines(); renderDial(); renderGallery(); renderCoverage([]); renderTimeline();
  $("#footStatus").textContent = `v${cfg.version} · ${cfg.demo ? "DEMO mode (no keys, simulated)" : "live engines"} · cost cap ${cfg.max_credits_per_run} credits/run`;
  if (S.samples[0]) await setSource(S.samples[0].id);
  bind();
}

function renderTop() {
  const pill = $("#modePill");
  if (S.config.demo) { pill.textContent = "DEMO · no keys"; pill.className = "pill demo"; pill.classList.remove("hidden"); }
  const e = S.engines.find(x => x.id === S.engineId);
  $("#enginePill").textContent = "engine: " + (e ? e.label : S.engineId);
  if (S.config.repo_url) { $("#repoLink").href = S.config.repo_url; } else { $("#repoLink").removeAttribute("href"); }
}

/* ---------- source ---------- */
function renderSamples() {
  const box = $("#samples"); box.replaceChildren();
  for (const s of S.samples) {
    box.append(h("button", { class: "sample" + (S.source && S.source.id === s.id ? " on" : ""), title: `${s.title}: ${s.blurb}`, "data-id": s.id, onclick: () => setSource(s.id) }, h("img", { src: s.url, alt: s.title, loading: "lazy" })));
  }
}
async function setSource(id, extra) {
  const s = S.samples.find(x => x.id === id) || extra;
  if (!s) return;
  S.source = { id: s.id, url: s.url, name: s.title || s.name };
  S.reframedUrl = null; S.result = null;
  const prev = $("#srcPreview"); prev.src = s.url; prev.classList.remove("hidden"); $("#dropHint").classList.add("hidden");
  if (s.title && !$("#scene").value) { /* leave scene empty by default so committed example clips can replay */ }
  renderSamples(); setStill(s.url); setVideo(null); showSim(false); updateActions(); refreshEstimate();
  $("#stageTitle").textContent = S.source.name || "Source frame";
  $("#getCov").disabled = false;
}
async function uploadFile(file) {
  if (!file) return;
  const fd = new FormData(); fd.append("file", file);
  try { clearError(); const r = await api("/api/upload", { form: fd }); await setSource(r.id, { id: r.id, url: r.url, name: r.name }); toast("Image uploaded"); }
  catch (e) { showError(e); }
}

/* ---------- moves & options ---------- */
const CAT_LABEL = { all: "All", dolly: "Dolly", jib: "Jib / crane", orbit: "Orbit", special: "Special", static: "Static" };
function renderCats() {
  const cats = ["all", ...new Set(S.presets.map(p => p.category))];
  const box = $("#cats"); box.replaceChildren();
  for (const c of cats) box.append(h("button", { class: "chip" + (S.cat === c ? " on" : ""), onclick: () => { S.cat = c; renderCats(); renderMoves(); } }, CAT_LABEL[c] || c[0].toUpperCase() + c.slice(1)));
}
let io;
function renderMoves() {
  const box = $("#moves"); box.replaceChildren();
  if (io) io.disconnect();
  io = new IntersectionObserver(es => es.forEach(en => { const v = en.target; if (en.isIntersecting) { v.play().catch(() => {}); } else v.pause(); }), { root: box, threshold: 0.4 });
  for (const p of S.presets.filter(p => S.cat === "all" || p.category === S.cat)) {
    const v = h("video", { src: p.thumb, muted: true, loop: true, playsinline: true, preload: "metadata", "aria-hidden": "true" }); v.muted = true;
    const b = h("button", { class: "move" + (p.id === S.presetId ? " on" : ""), role: "option", "aria-selected": p.id === S.presetId, title: p.description, onclick: () => { S.presetId = p.id; renderMoves(); refreshEstimate(); }, onmouseenter: () => v.play().catch(() => {}) }, v, h("span", {}, p.name), p.lora ? h("em", { class: "lora", title: "Official LTX-2 camera-control LoRA available" }, "LoRA") : null);
    box.append(b); io.observe(v);
  }
}
function chipGroup(id, items, current, onpick, nullable) {
  const box = $(id); box.replaceChildren();
  for (const it of items) {
    const on = current === it.id;
    box.append(h("button", { class: "chip" + (on ? " on" : ""), onclick: () => onpick(nullable && on ? null : it.id) }, it.label));
  }
}
function renderChips() {
  chipGroup("#lensChips", S.options.lens, S.lens, v => { S.lens = v; renderChips(); }, true);
  chipGroup("#moodChips", S.options.mood, S.mood, v => { S.mood = v; renderChips(); }, true);
  chipGroup("#durChips", S.options.durations.map(d => ({ id: d, label: d + " s" })), S.duration, v => { S.duration = v; renderChips(); refreshEstimate(); });
  chipGroup("#resChips", S.options.resolutions.map(r => ({ id: r, label: r })), S.resolution, v => { S.resolution = v; renderChips(); refreshEstimate(); });
}

/* ---------- angle dial ---------- */
const C = 120, R = 92;
function polar(az, r = R) { const a = az * Math.PI / 180; return [C + r * Math.sin(a), C + r * Math.cos(a)]; }  // 0 deg = bottom (front of subject), + = to the right
function renderDial() {
  const ticks = $("#dialTicks"); ticks.replaceChildren();
  for (const [az, t] of [[0, "front"], [90, "right"], [180, "back"], [270, "left"]]) {
    const [x, y] = polar(az, R + 0); const [tx, ty] = polar(az, R - 18);
    ticks.append(h("circle", { cx: x, cy: y, r: 2.6, fill: "#2e3447" }));
    const el = document.createElementNS("http://www.w3.org/2000/svg", "text");
    el.setAttribute("x", tx); el.setAttribute("y", ty + 3); el.setAttribute("text-anchor", "middle"); el.setAttribute("class", "tick"); el.textContent = t; ticks.append(el);
  }
  chipGroup("#distChips", [{ id: "close", label: "Close" }, { id: "medium", label: "Medium" }, { id: "wide", label: "Wide" }], S.angle.distance, v => { S.angle.distance = v; updateDial(); });
  updateDial();
}
let angleT;
async function updateDial() {
  const [x, y] = polar(S.angle.azimuth);
  $("#dialCam").setAttribute("transform", `translate(${x} ${y})`);
  const l = $("#dialLine"); l.setAttribute("x2", x); l.setAttribute("y2", y);
  $("#elev").value = S.angle.elevation;
  chipGroup("#distChips", [{ id: "close", label: "Close" }, { id: "medium", label: "Medium" }, { id: "wide", label: "Wide" }], S.angle.distance, v => { S.angle.distance = v; updateDial(); });
  clearTimeout(angleT);
  angleT = setTimeout(async () => {
    try { const r = await api(`/api/angle?azimuth=${S.angle.azimuth}&elevation=${S.angle.elevation}&distance=${S.angle.distance}`); $("#anglePrompt").textContent = r.prompt; } catch (e) { /* non-fatal */ }
  }, 80);
}
function dialPointer(ev) {
  const svg = $("#dial"); const r = svg.getBoundingClientRect();
  const px = (ev.clientX - r.left) / r.width * 240 - C, py = (ev.clientY - r.top) / r.height * 240 - C;
  let az = Math.atan2(px, py) * 180 / Math.PI; az = Math.round(az / 15) * 15;
  S.angle.azimuth = ((az + 180) % 360 + 360) % 360 - 180; updateDial();
}

/* ---------- engines & estimate ---------- */
function renderEngines() {
  const box = $("#engines"); box.replaceChildren();
  for (const e of S.engines) {
    const ok = e.health.ok;
    const tag = e.kind === "router" || e.kind === "cloud" ? h("span", { class: "tag paid" }, "CREDITS") : h("span", { class: "tag free" }, e.kind === "demo" ? "FREE · SIMULATED" : "FREE · LOCAL");
    const open = e.kind === "open" ? h("span", { class: "tag", title: "Open-weights models only" }, "OPEN WEIGHTS") : null;
    box.append(h("button", { class: "eng" + (e.id === S.engineId ? " on" : "") + (ok ? "" : " off"), role: "radio", "aria-checked": e.id === S.engineId, disabled: false, onclick: () => ok ? pickEngine(e.id) : toast(e.health.detail || "Engine not ready"), title: e.health.detail },
      h("i", { class: "dot " + e.health.status }), h("div", {}, h("b", {}, e.label, tag, open), h("small", {}, ok ? e.description : e.health.detail || e.description))));
  }
  const cur = S.engines.find(e => e.id === S.engineId);
  const row = $("#modelRow");
  if (cur && cur.models) {
    row.classList.remove("hidden");
    const sel = $("#modelSel"); sel.replaceChildren(h("option", { value: "" }, "Preset default"), ...cur.models.map(m => h("option", { value: m.id }, `${m.label || m.id}`)));
    sel.value = S.model || "";
  } else row.classList.add("hidden");
  renderTop();
}
function pickEngine(id) { S.engineId = id; S.model = null; renderEngines(); refreshEstimate(); }
function shotBody(extra = {}) {
  return { source_id: S.source.id, preset_id: S.presetId, engine: S.engineId, scene: $("#scene").value.trim(), lens: S.lens, mood: S.mood, duration: S.duration, resolution: S.resolution, model: S.model || null, angle: S.useAngle ? S.angle : null, ...extra };
}
let estT;
function refreshEstimate() {
  clearTimeout(estT);
  const el = $("#estimate");
  if (!S.source) { el.textContent = ""; return; }
  estT = setTimeout(async () => {
    try {
      const e = await api("/api/estimate", { json: shotBody() });
      S.estimate = e;
      const cost = e.credits == null ? "unknown cost" : (e.credits === 0 ? "Free" : `≈ ${e.credits.toFixed(0)} credits${e.usd != null ? ` (~$${e.usd.toFixed(2)})` : ""}`);
      el.className = "estimate" + (e.over_cap ? " over" : "");
      el.replaceChildren(h("b", {}, cost), e.exact ? " · exact" : e.credits === 0 ? "" : " · estimate", e.seconds ? ` · ~${Math.round(e.seconds)} s` : "", h("br"), e.over_cap ? `Over your ${e.cap}-credit cap. Raise MAX_CREDITS_PER_RUN to allow it.` : (e.note || ""));
    } catch (err) { S.estimate = null; el.className = "estimate over"; el.textContent = err.message || "Estimate unavailable"; }
    updateActions();
  }, 120);
}

/* ---------- stage ---------- */
function setStill(url) { S.stillUrl = url; const i = $("#stillImg"); i.src = url || ""; applyView(); }
function setVideo(url) { const v = $("#vid"); if (url) { v.src = url; v.load(); v.play().catch(() => {}); } else { v.removeAttribute("src"); v.load(); } S.videoUrl = url; applyView(); }
function applyView() {
  const hasStill = !!S.stillUrl, hasVid = !!S.videoUrl;
  let view = S.view; if (!hasVid && view !== "still") view = "still";
  $("#empty").classList.toggle("hidden", hasStill || hasVid);
  $("#stillImg").classList.toggle("hidden", !hasStill || view === "video");
  $("#vid").classList.toggle("hidden", !hasVid || view === "still");
  if (view === "split") { $("#stillImg").classList.remove("hidden"); }
  $("#stage").classList.toggle("split", view === "split");
  $("#wipeWrap").classList.toggle("hidden", view !== "split");
  $$("#abSeg button").forEach(b => { b.classList.toggle("on", b.dataset.view === view); b.disabled = !hasVid && b.dataset.view !== "still"; });
}
function setView(v) { S.view = v; applyView(); }
/* Provenance badge: amber = simulated demo fixture, green = real model output. Never show neither for a demo result. */
function showSim(on, real) {
  const b = $("#simBadge");
  const r = real && real.real;
  b.classList.toggle("hidden", !(on || r));
  b.classList.toggle("real", !!r);
  if (r) { b.textContent = real.badge || "Real LTX-2.3 output (Comfy Cloud)"; b.title = "Real model output generated on Comfy Cloud and replayed from examples/real/"; }
  else if (on) { b.textContent = S.badge; b.title = "This output was produced by the Demo engine, not by a generative model"; }
}

function updateActions() {
  const r = S.result; const vid = r && r.artifacts.find(a => a.kind === "video");
  $("#addTl").disabled = !vid;
  for (const [id, url] of [["#dlVideo", vid && vid.url], ["#dlRecipe", r && r.recipe_url]]) { const a = $(id); if (url) { a.href = url; a.hidden = false; } else a.hidden = true; }
  $("#go").disabled = S.busy || !S.source || (S.estimate && S.estimate.over_cap) || !S.estimate;
  $("#go").textContent = S.busy ? "Working…" : "Generate shot";
  $("#getCov").disabled = S.busy || !S.source;
  $("#previewAngle").disabled = S.busy || !S.source;
}

/* ---------- jobs ---------- */
function runJob(start, { title, onDone }) {
  return new Promise(async (resolve) => {
    clearError(); S.busy = true; updateActions();
    const prog = $("#progress"), bar = $("#bar"), msg = $("#progMsg"), log = $("#log");
    prog.classList.remove("hidden"); bar.style.width = "2%"; msg.textContent = "Submitting…"; log.replaceChildren();
    const finish = () => { S.busy = false; prog.classList.add("hidden"); updateActions(); resolve(); };
    let job;
    try { job = await start(); } catch (e) { showError(e); return finish(); }
    const es = new EventSource(`/api/jobs/${job.id}/events`);
    es.onmessage = ev => {
      const d = JSON.parse(ev.data);
      if (d.type === "progress") { bar.style.width = Math.round(d.value * 100) + "%"; if (d.message) msg.textContent = d.message; }
      if (d.message) { log.prepend(h("li", {}, `${String(d.t ?? "").padStart(5)} s  ${d.message}`)); if (!d.type || d.type === "status") msg.textContent = d.message; }
      if (d.type === "estimate") log.prepend(h("li", {}, `estimate: ${d.estimate.credits ?? "?"} credits`));
      if (d.type === "done") { es.close(); api(`/api/jobs/${job.id}`).then(j => { onDone(j.result); finish(); }).catch(e => { showError(e); finish(); }); }
      if (d.type === "error") { es.close(); showError(d.error); finish(); }
    };
    es.onerror = () => { if (es.readyState === 2) { showError({ message: "Lost the live connection.", hint: "The job may still be running: reload to check." }); finish(); } };
  });
}
async function confirmSpend(est) {
  if (!["router", "cloud"].includes(S.engineId)) return true;
  $("#confirmText").textContent = est && est.credits != null ? `Estimated ${est.credits.toFixed(0)} credits (cap ${est.cap}). The request is submitted once and never retried.` : "The cost is unknown. Continue only if you allowed unknown costs.";
  const d = $("#confirm"); d.returnValue = ""; d.showModal();  // reset: Esc keeps the previous returnValue ("ok") and would silently approve spending
  return new Promise(res => d.addEventListener("close", () => res(d.returnValue === "ok"), { once: true }));
}

async function generate() {
  if (!S.source) return;
  if (S.useAngle && !$("#useAngle").checked) S.useAngle = false;
  if (!(await confirmSpend(S.estimate))) return;
  const preset = S.presets.find(p => p.id === S.presetId);
  $("#stageTitle").textContent = `${preset.name} · generating…`;
  await runJob(() => api("/api/shots", { json: shotBody({ confirm_cost: true }) }), {
    onDone: r => {
      S.result = r; const vid = r.artifacts.find(a => a.kind === "video");
      setVideo(vid.url); S.view = "video"; applyView(); showSim(r.simulated, r);
      $("#stageTitle").textContent = `${preset.name} · ${S.source.name}`;
      const v = $("#vid"); v.muted = true; v.play().catch(() => {}); updateActions();
    },
  });
}

async function previewAngle() {
  if (!S.source) return;
  if (!(await confirmSpend(null))) return;
  await runJob(() => api("/api/reframe", { json: { source_id: S.source.id, engine: S.engineId, angle: S.angle, scene: $("#scene").value.trim(), model: S.model || null, confirm_cost: true } }), {
    onDone: r => {
      const img = r.artifacts[0]; S.reframedUrl = img.url; setStill(img.url); setView("still"); showSim(r.simulated, r);
      $("#stageTitle").textContent = "Re-shoot: " + img.label; $("#useAngle").checked = true; S.useAngle = true;
      toast("Angle previewed: it will be used for the shot");
    },
  });
}

/* ---------- coverage ---------- */
function renderCoverage(items) {
  const box = $("#cov"); box.replaceChildren();
  const labels = ["Wide", "Medium", "Close-up", "Low angle", "High angle", "Over-shoulder / profile"];
  const byLabel = Object.fromEntries(items.map(a => [a.label, a]));
  for (const l of labels) {
    const a = byLabel[l];
    if (!a) { box.append(h("div", { class: "tile" }, l)); continue; }
    box.append(h("div", { class: "tile has" }, h("img", { src: a.url, alt: l, loading: "lazy" }), h("span", { class: "lbl" }, l),
      h("button", { class: "animate", title: "Use this still as the new source frame", onclick: async () => { try { const r = await api("/api/adopt", { json: { url: a.url } }); await setSource(r.id, { id: r.id, url: r.url, name: `${S.source ? S.source.name : "Shot"} · ${l}` }); toast("Now animating this angle"); } catch (e) { showError(e); } } }, "ANIMATE")));
  }
}
async function getCoverage() {
  if (!S.source) return;
  if (!(await confirmSpend(null))) return;
  await runJob(() => api("/api/coverage", { json: { source_id: S.source.id, engine: S.engineId, scene: $("#scene").value.trim(), model: S.model || null, confirm_cost: true } }), {
    onDone: r => { renderCoverage(r.artifacts); showSim(r.simulated, r); toast(r.simulated ? "Coverage ready (simulated)" : "Coverage ready"); },
  });
}

/* ---------- timeline ---------- */
function renderTimeline() {
  const ol = $("#timeline"); ol.replaceChildren();
  $("#tlEmpty").classList.toggle("hidden", S.timeline.length > 0);
  $("#exportSeq").disabled = S.timeline.length < 1;
  let dragI = null;
  S.timeline.forEach((c, i) => {
    const li = h("li", { class: "clip", draggable: "true",
      ondragstart: e => { dragI = i; li.classList.add("drag"); e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", String(i)); },
      ondragend: () => li.classList.remove("drag"),
      ondragover: e => { e.preventDefault(); li.classList.add("over"); }, ondragleave: () => li.classList.remove("over"),
      ondrop: e => { e.preventDefault(); if (dragI == null || dragI === i) return; const [m] = S.timeline.splice(dragI, 1); S.timeline.splice(i, 0, m); renderTimeline(); } },
      h("span", { class: "grip", "aria-hidden": "true" }, "⋮⋮"), h("video", { src: c.url, muted: true, loop: true, playsinline: true, onmouseenter: e => e.target.play().catch(() => {}), onmouseleave: e => e.target.pause() }),
      h("div", {}, h("b", {}, c.label), h("small", {}, `${c.real ? "real · " : c.sim ? "simulated · " : ""}shot ${i + 1}`)),
      h("button", { class: "x", "aria-label": "Remove from timeline", onclick: () => { S.timeline.splice(i, 1); renderTimeline(); } }, "×"));
    ol.append(li);
  });
}
function addToTimeline(url, label, sim, real) { S.timeline.push({ url, label, sim, real }); if (S.timeline.length > 12) S.timeline.shift(); renderTimeline(); toast("Added to timeline"); }
async function exportSeq() {
  const btn = $("#exportSeq"); btn.disabled = true; btn.textContent = "Stitching…";
  try {
    const r = await api("/api/sequence", { json: { clips: S.timeline.map(c => c.url), crossfade: $("#xfade").checked ? 0.4 : 0 } });
    const v = $("#seqVid"); v.src = r.url; v.load(); v.play().catch(() => {});
    $("#seqDl").href = r.url; $("#seqRecipe").href = r.recipe_url; $("#seqOut").classList.remove("hidden");
    toast(r.recipe.simulated ? "Sequence ready (simulated clips)" : "Sequence ready");
  } catch (e) { showError(e); }
  btn.textContent = "Export sequence"; btn.disabled = S.timeline.length < 1;
}

/* ---------- gallery ---------- */
function renderGallery() {
  const box = $("#gallery"); box.replaceChildren();
  const items = S.gallery.filter(i => i.kind === "clip" || i.kind === "sequence");
  const nReal = items.filter(i => i.real).length, nSim = items.length - nReal;
  $("#galNote").className = "hint warn" + (nSim ? "" : " hidden");
  $("#galReal").textContent = nReal ? `${nReal} real clip${nReal > 1 ? "s" : ""} (green badge): generated by a model on Comfy Cloud, replayed from examples/real/.` : "No real model clips have been added yet (see docs/REAL_RUN.md).";
  if (!items.length) { box.append(h("p", { class: "hint" }, "Run scripts/make_fixtures.py to generate example clips.")); return; }
  for (const it of items) {
    const pn = (S.presets.find(p => p.id === it.preset) || {}).name || it.preset, sn = (S.samples.find(x => x.sample_id === it.input) || {}).title || it.input;
    const label = it.title || `${pn} · ${sn}`;
    const v = h("video", { src: it.url, muted: true, loop: true, playsinline: true, preload: "metadata", onmouseenter: e => e.target.play().catch(() => {}), onmouseleave: e => e.target.pause() }); v.muted = true;
    const tag = h("em", { class: "g-tag " + (it.real ? "real" : "sim") }, it.real ? "REAL" : "SIM");
    box.append(h("button", { class: "g-item" + (it.real ? " is-real" : ""), title: label + (it.real ? ` (${it.badge})` : " (simulated placeholder)"), onclick: () => {
      const rurl = it.recipe_url || (it.recipe ? `/examples/outputs/${it.recipe}` : null);
      setVideo(it.url); S.result = { artifacts: [{ kind: "video", url: it.url }], recipe_url: rurl, simulated: !!it.simulated, real: !!it.real, badge: it.badge };
      S.view = "video"; applyView(); showSim(!!it.simulated, S.result); $("#stageTitle").textContent = label; updateActions();
    } }, v, tag, h("span", {}, label)));
  }
}

/* ---------- caption ---------- */
function caption() {
  const p = S.presets.find(x => x.id === S.presetId); const r = S.result;
  const src = S.source ? S.source.name : "a single frame";
  const tags = "Open source, built around @ComfyUI. #OpenSourceHiggsfield";
  if (r && r.real) {
    // The real clips were prompt-only runs of the official template in the Comfy Cloud web UI; the app did not generate them.
    return `Real LTX-2.3 clip on "${src}": made in Comfy Cloud with a prompt only (no camera LoRA, unedited). The camera move comes from the Shot Director preset library; the app is a shot-planning workflow around it. ${tags}`;
  }
  const eng = S.engines.find(e => e.id === S.engineId);
  if (!r || r.simulated) return `${p.name} on "${src}" in Shot Director: (Demo mode: a simulated camera move over a still, not model output.) One frame in, full coverage out. ${tags}`;
  return `${p.name} on "${src}", directed with Shot Director (engine: ${eng ? eng.label : S.engineId}). One frame in, full coverage out. ${tags}`;
}

/* ---------- wiring ---------- */
function bind() {
  const drop = $("#drop"), file = $("#file");
  drop.addEventListener("click", () => file.click());
  drop.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); file.click(); } });
  file.addEventListener("change", () => uploadFile(file.files[0]));
  ["dragenter", "dragover"].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.add("over"); }));
  ["dragleave", "drop"].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.remove("over"); }));
  drop.addEventListener("drop", e => uploadFile(e.dataTransfer.files[0]));
  $$(".tab").forEach(t => t.addEventListener("click", () => { $$(".tab").forEach(x => { x.classList.toggle("active", x === t); x.setAttribute("aria-selected", x === t); }); $("#tab-moves").classList.toggle("hidden", t.dataset.tab !== "moves"); $("#tab-angle").classList.toggle("hidden", t.dataset.tab !== "angle"); }));
  $("#abSeg").addEventListener("click", e => { const b = e.target.closest("button"); if (b && !b.disabled) setView(b.dataset.view); });
  $("#wipe").addEventListener("input", e => $("#stage").style.setProperty("--cut", e.target.value + "%"));
  const dial = $("#dial"); let drag = false;
  dial.addEventListener("pointerdown", e => { drag = true; dial.setPointerCapture(e.pointerId); dialPointer(e); });
  dial.addEventListener("pointermove", e => drag && dialPointer(e)); dial.addEventListener("pointerup", () => drag = false);
  dial.addEventListener("keydown", e => { const d = e.key === "ArrowRight" ? 15 : e.key === "ArrowLeft" ? -15 : 0; if (d) { e.preventDefault(); S.angle.azimuth = ((S.angle.azimuth + d + 180) % 360 + 360) % 360 - 180; updateDial(); } });
  $("#elev").addEventListener("input", e => { S.angle.elevation = +e.target.value; updateDial(); });
  $("#previewAngle").addEventListener("click", previewAngle);
  $("#useAngle").addEventListener("change", e => { S.useAngle = e.target.checked; refreshEstimate(); });
  $("#modelSel").addEventListener("change", e => { S.model = e.target.value || null; refreshEstimate(); });
  $("#scene").addEventListener("input", () => refreshEstimate());
  $("#go").addEventListener("click", generate);
  $("#getCov").addEventListener("click", getCoverage);
  $("#addTl").addEventListener("click", () => { const v = S.result && S.result.artifacts.find(a => a.kind === "video"); if (v) addToTimeline(v.url, $("#stageTitle").textContent.split(" · ")[0] || "Shot", S.result.simulated, S.result.real); });
  $("#exportSeq").addEventListener("click", exportSeq);
  $("#copyCaption").addEventListener("click", async () => { try { await navigator.clipboard.writeText(caption()); toast("Caption copied"); } catch { toast("Copy blocked: select the text manually"); prompt("Caption", caption()); } });
}

init().catch(e => { document.body.prepend(h("div", { class: "errorbox", style: "position:static;margin:20px" }, h("b", {}, "Couldn't start the UI"), h("span", {}, e.message || String(e)))); });
