/* Shot Director: static demo. No backend. Everything runs in this page.
   - Amber previs: a simplified in-browser depth-parallax camera (WebGL), simulated, not model output.
   - Green clips: real model output replayed from media/ (web copies).
   - Optional "run for real": direct fetch() calls to api.comfy.org with a key held in memory only. */
"use strict";
const $ = s => document.querySelector(s);
const API = "https://api.comfy.org";
const NEAR = 3.0, FAR = 30.0;                         // metres, same as the server's virtual camera
const CHANNELS = ["right", "up", "forward", "yaw", "pitch", "roll", "zoom"];
const S = { data: null, input: null, preset: null, cat: "all", glOk: false, raf: 0, apiKey: "", running: false };

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v; else if (k.startsWith("on")) el.addEventListener(k.slice(2), v); else el.setAttribute(k, v);
  }
  for (const c of kids.flat()) if (c != null) el.append(c.nodeType ? c : document.createTextNode(String(c)));
  return el;
}
const fmtCr = n => (n == null ? "?" : (Math.round(n * 10) / 10).toString());

/* ------------------------------------------------------------------ camera path (port of app/vcam.py CameraPath) */
function ease(name, t) {
  t = Math.min(Math.max(t, 0), 1);
  if (name === "linear") return t;
  if (name === "in") return t * t * t;
  if (name === "out") return 1 - (1 - t) ** 3;
  if (name === "snap") return t * t * t * (t * (6 * t - 15) + 10);
  return t * t * (3 - 2 * t);
}
function camAt(spec, t) {
  const te = ease(spec.ease || "inout", t), ks = [...spec.keys].sort((a, b) => a.t - b.t), out = {};
  for (const ch of CHANNELS) {
    const dflt = ch === "zoom" ? 1 : 0, pts = ks.map(k => [k.t, k[ch] ?? dflt]);
    if (te <= pts[0][0]) out[ch] = pts[0][1];
    else if (te >= pts[pts.length - 1][0]) out[ch] = pts[pts.length - 1][1];
    else for (let i = 0; i < pts.length - 1; i++) {
      const [t0, v0] = pts[i], [t1, v1] = pts[i + 1];
      if (te >= t0 && te <= t1) { out[ch] = v0 + (v1 - v0) * ((te - t0) / Math.max(t1 - t0, 1e-9)); break; }
    }
  }
  if (spec.shake) {   // deterministic handheld wobble
    const amps = { right: 0.035, up: 0.03, yaw: 0.45, pitch: 0.4, roll: 0.5 }, ph = { right: 0.3, up: 1.7, yaw: 2.9, pitch: 4.1, roll: 5.3 };
    for (const k of Object.keys(amps)) {
      const n = [0.9, 2.3, 4.1].reduce((a, f, j) => a + Math.sin(2 * Math.PI * f * t * 4 + ph[k] + j) / (j + 1), 0);
      out[k] += amps[k] * spec.shake * n;
    }
  }
  return out;
}
function rotation(yaw, pitch, roll) {   // R = Ry * Rx * Rz, camera frame x right, y down, z forward (as vcam._rotation)
  const [y, p, r] = [yaw, pitch, roll].map(d => d * Math.PI / 180);
  const mul = (a, b) => a.map((_, i) => [0, 1, 2].map(j => a[i][0] * b[0][j] + a[i][1] * b[1][j] + a[i][2] * b[2][j]));
  const ry = [[Math.cos(y), 0, Math.sin(y)], [0, 1, 0], [-Math.sin(y), 0, Math.cos(y)]];
  const rx = [[1, 0, 0], [0, Math.cos(p), -Math.sin(p)], [0, Math.sin(p), Math.cos(p)]];
  const rz = [[Math.cos(r), -Math.sin(r), 0], [Math.sin(r), Math.cos(r), 0], [0, 0, 1]];
  return mul(mul(ry, rx), rz);
}

