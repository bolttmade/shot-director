# Demo video: plan and as-built (v2, 96 s, limit 1:45; entry limit 2:00)

Status: **v2 built** (free, local, no credits spent) with `scripts/make_demo_video.sh`. Entry rules: 2 minutes maximum, judged on the work (usable UI, example outputs, how it is built), not polish. The **honesty rules**, the "what not to say" list and the social-post draft live in [DEMO_SCRIPT.md](DEMO_SCRIPT.md) and apply here. The video is not posted or submitted by the builder: the owner submits it under their own name.

**The story:** *free previs, then one real render.* Open on real outputs, show the app flow, then the platform/build beat, end on the two links.

## Output files

| File | What it is |
|---|---|
| `demo/shot-director-demo.mp4` | **PRIMARY: burned-in captions only** (silent AAC track, no synthetic voice). |
| `demo/shot-director-demo-tts.mp4` | Alt: the same picture with the piper voice-over. Use only after the voice licence question below is settled. |

Both are 1280x720, H.264 + AAC, about 96 s and 11-12 MB, kept out of git (`/demo/` is ignored). `PRIMARY=tts scripts/make_demo_video.sh` flips which one gets the main name.

## Voice licence finding (why the captions-only cut is primary)

Voice: `en_US-lessac-medium` from `rhasspy/piper-voices` on Hugging Face (checked 2026-10-16).

* The repo-level `README.md` header says `license: mit`.
* The voice's own `MODEL_CARD` says: Dataset URL `https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/`, "License: https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html", "Trained from scratch."
* That licence page is the **Blizzard 2013 "Research Licence Agreement"** (Voice Factory International / Lessac Technologies). It grants a "non-exclusive and non-transferable licence, without the right to sub-licence, to use the Materials exclusively for Research Purposes only", and defines Research Purposes as excluding "any commercial purpose, including the development, marketing, commercialisation, sale or licencing of voice synthesis or speech recognition products or services". The licence is "granted only to the person or organisation named" in the licence form.

So the repo's MIT label does not clearly cover the voice: the training data is research-only, and whether audio synthesised by a model trained on it may be used in a public contest video is **unclear, not clearly permissive**. Decision: the captions-only file is primary and the narrated file is an alternative. A voice whose data is clearly free would settle it: `en_US-ljspeech-medium` has "License: public domain" for its dataset (LJ Speech) in its MODEL_CARD; it was **not** built or listened to here (`PIPER_VOICE=... scripts/make_demo_video.sh tts` and `assemble` would try it).

## Changes in v2 (from the v1 review)

1. **Popups describe the clip on screen.** Every real clip now shows a dark popup headed `REAL · <model> · <move> on <still> · own rating N/10 · <credits> credits`, built from that clip's own gallery data (notes JSON), in the local app and in the Space. The capture script asserts the popup text for each clip it selects (it would fail otherwise), and `tests/test_popup_ui.py` clicks every gallery clip in both UIs and checks the popup (browser test, skipped without Playwright/Chrome). In v1 the popup text was the clip's one-line quality note only; the v1 recording itself already showed the matching note per clip, so the "copy of the forest-cabin text" could not be reproduced from the file, but the popups were hard to read and did not state model, move, rating or credits, which is now fixed.
2. **Legibility.** UI beats are recorded as 1.4x punch-ins (a 914x457 CSS window panned to what the beat is about, captured at device scale 1.4, so text is rendered natively at 1280x640 instead of upscaled).
3. **Popup boxes.** Larger font, dark background, light text, coloured edge (amber SIMULATED, green REAL); the hero label and the app and Space popups share the style.
4. **Slides.** The platform slide has four big facts; the credit log shows one row per model with the real per-clip figure ("Grok Imagine lite · 6 clips: ~33 to 48 credits each, depending on resolution").
5. **Space fix kept from v1:** images load with `crossOrigin` so the WebGL previs works behind the Hugging Face CDN redirect.

## Deviations from the first plan (1:50, README-first)

* The cut **opens on the real hero clip** (within 5 s) instead of a title card; the build/platform beat and the credit log are cards.
* Narration is **offline TTS (piper)** plus burned-in ASS captions in the alt file; no music.
* The UI beats are **real headless-Chrome captures**; dead waiting time (previs generation, coverage, reel build) is cut out.

## What is real and what is not (say only this)

