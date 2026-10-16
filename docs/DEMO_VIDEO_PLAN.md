# Demo video: plan and as-built (96 s, limit 1:45; entry limit 2:00)

Status: **a draft was built** (free, local, no credits spent) with `scripts/make_demo_video.sh`. Entry rules: 2 minutes maximum, judged on the work (usable UI, example outputs, how it is built), not polish. The **honesty rules**, the "what not to say" list and the social-post draft live in [DEMO_SCRIPT.md](DEMO_SCRIPT.md) and apply here. The video is not posted or submitted by the builder: the owner submits it under their own name.

**The story:** *free previs, then one real render.* Open on real outputs, show the app flow, then the platform/build beat, end on the two links.

## Deviations from the first plan (1:50, README-first)

* The cut now **opens on the real hero clip** (within 5 s) instead of a title card, then goes into the app; the build/platform beat and credit log are cards, not screen captures of `docs/COSTS.md`.
* Narration is **offline TTS (piper, voice `en_US-lessac-medium`)** plus burned-in ASS captions; there is also a silent `-captions-only` variant. No music. Piper and the voice are downloaded by the script and are not in git. Check the voice's licence terms before publishing the audio; use the captions-only file if in doubt.
* The UI beats are **real headless-Chrome captures** (CDP screencast; screenshot polling for the WebGL Space page), with dead waiting time (previs generation, coverage, reel build) cut out. 1280x640 captures sit in a 1280x720 frame with a caption bar.
* The old beat 2 (architecture diagram) and the old 1:50 timings are replaced by the as-built timings below.

## What is real and what is not (say only this)

| Item | Status | How it may be described |
|---|---|---|
| `forest-cabin__fpv-drone__router-minimax-h3.mp4` | **Real** MiniMax H3 (`minimax/minimax-h3`, 768P, 5 s) via the Comfy Router, one request, 135.78 credits (balance delta, equal to the estimate), unedited, own rating 7/10 (soft and blurry mid-swoop). **The hero clip, chosen for its dramatic motion.** Input still made by FLUX 3 Image | "partner model, not open weights, not LTX, prompt-only"; "the forest at the end is invented" |
| Other Router clips (11) | **Real**, one request each: H3 x4 (7-8/10), Grok lite x6 (6-7/10, about 33-48 credits), FLUX 3 Video x1 (226.3 credits, 4/10) | name the model; show ratings honestly; FLUX 3 Video barely moves; the Grok orbit is "a gentle arc or lateral drift, closer to an orbit than the LTX attempt" (6/10) |
| `alley__dolly-in.mp4`, `alley__crane-up.mp4` | **Real** LTX-2.3 from Comfy Cloud's web UI, free tier, prompt-only, 5/10 each | "not made through this app's pipeline" |
| `examples/real/coverage/alley/` | **Real** FLUX 3 Image edits, 6 requests, 86.9 credits, 7/10; the close-up has a garbled unreadable emblem on the scooter | "real FLUX 3 Image edits" |
| The previs (every amber clip and every non-alley coverage tile) | **Simulated** by the Demo engine or the Space's WebGL shader (depth-parallax virtual camera over a still) | "simulated", "a preview of the move"; never "AI-generated" or "model output" |

Never claim: camera-LoRA results (none exist), that the open-weights or Cloud engines ran live, that `/estimate` works (it answered "not enabled"; the static price table was used), or that Seedance/LTX-via-Router ran. The failed LTX orbit is not shown.

## As-built shot list