/* ------------------------------------------------------------------ WebGL depth-parallax renderer */
const VS = "attribute vec2 p;varying vec2 v;void main(){v=p*0.5+0.5;gl_Position=vec4(p,0.,1.);}";
const FS = `precision highp float;varying vec2 v;uniform sampler2D img,dep;uniform vec3 cam;uniform mat3 R;uniform float zoom,aspect;
const float NEAR=${NEAR.toFixed(1)},FAR=${FAR.toFixed(1)},TH=0.5774;
float zAt(vec2 uv){return NEAR+(FAR-NEAR)*texture2D(dep,clamp(uv,0.,1.)).r;}
vec2 proj(vec3 P){return vec2(P.x/P.z/TH*0.5+0.5,0.5+P.y/P.z*aspect/TH*0.5);}
void main(){
  vec2 n=v*2.-1.;
  vec3 ray=vec3(n.x*TH/zoom,-n.y*TH/aspect/zoom,1.);
  vec3 D=R*ray;
  float z0=max(NEAR*0.6,cam.z+0.15);float zPrev=z0,zp=zPrev;
  vec3 P=cam+D*((zp-cam.z)/D.z);
  float dPrev=zp-zAt(proj(P));
  vec2 hit=proj(P);bool found=false;
  for(int i=0;i<72;i++){
    zp=z0+(FAR*1.15-z0)*float(i+1)/72.;
    P=cam+D*((zp-cam.z)/D.z);
    vec2 uv=proj(P);
    float d=zp-zAt(uv);
    if(d>=0.){float a=dPrev/(dPrev-d+1e-5);float zi=mix(zPrev,zp,clamp(a,0.,1.));vec3 Q=cam+D*((zi-cam.z)/D.z);hit=proj(Q);found=true;break;}
    zPrev=zp;dPrev=d;hit=uv;
  }
  vec2 uv=clamp(hit,0.,1.);
  gl_FragColor=vec4(texture2D(img,uv).rgb,1.);
}`;
const GL = { gl: null, prog: null, tex: {}, loc: {}, key: null };
function glInit() {
  const c = $("#gl");
  const gl = c.getContext("webgl", { preserveDrawingBuffer: true, antialias: false });
  if (!gl) return false;
  const sh = (t, src) => { const s = gl.createShader(t); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s)); return s; };
  const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, FS)); gl.linkProgram(pr);
  if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(pr));
  gl.useProgram(pr);
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const a = gl.getAttribLocation(pr, "p"); gl.enableVertexAttribArray(a); gl.vertexAttribPointer(a, 2, gl.FLOAT, false, 0, 0);
  for (const u of ["img", "dep", "cam", "R", "zoom", "aspect"]) GL.loc[u] = gl.getUniformLocation(pr, u);
  gl.uniform1i(GL.loc.img, 0); gl.uniform1i(GL.loc.dep, 1);
  GL.gl = gl; GL.prog = pr; return true;
}
function loadTex(unit, image) {
  const gl = GL.gl, t = gl.createTexture();
  gl.activeTexture(gl.TEXTURE0 + unit); gl.bindTexture(gl.TEXTURE_2D, t);
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
  for (const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR], [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v);
  return t;
}
const loadImg = src => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error("could not load " + src)); i.src = src; });
async function glLoadInput(inp) {
  if (GL.key === inp.id) return;
  const [img, dep] = await Promise.all([loadImg(inp.still), loadImg(inp.depth)]);
  const gl = GL.gl;
  if (GL.tex.img) gl.deleteTexture(GL.tex.img); if (GL.tex.dep) gl.deleteTexture(GL.tex.dep);
  GL.tex.img = loadTex(0, img); GL.tex.dep = loadTex(1, dep); GL.key = inp.id;
}
function glDraw(c) {
  const gl = GL.gl, cv = $("#gl"), R = rotation(c.yaw, c.pitch, c.roll);
  gl.viewport(0, 0, cv.width, cv.height);
  gl.uniform3f(GL.loc.cam, c.right, -c.up, c.forward);
  gl.uniformMatrix3fv(GL.loc.R, false, new Float32Array([R[0][0], R[1][0], R[2][0], R[0][1], R[1][1], R[2][1], R[0][2], R[1][2], R[2][2]]));
  gl.uniform1f(GL.loc.zoom, c.zoom); gl.uniform1f(GL.loc.aspect, cv.width / cv.height);
  gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
}

