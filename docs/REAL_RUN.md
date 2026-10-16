# The real run: what was actually done

Short record of how the real clips in `examples/real/` were made, so nobody has to guess. Nothing here is a plan that has not happened, except the last section.

## What was run

- **Where:** Comfy Cloud web UI (free account, 0 credits; the API and Router return 402 on a free account, so the web UI was the only route). Run by hand in a browser, on 2026-10-16.
- **Template:** *LTX-2.3: Image to Video* (template id `video_ltx2_3_i2v`, official Comfy Org template, open weights, core nodes only). A reference copy of the unmodified template is in `workflows/ltx23_i2v_official_template.json` (attribution in the `.NOTICE.md` next to it). The exact exported workflows of the runs are in [`workflows/real/`](../workflows/real/README.md).
- **Input:** `examples/inputs/alley.jpg` (1280x720, no people).
- **Mode:** **prompt-only.** The camera move was requested in the text prompt. No camera LoRA, no depth or virtual camera, no editing of the output.
- **Settings (from the exported workflows):** Width 1280, Height 720, Duration 5 s, Frame Rate 25, Enable Prompt Enhance off, model pickers at template defaults. The delivered files are **1280x704, 4.84 s, 25 fps, H.264 + AAC audio** (ffprobe).
- **Seed:** the exported workflows hold a `noise_seed`, but its control was *randomize*, which advances the value after a run. **UNVERIFIED** whether the stored value is the seed that made each clip, so the recipes say so and nothing claims the clips are reproducible.
- **Template version:** unknown (no version string was recorded; exported with ComfyUI frontend 1.56.3).
- **Cost:** $0, free-tier runs.

## Results (honest)

| Clip | Preset | Prompt idea (exact text in the recipe) | Verdict | In the app? |
|---|---|---|---|---|
| `alley__dolly-in.mp4` | `dolly-in` | slow level forward dolly down the alley | Smooth forward dolly with some background warping. Own rating 5/10. | Yes, green badge |
| `alley__crane-up.mp4` | `crane-up` | slow crane move upward revealing the alley | **Partial:** it rises, but also pushes forward and the scooter flattens. Own rating 5/10. | Yes, green badge **plus** "partial: rises but also pushes forward" |
| orbit-left (not in the repo as a clip) | `orbit-left` | slow orbit left around the scooter | **Did not orbit.** Own rating 4/10. | **No.** Not imported, not shown anywhere. Only its workflow is kept in `workflows/real/` for the record |

One earlier pilot render was discarded and is not used anywhere.

Takeaway, stated plainly: with a prompt alone, LTX-2.3 follows a plain dolly reasonably, a crane only partly, and an orbit not at all. Reliable camera control needs a camera-control LoRA (or a depth-based camera, as in this app's demo path), which need a local GPU and have **not been run** here.

## How they get into the app

```bash
cp alley__dolly-in.mp4 alley__dolly-in.json examples/real/     # .json = notes (prompt, settings, verdict)
.venv/bin/python scripts/import_real.py                        # validate, ffprobe, strip metadata, write recipe.json
```

`import_real.py` strips all container metadata (Comfy Cloud embeds the full workflow JSON in the mp4 as a tag), keeps the streams untouched (no re-encode unless the file is over 6 MB or not H.264), keeps the pre-strip original in the git-ignored `examples/real/_originals/`, and writes `<name>.recipe.json`. The gallery then shows the clip with a **green** badge ("Real LTX-2.3 output (prompt-only, no camera LoRA), unedited"), while simulated fixtures keep the **amber** "Demo fixture: simulated" badge. In Demo mode a real clip replaces the simulated one only for the same input and move with an unchanged request (no custom scene text, no angle).

## Real vs simulated

| | Real | Simulated |
|---|---|---|
| Made by | LTX-2.3 on Comfy Cloud | `app/vcam.py` (depth-parallax virtual camera over a still) |
| Where | `examples/real/` | `examples/outputs/`, `examples/presets/` |
| Badge | green | amber |
| May be called "model output" | yes | **never** |

## A possible 4th run (on hold)

One free run is left and is being held. If it is used, it needs:

1. Same template, same input `alley.jpg`, settings left at defaults (so it is comparable).
2. Decide the goal first. A re-try of `orbit-left` with a different prompt is the only one that would change the story; do not expect a prompt alone to fix it.
3. Before pressing Run: check there is no price, "Upgrade" or credits prompt. If there is, stop. **No credits have been spent so far.** A small Router top-up may be used for a Router smoke test (`scripts/smoke_real.py`) only if the owner explicitly approves it; never add a card, subscribe or spend credits without that explicit approval.
4. Save the video as `alley__<preset-id>.mp4` and write a notes JSON from `examples/real/_notes.example.json` with the **exact** prompt and an honest verdict; export the workflow (Comfy icon → File → **Export**) into `workflows/real/`; then run `scripts/import_real.py`.
5. If the result is bad, keep it out of the gallery (it can stay in `workflows/real/` as a documented failure).