| # | Time | On screen | Voice-over (also the captions) | Honesty check |
|---|---|---|---|---|
| 1 | 0:00.0 to 0:05.2 | REAL footage, full frame: `forest-cabin__fpv-drone__router-minimax-h3.mp4` (MiniMax H3 via the Comfy Router, unedited, cropped from 1280x732 to 1280x720 only). Green burned-in label. | One still. One real render. This is Shot Director. (9 words) | Label names model, Router, credits, "unedited" |
| 2 | 0:05.2 to 0:14.6 | Card: still -> free previs (amber, simulated) -> one real render (green). | Shot Director is a camera-move studio for Comfy. Preview any move for free with a simulated camera, then spend credits once, on the real render of the move you picked. (30 words) | Green = real, amber = simulated |
| 3 | 0:14.6 to 0:29.2 | UI capture, local Demo app: Forest Cabin -> FPV Drone -> Previs this shot (free) -> the amber previs and callout -> Play the real render (green badge). | Pick a still and a move. The free preview is simulated, and the amber badge says so. Happy with it? Play the real render: green badge, MiniMax H3 through the Comfy Router, a partner model, unedited. A hundred and thirty-six credits. (41 words) | Amber badge, then green badge, both on screen |
| 4 | 0:29.2 to 0:45.1 | UI capture: Example outputs gallery; clicks FPV Drone, Orbit Left (Grok lite, 6/10) and the FLUX 3 Video arc (4/10) real clips. | The gallery holds fourteen real clips, with their credits and my honest ratings. Grok lite costs forty-eight credits and is close behind; its orbit is a gentle arc, six out of ten. FLUX 3 Video cost two hundred and twenty-six, and barely moves: four out of ten. (47 words) | Each clip keeps its own green badge, credits and rating |
| 5 | 0:45.1 to 0:52.4 | UI capture: Rainy Alley, Get coverage (real FLUX 3 Image board, green), then the A/B split wipe. | Coverage: six real FLUX 3 Image angles of one frame. The A/B player compares the still with the clip. (19 words) | Green board badge; the stage clip keeps its own badge |
| 6 | 0:52.4 to 1:01.7 | UI capture: + All real clips, Make my reel; the 16:9 and 9:16 outputs play. | Make my reel cuts the real clips into sixteen by nine and nine by sixteen, labelled with the model. No credits spent. (22 words) | Real clips only, labelled with the model, no credits |
| 7 | 1:01.7 to 1:09.3 | UI capture of the live static Space (https://bolttmade-shot-director.static.hf.space/): in-browser WebGL previs (amber), then Play the real render (green). | It also runs free in your browser, as a static Hugging Face Space. (13 words) | Amber and green badges |
| 8 | 1:09.3 to 1:18.2 | Card: Comfy Router API, SDK 0.5.0, Cloud, cost guard, tests and CI (numbers from the repo). | Under the hood: the Comfy Router API and SDK, one capped, confirmed submit per request, a hundred tests, and green CI. (21 words) | No claim beyond what ran |
| 9 | 1:18.2 to 1:29.4 | Card: the credit log (about 1,310 credits, every request id in docs/COSTS.md). | Every credit is logged with its request id: about thirteen hundred in total. The open-weights and Cloud engines are contract-tested only, and no camera LoRA result exists. (27 words) | "contract-tested only" for open-weights and Cloud; no camera LoRA |
| 10 | 1:29.4 to 1:36.3 | End card: github.com/bolttmade/shot-director and huggingface.co/spaces/BoltTmade/shot-director. | Shot Director. Open source, on GitHub and Hugging Face. (9 words) | Only the bolt / bolttmade / BoltTmade identity |

Total 96.3 s, 238 narrated words. Each beat lasts as long as its narration (plus 0.45 s), a real clip is never shortened, and a short freeze fills a capture that ends early.

## Voice-over script

**1 (0:00.0)** One still. One real render. This is Shot Director.
**2 (0:05.2)** Shot Director is a camera-move studio for Comfy. Preview any move for free with a simulated camera, then spend credits once, on the real render of the move you picked.
**3 (0:14.6)** Pick a still and a move. The free preview is simulated, and the amber badge says so. Happy with it? Play the real render: green badge, MiniMax H3 through the Comfy Router, a partner model, unedited. A hundred and thirty-six credits.
**4 (0:29.2)** The gallery holds fourteen real clips, with their credits and my honest ratings. Grok lite costs forty-eight credits and is close behind; its orbit is a gentle arc, six out of ten. FLUX 3 Video cost two hundred and twenty-six, and barely moves: four out of ten.
**5 (0:45.1)** Coverage: six real FLUX 3 Image angles of one frame. The A/B player compares the still with the clip.
**6 (0:52.4)** Make my reel cuts the real clips into sixteen by nine and nine by sixteen, labelled with the model. No credits spent.
**7 (1:01.7)** It also runs free in your browser, as a static Hugging Face Space.
**8 (1:09.3)** Under the hood: the Comfy Router API and SDK, one capped, confirmed submit per request, a hundred tests, and green CI.
**9 (1:18.2)** Every credit is logged with its request id: about thirteen hundred in total. The open-weights and Cloud engines are contract-tested only, and no camera LoRA result exists.
**10 (1:29.4)** Shot Director. Open source, on GitHub and Hugging Face.

Say the credit numbers only if they agree with the repo (H3 135.78, Grok lite 48.28 at 720p, FLUX 3 Video 226.3, coverage 86.9; total about 1,310).

## How it is built (reproducible)

`scripts/make_demo_video.sh` (needs python3, ffmpeg, Chrome/Chromium, network once for the piper voice and the live Space beat) runs `scripts/demo_video.py`: `cards` (Pillow cards from repo facts), `tts` (piper, length scale 0.95), `capture` (local Demo app on a free port with a temp output dir; the live Space), `assemble` (ffmpeg: segments, ASS captions, AAC, H.264 crf 21, metadata stripped). `DEMO_OUT` picks the output folder (default `./demo`, git-ignored; the mp4 is not committed). Stages can be re-run alone, e.g. `scripts/make_demo_video.sh capture --only space`. It spends no Comfy credits and uploads nothing.

## Pre-flight checklist (before anyone posts it)

- [ ] Watch it once with sound: judge the piper voice (pronunciation of "FLUX", "Grok", "H3"); if poor, use the captions-only file.
- [ ] No real name, email, handle or avatar anywhere on screen. Only the anonymous **bolt** / **bolttmade** / **BoltTmade** identity.
- [ ] No API key, `.env`, shell or account page visible.
- [ ] SFW, no people, no logos/IP. The garbled emblem in the alley close-up coverage still is not zoomed on.
- [ ] Badges readable: amber simulated, green real.
- [ ] Nothing says or implies: camera-LoRA works, open-weights or Cloud engines ran live, amber clips are model output.
- [ ] Total length under 2:00; the owner submits it, not the builder.
