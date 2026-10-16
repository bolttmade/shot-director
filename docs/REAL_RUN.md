# The real run: what was actually done

Short record of how the real clips in `examples/real/` were made (two from Comfy Cloud's web UI, two from the Router API), so nobody has to guess. Nothing here is a plan that has not happened, except the last section.

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
| `alley__dolly-in__router-grok-imagine-1-5-lite.mp4` | `dolly-in` | short preset prompt: the camera dollies in smoothly (Router, Grok Imagine 1.5 lite, 5 s @ 480p; see Run 4 below) | Smooth push-in, some invented detail at the end. Own rating 6/10. | Gallery only, own green badge |
| `alley__crane-up__router-grok-imagine-1-5-lite-720p.mp4` | `crane-up` | the preset's own prompt: a sweeping crane shot, the camera rises high and steadily while pushing forward, tilting down (Router, Grok Imagine 1.5 lite, 5 s @ 720p; see Run 5 below) | **Clean crane.** Rises, pushes forward and tilts down; scooter sinks out of the bottom; walls and windows invented. Own rating 7/10. **The hero clip.** | Gallery only, own green badge |
| orbit-left (not in the repo as a clip) | `orbit-left` | slow orbit left around the scooter | **Did not orbit.** Own rating 4/10. | **No.** Not imported, not shown anywhere. Only its workflow is kept in `workflows/real/` for the record |

One earlier pilot render was discarded and is not used anywhere.

Takeaway, stated plainly: with a prompt alone, LTX-2.3 follows a plain dolly reasonably, a crane only partly, and an orbit not at all. Reliable camera control needs a camera-control LoRA (or a depth-based camera, as in this app's demo path), which need a local GPU and have **not been run** here.

## Run 4 (Router): the smoke test (2026-10-16, real, via API)

- **What:** `scripts/smoke_real.py --duration 5 --max-credits 150`, so the whole Router path ran live for the first time: build request, `/estimate`, cap check, ONE `submit`, poll, download, importer.
- **Model:** `xai/grok-imagine-video-1.5-lite` (Grok Imagine 1.5 lite, a partner model: **not open weights**), the cheapest image-to-video model on Router. Not LTX, not a camera LoRA.
- **Request:** `examples/inputs/alley.jpg` as the first frame + the `dolly-in` preset prompt (exact text in the recipe), 5 s, 480p, 16:9. The delivered file is 736x400, 5.04 s, 24 fps, H.264 + AAC.
- **Estimate:** `/estimate` replied that it is not enabled for this workspace, so the app used the static price table: **30.17 credits (about $0.143)**, under the 150-credit cap. This is the number the app recorded as `credits_used`.
- **Real cost:** a read-only balance check afterwards showed 984.27 cents. Against a presumed 1,000 cents before (not read before the run) that is about 33.2 credits. So the charge is **about 30-33 credits** and the exact figure is unverified.
- **Failures:** none. One submit, no retries, no 402. The request id is in the recipe.
- **Result:** `examples/real/alley__dolly-in__router-grok-imagine-1-5-lite.mp4` (+ `.json` notes, `.recipe.json`). A smooth, steady push down the alley; the scooter slides out on the left and the steam drifts; lighting stays consistent. The walls and windows near the end are invented by the model. 480p. Own rating **6/10**, prompt-only, unedited (the importer only strips container metadata).
- **In the app:** the file name carries a third part (`<input>__<preset>__<variant>.mp4`), which makes it a gallery-only clip with its own green badge naming Grok Imagine 1.5 lite and Comfy Router. The Demo engine keeps replaying the LTX-2.3 clip for `alley` + `dolly-in`; it never substitutes the Router clip.
- **What it proves:** the Router adapter works against the live API for image-to-video (submit, queue, download within the link lifetime). It does **not** prove the other engines, the FLUX stills, `/estimate`, or anything about camera LoRAs.

## Run 5 (Router): the hero clip (2026-10-16, real, via API)

- **Why this clip:** the demo needs one real clip that visibly shows a camera move. The free LTX-2.3 crane was only partial (5/10), and the 480p Router dolly was 6/10. A crane-up shows more of a move than a dolly (a rise plus a tilt, and the scooter leaving the frame), and the Router can show it more cleanly. The cheapest Router image-to-video model with a known price, Grok Imagine 1.5 lite, was kept and moved from 480p to 720p (+~15 credits) rather than paying about 136 credits for a 5 s MiniMax H3 clip.
- **What:** `scripts/smoke_real.py --preset crane-up --duration 5 --resolution 720p --max-credits 100`: build request, price, cap check, ONE `submit`, poll, download, importer.
- **Model:** `xai/grok-imagine-video-1.5-lite` (partner model: **not open weights**, **not LTX**, no camera LoRA). Request: `alley.jpg` as the first frame + the `crane-up` preset prompt (exact text in the recipe), 5 s, 720p, 16:9. The delivered file is 1280x720, 5.04 s, 24 fps, H.264 + AAC (ffprobe).
- **Estimate:** `/estimate` replied "not enabled" again, so the static table gave **45.26 credits (about $0.214)**, under the 100-credit cap.
- **Real cost:** the balance was read before (984.27 cents) and after (961.39 cents) the run: 22.88 cents, **about 48.3 credits**. The recipe's `credits_used` field holds this measured figure; the estimate is in the notes. The table under-reports by about 7%.
- **Failures:** none. One submit, no retries, no 402. Request id `01e36596-d4d5-47dd-91bc-7bac11f57373` is in the recipe.
- **How it was judged:** frames were extracted at the start, the middle and the end and compared with the still. The camera rises and pushes forward and tilts down the alley; the scooter sinks out of the bottom of the frame; fire escapes and lit windows come into view; steam and reflections stay consistent; no cuts or flicker. The walls and windows that appear are invented by the model, not in the still, and the scooter changes shape slightly early on. Own rating **7/10**, unedited (the importer only strips container metadata). It is clearly better than the LTX-2.3 prompt-only crane, but it is a different model on a different platform, so it is not a like-for-like comparison.
- **Not run:** a second generation. The first result was clean enough, so no second request was made and no credits were spent on one. No other model was tried.
- **In the app:** a gallery-only variant (`alley__crane-up__router-grok-imagine-1-5-lite-720p.mp4`) with its own green badge. In Demo mode, Crane Up on the alley still keeps replaying the LTX-2.3 clip; the hero is opened from the gallery.

## How they get into the app

```bash
cp alley__dolly-in.mp4 alley__dolly-in.json examples/real/     # .json = notes (prompt, settings, verdict)
.venv/bin/python scripts/import_real.py                        # validate, ffprobe, strip metadata, write recipe.json
```

`import_real.py` strips all container metadata (Comfy Cloud embeds the full workflow JSON in the mp4 as a tag), keeps the streams untouched (no re-encode unless the file is over 6 MB or not H.264), keeps the pre-strip original in the git-ignored `examples/real/_originals/`, and writes `<name>.recipe.json`. The gallery then shows the clip with a **green** badge ("Real LTX-2.3 output (prompt-only, no camera LoRA), unedited"), while simulated fixtures keep the **amber** "Demo fixture: simulated" badge. In Demo mode a real clip replaces the simulated one only for the same input and move with an unchanged request (no custom scene text, no angle).

## Real vs simulated

| | Real | Simulated |
|---|---|---|
| Made by | LTX-2.3 on Comfy Cloud, or Grok Imagine 1.5 lite via the Comfy Router | `app/vcam.py` (depth-parallax virtual camera over a still) |
| Where | `examples/real/` | `examples/outputs/`, `examples/presets/` |
| Badge | green | amber |
| May be called "model output" | yes | **never** |

## A possible further Cloud web run (on hold)

One free run is left and is being held. If it is used, it needs:

1. Same template, same input `alley.jpg`, settings left at defaults (so it is comparable).
2. Decide the goal first. A re-try of `orbit-left` with a different prompt is the only one that would change the story; do not expect a prompt alone to fix it.
3. Before pressing Run: check there is no price, "Upgrade" or credits prompt. If there is, stop. The Cloud web runs cost no credits. The only credits spent so far are the ~30-33 (dolly-in) and ~48 (crane-up) of the two Router runs above; never add a card, subscribe or spend further credits without the owner's approval.
4. Save the video as `alley__<preset-id>.mp4` and write a notes JSON from `examples/real/_notes.example.json` with the **exact** prompt and an honest verdict; export the workflow (Comfy icon → File → **Export**) into `workflows/real/`; then run `scripts/import_real.py`.
5. If the result is bad, keep it out of the gallery (it can stay in `workflows/real/` as a documented failure).
