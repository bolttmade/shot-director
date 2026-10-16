# How Shot Director works

```
Browser (web/: plain HTML/CSS/JS)
   │ REST + Server-Sent Events
FastAPI (app/server.py)  ── JobStore (in-memory, worker threads, event list per job)
   │
   ├─ engines/base.py      Engine interface: health() estimate() run_shot() reframe() coverage()
   ├─ engines/fixtures.py  "demo": replay committed clip, else render the simulated camera (app/vcam.py)
   ├─ engines/workflow.py  "open" / "cloud": ComfyUI API graphs via comfy_sdk.Comfy()
   └─ engines/router.py    "router": partner models via comfy_sdk Router (client.models.*)
presets/*.json            camera moves as data → workflow params AND Router model + body
workflows/*.json          ComfyUI API-format graphs + .meta.json (which node/field is which input)
```

## One preset, four engines

A preset (`presets/dolly-in.json`) holds a prompt template, a negative prompt, an optional official LTX-2 camera-control LoRA, a `virtual_camera` path (Demo engine only), and per-engine bindings:

* `engines.workflow` → which graph in `workflows/` and its parameters (LoRA strength, CFG).
* `engines.router` → the default model id, alternates, and request-body overrides.

The server renders the prompt (`{scene}`, `{lens}`, `{mood}` slots), then hands a `ShotRequest` to the selected engine. The UI never knows which engine it is talking to beyond its id, label, health and cost estimate.

## Engines

**Demo** (`engines/fixtures.py`). If the (sample, move) pair has a committed clip it is replayed with simulated progress; otherwise `app/vcam.py` renders it live. `vcam` is a geometric depth-parallax camera: it forward-splats the still into a z-buffer using its depth map (far to near), fills disocclusions from the farther neighbour, supports right/up/forward/yaw/pitch/roll/zoom, handheld shake, motion blur and rack focus, then pipes frames to ffmpeg. It is **not** generative: it cannot invent unseen content, and large moves tear thin structures. Uploaded images get a cheap heuristic pseudo-depth (top far, bottom near). Everything it emits is flagged `simulated`.

**Workflow** (`engines/workflow.py`). Loads `workflows/<name>.json` with `client.workflows.from_file`, uploads the still with `client.assets.from_file`, sets inputs by the node ids in `<name>.meta.json` (`wf.set_input`), removes the LoRA nodes if the move has none (`wf.remove_node`), calls `client.submit(wf)` once, streams `job.events()`, and downloads `job.get_outputs(node)` immediately. The same code targets a local `comfy-api-proxy` (`open`), Comfy Cloud, or a Comfy API deployment (`cloud`); the base URL decides. Re-framing runs the Qwen angle graph first and feeds that image to the video graph.

**Router** (`engines/router.py`). Builds each provider's native request body, calls `POST /v2/models/{model}/estimate`, enforces the cap, then `client.models.submit` once and polls `handle.iter_events()`. Result URLs expire in 12-24 h, so the file is downloaded as soon as it appears.

## Cost safety (Router and Cloud)

1. Estimate before every run; show it in the UI (exact vs. estimated vs. static table).
2. Hard cap `MAX_CREDITS_PER_RUN` (default 50). Over the cap: refused, nothing submitted.
3. Unknown price: refused unless `ALLOW_UNKNOWN_COST=1`.
4. The server requires `confirm_cost=true` for credit-spending engines, and the UI shows a confirm dialog.
5. `submit` is never retried and never wrapped in a loop (a retry is a second charge). The request/job id is shown immediately so a lost page can be reconciled in the Comfy dashboard.
6. `402 insufficient_credits` becomes a plain message ("nothing was run").
7. `DEMO=1` disables every credit-spending engine at the server, not just in the UI.

## Re-shoot angles

`app/angles.py` snaps the dial to the grid the Qwen *Multiple Angles* LoRA was trained on (8 azimuths x 4 elevations x 3 distances) and emits `<sks> front-right quarter view elevated shot close-up`. The Demo engine instead converts the same angle into a (clamped) virtual-camera pose.

## Sequence

`app/stitch.py` builds one ffmpeg command (`xfade` crossfades or `concat`), normalising size/fps. `build_command` is a pure function and is unit-tested without ffmpeg.

## Recipes

Every output gets a `recipe.json`: engine, model, prompt, negative, seed, source hash, workflow hash, credits, `simulated`. It is how example outputs stay honest about provenance. No API keys or URLs with tokens are ever written.