| Item | Status | How it may be described |
|---|---|---|
| `forest-cabin__fpv-drone__router-minimax-h3.mp4` | **Real** MiniMax H3 (`minimax/minimax-h3`, 768P, 5 s) via the Comfy Router, one request, 135.78 credits (balance delta, equal to the estimate), unedited, own rating 7/10 (soft and blurry mid-swoop). **The hero clip, chosen for its dramatic motion.** Input still made by FLUX 3 Image | "partner model, not open weights, not LTX, prompt-only"; "the forest at the end is invented" |
| Other Router clips (11) | **Real**, one request each: H3 x4 (7-8/10), Grok lite x6 (6-7/10, about 33-48 credits), FLUX 3 Video x1 (226.3 credits, 4/10) | name the model; show ratings honestly; FLUX 3 Video barely moves; the Grok orbit is "a gentle arc or lateral drift, closer to an orbit than the LTX attempt" (6/10) |
| `alley__dolly-in.mp4`, `alley__crane-up.mp4` | **Real** LTX-2.3 from Comfy Cloud's web UI, free tier, prompt-only | "not made through this app's pipeline" |
| `examples/real/coverage/alley/` | **Real** FLUX 3 Image edits, 6 requests, 86.9 credits, 7/10; the close-up has a garbled unreadable emblem on the scooter | "real FLUX 3 Image edits" |
| The previs (every amber clip and every non-alley coverage tile) | **Simulated** by the Demo engine or the Space's WebGL shader (depth-parallax virtual camera over a still) | "simulated", "a preview of the move"; never "AI-generated" or "model output" |

Never claim: camera-LoRA results (none exist), that the open-weights or Cloud engines ran live, that `/estimate` works (it answered "not enabled"; the static price table was used), or that Seedance/LTX-via-Router ran. The failed LTX orbit is not shown.

## As-built shot list