/* ------------------------------------------------------------------ UI */
function realFor(inp, pre) { return S.data.clips.filter(c => c.input === inp && c.preset === pre).sort((a, b) => (b.rating ?? -1) - (a.rating ?? -1))[0]; }
function setBadge(kind, text) {
  const b = $("#badge");
  if (!kind) { b.className = "b hidden"; return; }
  b.className = "b " + kind; b.textContent = text;
}
function showCanvas() { $("#vid").pause(); $("#vid").classList.add("hidden"); $("#gl").classList.remove("hidden"); }
function showVideo(src) { const v = $("#vid"); $("#gl").classList.add("hidden"); v.classList.remove("hidden"); v.src = src; v.muted = true; v.play().catch(() => {}); }
function infoReal(c) {
  const box = $("#info"); box.replaceChildren(
    h("p", {}, h("b", {}, `${c.model_label} via ${c.platform}`), ` · ${c.preset_name} on ${c.input_title}`),
    h("p", {}, h("span", { class: "k" }, "credits "), c.credits_used ? fmtCr(c.credits_used) : "0 (free tier)", h("span", { class: "k" }, "  ·  own rating "), c.rating != null ? c.rating + "/10" : "n/a", h("span", { class: "k" }, "  ·  request id "), c.request_id || "n/a (Comfy Cloud web UI)"),
    h("p", {}, c.quality || ""), c.verdict ? h("p", { class: "k" }, c.verdict) : null,
    h("p", { class: "k" }, "Prompt: " + (c.prompt || "")));
}
function renderInputs() {
  const box = $("#inputs"); box.replaceChildren();
  for (const i of S.data.inputs) box.append(h("button", { class: i.id === S.input.id ? "on" : "", title: i.title, onclick: () => selectInput(i.id) }, h("img", { src: i.still, alt: i.title })));
  $("#inputNote").textContent = `${S.input.title}: ${S.input.blurb}`;
}
function renderCats() {
  const cats = ["all", ...new Set(S.data.presets.map(p => p.category))], box = $("#cats"); box.replaceChildren();
  for (const c of cats) box.append(h("button", { class: "chip" + (S.cat === c ? " on" : ""), onclick: () => { S.cat = c; renderCats(); renderMoves(); } }, c));
}
function renderMoves() {
  const box = $("#moves"); box.replaceChildren();
  for (const p of S.data.presets.filter(p => S.cat === "all" || p.category === S.cat)) {
    const has = !!realFor(S.input.id, p.id);
    box.append(h("button", { class: "move" + (S.preset && S.preset.id === p.id ? " on" : ""), title: has ? "A real render of this still + move exists" : p.description, onclick: () => selectPreset(p.id) }, p.name, h("small", {}, p.category), has ? h("span", { class: "dot" }) : null));
  }
}
function updateButtons() {
  const real = S.preset && realFor(S.input.id, S.preset.id);
  $("#previs").disabled = !S.preset || !S.glOk; $("#real").disabled = !real;
  $("#real").textContent = real ? `Play the real render (${real.model_label})` : "No real render for this still + move";
  estimate();
}
async function selectInput(id) {
  S.input = S.data.inputs.find(i => i.id === id); renderInputs(); renderMoves();
  if (S.glOk) { try { await glLoadInput(S.input); showCanvas(); glDraw(camAt({ keys: [{ t: 0 }] }, 0)); } catch (e) { console.error(e); } }
  setBadge(null); $("#stageTitle").textContent = S.preset ? `${S.preset.name} · ${S.input.title}` : S.input.title; $("#info").replaceChildren(); updateButtons();
}
function selectPreset(id) { S.preset = S.data.presets.find(p => p.id === id); renderMoves(); $("#stageTitle").textContent = `${S.preset.name} · ${S.input.title}`; setBadge(null); $("#info").replaceChildren(h("p", {}, S.preset.description)); updateButtons(); }
function previs() {
  if (!S.preset || !S.glOk) return;
  cancelAnimationFrame(S.raf); showCanvas();
  const spec = S.preset.virtual_camera, dur = 4000, t0 = performance.now();
  setBadge("sim", "Simulated previs: in-browser depth-parallax camera, not model output");
  const tick = now => { const t = Math.min((now - t0) / dur, 1); glDraw(camAt(spec, t)); if (t < 1) S.raf = requestAnimationFrame(tick); };
  S.raf = requestAnimationFrame(tick);
  const real = realFor(S.input.id, S.preset.id), box = $("#info");
  box.replaceChildren(h("p", {}, h("b", {}, "Previsualised. "), "This is a free preview of the move computed in your browser from the still and a ",
    S.input.depth_kind === "hand-made" ? "hand-made depth map" : "heuristic depth guess", " (simplified: stretched at edges, no inpainting). It is not a generated video."),
    real ? h("div", { class: "callout" }, `A real render of this exact still and move exists: ${real.model_label} via ${real.platform}, ${real.credits_used ? fmtCr(real.credits_used) + " credits" : "free tier"}, own rating ${real.rating ?? "n/a"}/10. Press "Play the real render".`) : h("div", { class: "callout" }, "No real render of this still + move is committed. See the gallery below for the real clips, or run it yourself (section 5)."));
}
function playReal(c) {
  cancelAnimationFrame(S.raf); showVideo(c.file); setBadge("real", c.badge || `Real ${c.model_label} output via ${c.platform}`);
  $("#stageTitle").textContent = `${c.preset_name} · ${c.input_title} · real render`; infoReal(c);
  $("#stage")?.scrollIntoView?.({ block: "nearest" });
}
function renderGallery() {
  const box = $("#gallery"); box.replaceChildren();
  const clips = [...S.data.clips].sort((a, b) => (b.rating ?? -1) - (a.rating ?? -1));
  $("#galCount").textContent = `(${clips.length} real clips, best-rated first)`;
  for (const c of clips) {
    const v = h("video", { src: c.file + "#t=0.8", preload: "metadata", muted: "", playsinline: "" });
    box.append(h("button", { class: "g", onclick: () => { S.input = S.data.inputs.find(i => i.id === c.input) || S.input; S.preset = S.data.presets.find(p => p.id === c.preset) || S.preset; renderInputs(); renderMoves(); updateButtons(); playReal(c); window.scrollTo({ top: 0, behavior: "smooth" }); } },
      h("div", { class: "th" }, v, h("span", { class: "b real tg" }, "REAL")),
      h("div", { class: "m" }, h("b", {}, `${c.preset_name} · ${c.input_title}`), h("span", {}, `${c.model_label} · ${c.credits_used ? fmtCr(c.credits_used) + " cr" : "free"} · ${c.rating != null ? c.rating + "/10" : "unrated"}`))));
  }
}
function renderCoverage() {
  const box = $("#coverage"); box.replaceChildren();
  for (const t of S.data.coverage) box.append(h("figure", {}, h("img", { src: t.file, alt: t.label, loading: "lazy" }), h("figcaption", {}, t.label)));
}

