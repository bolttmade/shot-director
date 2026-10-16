# workflows/real: the workflows that produced the real clips

Exported from the Comfy Cloud web UI (Comfy icon → File → **Export**) after each run of the official *LTX-2.3: Image to Video* template. UI/workflow format with a subgraph (not API format). Prompt-only: **no camera LoRA** anywhere in these runs.

| File | Clip | Used in the app? |
|---|---|---|
| `ltx23_i2v_alley_dolly-in.json` | `examples/real/alley__dolly-in.mp4` | yes |
| `ltx23_i2v_alley_crane-up.json` | `examples/real/alley__crane-up.mp4` (partial) | yes, labelled partial |
| `ltx23_i2v_alley_orbit-left_NOT-FEATURED.json` | no clip kept: the render did not orbit | **no**, kept only as a record of the failed attempt |

Edits made before committing (nothing else was changed): the frontend leaves a stale `extra.prompt` (an unrelated API graph), view-position data and a backend fork tag in `extra`; those were removed. The prompt, widget values and graph are as exported. The workflow's `LoadImage` points at a content-hash filename, not at a path.

Checks: valid JSON; no API keys, tokens, e-mail addresses or account ids (scanned); no partner/API nodes (`scripts/check_open_weights.py` descends into the subgraph). Template licence and attribution: see `../ltx23_i2v_official_template.NOTICE.md` (Comfy Org, MIT). The seed stored in each file may be the *next* seed (see `docs/REAL_RUN.md`).