| # | Time | On screen | Voice-over (also the captions) | Honesty check |
|---|---|---|---|---|
| 1 | 0:00.0 to 0:05.2 | REAL footage, full frame: `forest-cabin__fpv-drone__router-minimax-h3.mp4` (MiniMax H3 via the Comfy Router, unedited, cropped from 1280x732 to 1280x720 only). Dark label with the clip's facts (model, move, own rating 7/10, 135.78 credits). | One still. One real render. This is Shot Director. (9 words) | Label names model, move, rating, credits, "unedited" |
| 2 | 0:05.2 to 0:15.0 | Card: still -> free previs (amber, simulated) -> one real render (green). | Shot Director is a camera-move studio for Comfy. Preview any move for free with a simulated camera, then spend credits once, on the real render of the move you picked. (30 words) | Green = real, amber = simulated |
| 3 | 0:15.0 to 0:30.3 | UI capture, local Demo app, punched in 1.4x: Forest Cabin -> FPV Drone -> Previs this shot (free) -> amber SIMULATED popup and callout -> Play the real render (green REAL popup with model, move, rating 7/10, 136 credits). | Pick a still and a move. The free preview is simulated, and the amber badge says so. Happy with it? Play the real render: green badge, MiniMax H3 through the Comfy Router, a partner model, unedited. A hundred and thirty-six credits. (41 words) | SIMULATED popup, then REAL popup, both on screen |
| 4 | 0:30.3 to 0:46.0 | UI capture (1.4x): Example outputs gallery; clicks FPV Drone (H3, 7/10), Orbit Left (Grok lite, 6/10) and the FLUX 3 Video arc (4/10). The popup is built from the selected clip's own data (checked in the recording script and by `tests/test_popup_ui.py`). | The gallery holds fourteen real clips, with their credits and my honest ratings. Grok lite costs forty-eight credits and is close behind; its orbit is a gentle arc, six out of ten. FLUX 3 Video cost two hundred and twenty-six, and barely moves: four out of ten. (47 words) | Each popup shows that clip's model, move, rating, credits |
| 5 | 0:46.0 to 0:53.1 | UI capture (1.4x): Rainy Alley, Get coverage (real FLUX 3 Image board, green), then the A/B split wipe. | Coverage: six real FLUX 3 Image angles of one frame. The A/B player compares the still with the clip. (19 words) | Green board popup; the stage clip keeps its own popup |
| 6 | 0:53.1 to 1:01.8 | UI capture (1.4x): + All real clips, Make my reel; the 16:9 and 9:16 outputs play. | Make my reel cuts the real clips into sixteen by nine and nine by sixteen, labelled with the model. No credits spent. (22 words) | Real clips only, labelled with the model, no credits |
| 7 | 1:01.8 to 1:09.2 | UI capture (1.4x) of the live static Space (https://bolttmade-shot-director.static.hf.space/): in-browser WebGL previs (SIMULATED), then Play the real render (REAL popup with the clip's facts). | It also runs free in your browser, as a static Hugging Face Space. (13 words) | SIMULATED and REAL popups |
| 8 | 1:09.2 to 1:18.2 | Card: four facts: 14 real clips, 4 Router models, 100+ tests and CI green, cap + confirm. | Under the hood: the Comfy Router API and SDK, one capped, confirmed submit per request, a hundred tests, and green CI. (21 words) | No claim beyond what ran |
| 9 | 1:18.2 to 1:29.1 | Card: credits spent by model (about 1,310 in total, Grok lite clips ~33 to 48 credits each depending on resolution), every request id in docs/COSTS.md. | Every credit is logged with its request id: about thirteen hundred in total. The open-weights and Cloud engines are contract-tested only, and no camera LoRA result exists. (27 words) | Numbers match docs/COSTS.md |
| 10 | 1:29.1 to 1:35.9 | End card: github.com/bolttmade/shot-director and huggingface.co/spaces/BoltTmade/shot-director. | Shot Director. Open source, on GitHub and Hugging Face. (9 words) | Only the bolt / bolttmade / BoltTmade identity |

Total 95.9 s, 238 narrated words. Each beat lasts as long as its narration (plus 0.45 s), a real clip is never shortened, and a short freeze fills a capture that ends early.

## Voice-over script

**1 (0:00.0)** One still. One real render. This is Shot Director.
**2 (0:05.2)** Shot Director is a camera-move studio for Comfy. Preview any move for free with a simulated camera, then spend credits once, on the real render of the move you picked.
**3 (0:15.0)** Pick a still and a move. The free preview is simulated, and the amber badge says so. Happy with it? Play the real render: green badge, MiniMax H3 through the Comfy Router, a partner model, unedited. A hundred and thirty-six credits.
**4 (0:30.3)** The gallery holds fourteen real clips, with their credits and my honest ratings. Grok lite costs forty-eight credits and is close behind; its orbit is a gentle arc, six out of ten. FLUX 3 Video cost two hundred and twenty-six, and barely moves: four out of ten.
**5 (0:46.0)** Coverage: six real FLUX 3 Image angles of one frame. The A/B player compares the still with the clip.
**6 (0:53.1)** Make my reel cuts the real clips into sixteen by nine and nine by sixteen, labelled with the model. No credits spent.
**7 (1:01.8)** It also runs free in your browser, as a static Hugging Face Space.
**8 (1:09.2)** Under the hood: the Comfy Router API and SDK, one capped, confirmed submit per request, a hundred tests, and green CI.
**9 (1:18.2)** Every credit is logged with its request id: about thirteen hundred in total. The open-weights and Cloud engines are contract-tested only, and no camera LoRA result exists.
**10 (1:29.1)** Shot Director. Open source, on GitHub and Hugging Face.

Say the credit numbers only if they agree with the repo (H3 135.78, Grok lite 48.28 at 720p, FLUX 3 Video 226.3, coverage 86.9; total about 1,310).

## How it is built (reproducible)

`scripts/make_demo_video.sh` (needs python3, ffmpeg, Chrome/Chromium, network once for the piper voice and the live Space beat) runs `scripts/demo_video.py`: `cards` (Pillow cards from repo facts), `tts` (piper, length scale 0.95), `capture` (local Demo app on a free port with a temp output dir; the live Space; 1.4x punch-in screenshots), `assemble` (ffmpeg: segments, ASS captions, AAC, H.264 crf 21, metadata stripped). `DEMO_OUT` picks the output folder (default `./demo`, git-ignored). Stages can be re-run alone, e.g. `scripts/make_demo_video.sh capture --only space`. It spends no Comfy credits and uploads nothing.

## Pre-flight checklist (before anyone posts it)

- [ ] Decide on the voice: use the primary captions-only file, or settle the piper voice licence (see above) before using the `-tts` file.
- [ ] No real name, email, handle or avatar anywhere on screen. Only the anonymous **bolt** / **bolttmade** / **BoltTmade** identity.
- [ ] No API key, `.env`, shell or account page visible.
- [ ] SFW, no people, no logos/IP. The garbled emblem in the alley close-up coverage still is not zoomed on.
- [ ] Popups readable: amber SIMULATED, green REAL, each naming the clip's own model, move, rating and credits.
- [ ] Nothing says or implies: camera-LoRA works, open-weights or Cloud engines ran live, or amber clips are model output.
- [ ] Total length under 2:00; the owner submits it, not the builder.