/* ------------------------------------------------------------------ optional: run it for real (browser -> api.comfy.org) */
const MODELS = {   // static price table: credits per second (measured 2026-10-16, 211 credits per USD)
  grok480: { id: "xai/grok-imagine-video-1.5-lite", label: "Grok Imagine 1.5 lite 480p", cps: 0.0315 * 211, min: 1 },
  grok720: { id: "xai/grok-imagine-video-1.5-lite", label: "Grok Imagine 1.5 lite 720p", cps: 0.0458 * 211, min: 1 },
  h3: { id: "minimax/minimax-h3", label: "MiniMax H3 768P", cps: 0.1287 * 211, min: 4 },
};
function cost() { const m = MODELS[$("#model").value], d = Math.max(+$("#dur").value, m.min); return { m, d, credits: m.cps * d }; }
function estimate() {
  const { m, d, credits } = cost(), cap = +$("#cap").value || 0, over = credits > cap;
  $("#est").textContent = `${m.label}, ${d} s: about ${credits.toFixed(1)} credits (static price table, /estimate is not used). Cap ${cap}${over ? " : OVER THE CAP, refused" : ""}.`;
  $("#estN").textContent = credits.toFixed(0);
  $("#runBtn").disabled = S.running || !S.preset || !$("#confirm").checked || over || $("#key").value.trim().length < 8;
}
function promptFor(inp, pre) {
  return pre.prompt_template.replace("{scene}", inp.scene || inp.blurb || "").replace("{lens}", "").replace("{mood}", "").replace(/\s+/g, " ").trim();
}
async function stillDataUrl(inp) {
  const img = await loadImg(inp.still), c = document.createElement("canvas"), k = Math.min(1, 1280 / img.width);
  c.width = Math.round(img.width * k); c.height = Math.round(img.height * k); c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
  return c.toDataURL("image/jpeg", 0.88);
}
function buildBody(key, prompt, dataUrl, dur) {
  if (key === "h3") return { content: [{ type: "text", text: prompt }, { type: "image_url", image_url: { url: dataUrl }, role: "first_frame" }], duration: dur, resolution: "768P", ratio: "16:9" };
  return { prompt, duration: dur, aspect_ratio: "16:9", resolution: key === "grok480" ? "480p" : "720p", image: { type: "image_url", url: dataUrl } };
}
function newKey() { const a = new Uint8Array(16); crypto.getRandomValues(a); return "sd-" + Array.from(a, b => b.toString(16).padStart(2, "0")).join(""); }
async function comfyFetch(path, init = {}) {
  const r = await fetch(API + path, { ...init, headers: { "X-API-Key": S.apiKey, "Content-Type": "application/json", ...(init.headers || {}) }, credentials: "omit", cache: "no-store" });
  let body = null; try { body = await r.json(); } catch { /* not json */ }
  if (!r.ok) { const e = new Error(r.status === 402 ? "402: not enough credits. Nothing was run, and nothing will be retried." : `HTTP ${r.status}${body && (body.message || body.error_type || body.detail) ? ": " + (body.message || body.error_type || JSON.stringify(body.detail)) : ""}`); e.status = r.status; throw e; }
  return { body, headers: r.headers };
}
function findUrl(o) {
  if (typeof o === "string") return /^https?:/.test(o) ? o : null;
  if (Array.isArray(o)) { for (const v of o) { const u = findUrl(v); if (u) return u; } return null; }
  if (o && typeof o === "object") { for (const k of ["video_url", "url", "sample"]) if (typeof o[k] === "string" && /^https?:/.test(o[k])) return o[k]; for (const v of Object.values(o)) { const u = findUrl(v); if (u) return u; } }
  return null;
}
async function runReal() {
  const out = $("#runOut"), { m, d, credits } = cost();
  if (S.running || credits > (+$("#cap").value || 0) || !$("#confirm").checked) return;
  S.apiKey = $("#key").value.trim(); S.running = true; $("#runBtn").disabled = true; $("#confirm").checked = false;
  const say = t => out.replaceChildren(h("p", {}, t));
  try {
    say("Preparing the request…");
    const body = buildBody($("#model").value, promptFor(S.input, S.preset), await stillDataUrl(S.input), d);
    say("Submitting once (never retried)…");
    const sub = await comfyFetch(`/v2/models/${m.id}/requests`, { method: "POST", body: JSON.stringify(body), headers: { "Idempotency-Key": newKey() } });
    const id = sub.body && sub.body.request_id; if (!id) throw new Error("The queue answered without a request id; nothing more was sent. Check your Comfy dashboard before trying again.");
    const t0 = Date.now();
    for (;;) {
      await new Promise(r => setTimeout(r, 3000));
      const st = await comfyFetch(`/v2/models/${m.id}/requests/${id}/status`);
      say(`Request ${id}: ${st.body.status}${st.body.queue_position != null ? ", queue position " + st.body.queue_position : ""} (${Math.round((Date.now() - t0) / 1000)} s)`);
      if (st.body.error_type) throw new Error(`The request ended with ${st.body.error_type}. Request id ${id}.`);
      if (st.body.status === "COMPLETED") break;
      if (Date.now() - t0 > 12 * 60 * 1000) throw new Error(`Still not finished after 12 minutes. It may still complete: request id ${id}. Nothing was resubmitted.`);
    }
    const res = await comfyFetch(`/v2/models/${m.id}/requests/${id}`);
    const url = findUrl(res.body); if (!url) throw new Error(`Completed, but no video URL was found in the result. Request id ${id}.`);
    const used = res.headers.get("X-Comfy-Credits-Used");
    cancelAnimationFrame(S.raf); showVideo(url); setBadge("real", `Real ${m.label} output via Comfy Router (your own run, unedited)`);
    $("#stageTitle").textContent = `${S.preset.name} · ${S.input.title} · your render`;
    say(`Done. Request id ${id}${used ? ", credits used " + used : ", estimated " + credits.toFixed(1) + " credits"}. The result link expires in about 12-24 h: save the video now.`);
    out.append(h("p", {}, h("a", { href: url, target: "_blank", rel: "noopener" }, "Open the video file")));
  } catch (e) { say(String(e.message || e)); }
  finally { S.running = false; S.apiKey = ""; $("#key").value = ""; estimate(); }
}

