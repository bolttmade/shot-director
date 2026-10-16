# Demo video plan (target 1:45, hard limit 2:00)

Status: **plan only; nothing in it has been recorded.** Entry rules: 2 minutes maximum, judged on the work (usable UI, example outputs, how it is built), not polish. This plan supersedes the storyboard that used to be in [DEMO_SCRIPT.md](DEMO_SCRIPT.md); that file keeps the **honesty rules**, the "what not to say" list and the social-post draft, and all of them still apply here.

**Recording and assembly tooling: TBD.** This plan does not pick a screen recorder, a voice-over method or an editor. It only says what must be on screen and what must be said. Decide the tooling before capture and note it here.

## What is real and what is not (say only this)

| Item | Status | How it may be described |
|---|---|---|
| `alley__dolly-in.mp4`, `alley__crane-up.mp4` | **Real** LTX-2.3 from Comfy Cloud's web UI (official template, free tier), text prompt only, no camera LoRA, unedited. Dolly 5/10 smooth with warping; crane 5/10 partial | "real", "prompted by text only", "Comfy Cloud free tier"; **not** made through this app's pipeline |
| `alley__crane-up__router-grok-imagine-1-5-lite-720p.mp4` | **Real** Grok Imagine 1.5 lite via the Comfy Router, 720p, 5 s, one request, about 48 credits (balance delta; the table estimated 45.26), unedited, own rating 7/10. **The hero clip.** | "partner model, not open weights", "Comfy Router", "the walls it reveals are invented". Not LTX, not a camera LoRA |
| `alley__dolly-in__router-grok-imagine-1-5-lite.mp4` | **Real**, Router, 480p, about 30-33 credits, 6/10 | Not shown in the cut (gallery only); mention only if asked |
| Everything else (orbit-left on the alley, coverage tiles, other inputs, the timeline's amber clips) | **Simulated** by the Demo engine (depth-parallax virtual camera over a still) | "simulated"; never "AI-generated" or "model output" |

Never claim: camera-LoRA results (none exist), that the open-weights or Cloud engines have run live (contract-tested only), that the FLUX stills on Router were run, or that the Router `/estimate` endpoint works (it answered "not enabled"; the static price table was used). The failed orbit clip is not shown.

## (a) Shot list: 1:45

| # | Time | On-screen action | Clip shown | Voice-over | Honesty check on screen |
|---|---|---|---|---|---|
| 1 | 0:00 to 0:08 | Title card, then the app on the **Rainy Alley** still. The amber **DEMO · no keys** pill (top right) must be visible. | none (still frame) | "This is Shot Director: a shot-planning workflow that starts from one still frame. Open source, built on the Comfy platform." (20 words) | Amber DEMO · no keys pill |
| 2 | 0:08 to 0:30 | README architecture diagram (preset → three backends, cost-guard box). Cut to the app's **Engine** card: Demo engine selected, the **Free** cost line. | none | "One preset is one camera move, written as plain JSON. It maps to three backends: a ComfyUI graph through the Comfy SDK, a partner-model request through the Comfy Router, and a virtual camera for this offline demo. Every paid call gets a price estimate, a hard cap and one confirmation, and is never retried." (54 words) | Say "maps to", never "has run on" |
| 3 | 0:30 to 0:42 | Pick **Dolly In**, **Generate shot**. The clip plays with the **green** badge. Open **Download recipe.json** (or show it already open in an editor) for 2 s. | REAL: `alley__dolly-in.mp4` (LTX-2.3, Comfy Cloud web UI) | "The green badge means real model output. This dolly is LTX-2.3 on Comfy Cloud's free tier, prompted by text only, no camera LoRA, unedited. Smooth, with some background warping." (29 words) | Green badge on screen; "text only" said aloud |
| 4 | 0:42 to 0:52 | Pick **Crane Up**, **Generate shot**. Green badge **plus** the "partial: rises but also pushes forward" label. | REAL: `alley__crane-up.mp4` (LTX-2.3, partial) | "The crane from the same setup is only partly right: it rises, but it also pushes forward. A prompt alone is not reliable camera control." (25 words) | The "partial" label stays on screen |
| 5 | 0:52 to 1:11 | Scroll to the **gallery**, click the real clip **Crane Up · Rainy Alley · Router**, whose badge names Grok Imagine (file `alley__crane-up__router-grok-imagine-1-5-lite-720p.mp4`). Let it play once in full (5 s), then open its recipe.json (model id, request id, credits). | REAL (hero): Router, Grok Imagine 1.5 lite, 720p, rated 7/10 | "This is the best real clip I have: a crane-up from Grok Imagine 1.5 lite, run through the Comfy Router at 720p. It is a partner model, not open weights. The camera rises, pushes in and tilts down; the walls it reveals are invented. About forty-eight credits." (47 words) | Badge names the model, Router, "not open weights", "unedited" |
| 6 | 1:11 to 1:26 | Pick **Orbit Left** on the alley: amber clip plays. Switch to **Split** (A/B wipe). Click **Get coverage**: six tiles. | SIMULATED: Demo engine's virtual camera and coverage stills | "For moves I could not run for real, the app uses its own simulated camera, and the amber badge says so. Compare still and clip with the A/B player, and get six coverage angles from one frame." (37 words) | Amber badge on screen; word "simulated" said aloud |
| 7 | 1:26 to 1:34 | **+ Add to timeline** for 3 clips (green crane, green dolly, amber orbit), drag to reorder, **Export sequence**, play. Point at the real/simulated tag per timeline clip. | mixed: 2 real + 1 simulated (the cut is flagged simulated) | "Add shots to the timeline, reorder them, and export one cut. Any simulated clip flags the whole cut as simulated." (20 words) | Per-clip tag visible; cut flagged simulated |
| 8 | 1:34 to 1:41 | Engine card with the engine list, then the footer repo/licence link (**Open source · MIT**). | none | "The Router has run live twice. The open-weights and Cloud engines are contract-tested, not yet run live." (17 words) | No claim that open-weights or Cloud ran live |
| 9 | 1:41 to 1:45 | End card: repo URL, `#OpenSourceHiggsfield`. Hold at most 4 s. | none | "Shot Director. Built for Open Source Higgsfield." (7 words) | Repo link github.com/bolttmade/shot-director |

Timings follow the word counts at about 146 words per minute (an unhurried read); the cut ends at 1:45, leaving 15 s of margin under the 2:00 limit. If the take runs long, cut beat 7 first, then the last sentence of beat 2.

## (b) Capture plan

**Setup (once).** From the repo root: `DEMO=1 ./run.sh` (creates `.venv` on first run), then open `http://127.0.0.1:8000` in a clean browser profile. Do **not** create a `.env`, and do not export `COMFY_API_KEY` in the shell used for recording: Demo mode needs no keys and the top-right pill says "DEMO · no keys". The four real clips in `examples/real/` appear in the gallery automatically; the committed simulated clips and coverage are used for the rest. Leave **Length**, **Size** and the scene box at their defaults and do not drop a custom image or angle: any change makes the app produce a simulated clip instead of replaying the real one.

**Resolution.** The UI and the committed screenshots were checked at 1280x720. A 1920x1080 recording is **untested**: do a 10 s test capture first and check that the badge text is readable at the final export size. If it is not, record at 1280x720.

**Order of capture (one take per beat is fine; assemble in time order).**

1. Beats 2 and 8: README diagram on GitHub (or a local markdown preview) and the Engine card. Capture first because they need no state.
2. Beat 1 and 3: reload the app, **Rainy Alley** (source card) selected. Camera move tab → category list → **Dolly In** → **Generate shot** → wait for the green badge → click **Download recipe.json** only if the file opens on screen without showing a folder path (otherwise open the recipe in an editor).
3. Beat 4: **Crane Up** → **Generate shot**. Keep the "partial" text visible for the whole beat.
4. Beat 5 (hero): scroll the right-hand **gallery** to the green-tagged clip named *Crane Up · Rainy Alley* the one labelled *Crane Up · Rainy Alley · Router* (there are two Router clips, a dolly and a crane, and a separate LTX crane labelled without "Router"; pick the **crane** with "Router"). Click it, **Video** view, let it play once; then open `alley__crane-up__router-grok-imagine-1-5-lite-720p.recipe.json`.
5. Beat 6: **Orbit Left** → **Generate shot** (amber clip) → **Split** → **Get coverage**.
6. Beat 7: **+ Add to timeline** for Crane Up (real), Dolly In (real) and Orbit Left (simulated), drag to reorder, **Export sequence**, play the result.

Re-record a beat rather than fixing it later, and never edit the clips themselves (the real clips must be shown unedited; speed changes, crops and filters on them are not allowed).

## (c) Voice-over script (256 words; at about 146 words per minute this is about 1:45)

**1 (0:00 to 0:08)** This is Shot Director: a shot-planning workflow that starts from one still frame. Open source, built on the Comfy platform.

**2 (0:08 to 0:30)** One preset is one camera move, written as plain JSON. It maps to three backends: a ComfyUI graph through the Comfy SDK, a partner-model request through the Comfy Router, and a virtual camera for this offline demo. Every paid call gets a price estimate, a hard cap and one confirmation, and is never retried.

**3 (0:30 to 0:42)** The green badge means real model output. This dolly is LTX-2.3 on Comfy Cloud's free tier, prompted by text only, no camera LoRA, unedited. Smooth, with some background warping.

**4 (0:42 to 0:52)** The crane from the same setup is only partly right: it rises, but it also pushes forward. A prompt alone is not reliable camera control.

**5 (0:52 to 1:11)** This is the best real clip I have: a crane-up from Grok Imagine 1.5 lite, run through the Comfy Router at 720p. It is a partner model, not open weights. The camera rises, pushes in and tilts down; the walls it reveals are invented. About forty-eight credits.

**6 (1:11 to 1:26)** For moves I could not run for real, the app uses its own simulated camera, and the amber badge says so. Compare still and clip with the A/B player, and get six coverage angles from one frame.

**7 (1:26 to 1:34)** Add shots to the timeline, reorder them, and export one cut. Any simulated clip flags the whole cut as simulated.

**8 (1:34 to 1:41)** The Router has run live twice. The open-weights and Cloud engines are contract-tested, not yet run live.

**9 (1:41 to 1:45)** Shot Director. Built for Open Source Higgsfield.

Word count per beat is in the table above; the total is **256** words. Read it aloud once with a timer before recording; trim from beat 7 or the last sentence of beat 2 if it exceeds 1:45. Say "about forty-eight credits" only if the recipe on screen agrees (the recipe's `credits_used` is 48.27).

## (d) Pre-flight checklist

- [ ] Fresh browser profile (or guest window): no extensions, no bookmarks bar, no other tabs, no autofill, no signed-in avatar; notifications and "do not disturb" on.
- [ ] No real name, email address, handle or avatar anywhere on screen: browser profile, OS user name and hostname (terminal prompt, window titles, file-manager paths), GitHub account menu. Only the anonymous **bolt** / **bolttmade** identity and `bolttmade@users.noreply.github.com` may appear.
- [ ] No API key visible: no `.env` open, no `env`/`printenv` output, no shell history, no Comfy dashboard or API-keys page, no Comfy account page. The `COMFY_API_KEY` variable is not set in the recording shell.
- [ ] Recipes opened on screen contain no local paths or personal data (checked with `rg` before recording); the Router recipe's `credits_note` shows the account balance in USD cents; skip scrolling to it or accept that it is visible.
- [ ] SFW, no people, no logos or unlicensed IP: the alley still and the simulated inputs are generated art with no people.
- [ ] Badges readable at export size: amber **Demo fixture: simulated camera move, not model output**, green **Real ... output** badge, and the "partial" label.
- [ ] The app is in Demo mode (the pill says so) and the repo URL on the end card is github.com/bolttmade/shot-director.
- [ ] Nothing in the video says or implies: camera-LoRA works, open-weights or Cloud engines were run live, amber clips are model output, or that the app itself generated the LTX clips.
- [ ] Total length at most 2:00 (target 1:45); the video is **not** posted or submitted by the builder: the owner submits under their own name.