/* ------------------------------------------------------------------ boot */
async function boot() {
  S.data = await (await fetch("data.json")).json();
  S.input = S.data.inputs.find(i => i.id === "forest-cabin") || S.data.inputs[0];
  S.preset = S.data.presets.find(p => p.id === "fpv-drone") || null;
  try { S.glOk = glInit(); } catch (e) { console.error(e); S.glOk = false; }
  if (!S.glOk) { $("#glFail").classList.remove("hidden"); $("#gl").classList.add("hidden"); }
  renderInputs(); renderCats(); renderMoves(); renderGallery(); renderCoverage();
  $("#previs").addEventListener("click", previs);
  $("#real").addEventListener("click", () => { const c = realFor(S.input.id, S.preset.id); if (c) playReal(c); });
  $("#still").addEventListener("click", () => { cancelAnimationFrame(S.raf); showCanvas(); if (S.glOk) glDraw(camAt({ keys: [{ t: 0 }] }, 0)); setBadge(null); });
  for (const id of ["#model", "#dur", "#cap", "#confirm", "#key"]) $(id).addEventListener("input", estimate);
  $("#runBtn").addEventListener("click", runReal);
  await selectInput(S.input.id); if (S.preset) selectPreset(S.preset.id);
  window.__sd = { ready: true };
}
boot().catch(e => { console.error(e); document.body.prepend(h("p", { class: "honest" }, "The page failed to start: " + e.message)); });
