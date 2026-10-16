# Demo video plan (target 1:50, hard limit 2:00)

Status: **plan only; nothing in it has been recorded.** Entry rules: 2 minutes maximum, judged on the work (usable UI, example outputs, how it is built), not polish. The **honesty rules**, the "what not to say" list and the social-post draft live in [DEMO_SCRIPT.md](DEMO_SCRIPT.md) and apply here.

**Recording and assembly tooling: TBD.** This plan does not pick a screen recorder, a voice-over method or an editor. Decide before capture and note it here.

**The story:** *free previs, then one real render.* Preview a camera move for free with the simulated camera, render the move you picked once for real, compare models, cover the scene, cut a reel.

## What is real and what is not (say only this)

| Item | Status | How it may be described |
|---|---|---|
| `forest-cabin__fpv-drone__router-minimax-h3.mp4` | **Real** MiniMax H3 (`minimax/minimax-h3`, 768P, 5 s) via the Comfy Router, one request, 135.78 credits (balance delta, equal to the estimate), unedited, own rating 8/10. **The hero clip.** Input still made by FLUX 3 Image | "partner model, not open weights, not LTX, prompt-only"; "the forest at the end is invented" |
| Other Router clips (11) | **Real**, one request each: H3 x4 (7-8/10), Grok lite x6 (6-7/10, 30-48 credits), FLUX 3 Video x1 (226.3 credits, 4/10) | name the model; show ratings honestly; FLUX 3 Video barely moves |
| `alley__dolly-in.mp4`, `alley__crane-up.mp4` | **Real** LTX-2.3 from Comfy Cloud's web UI, free tier, prompt-only, 5/10 each | "not made through this app's pipeline" |
| `examples/real/coverage/alley/` | **Real** FLUX 3 Image edits, 6 requests, 86.9 credits, 7/10; the close-up has a garbled unreadable emblem on the scooter | "real FLUX 3 Image edits" |
| The previs (every amber clip and every non-alley coverage tile) | **Simulated** by the Demo engine (depth-parallax virtual camera over a still) | "simulated", "a preview of the move"; never "AI-generated" or "model output" |

Never claim: camera-LoRA results (none exist), that the open-weights or Cloud engines ran live, that `/estimate` works (it answered "not enabled"; the static price table was used), or that Seedance/LTX-via-Router ran. The failed LTX orbit is not shown.

## (a) Shot list: 1:50

| # | Time | On-screen action | Clip shown | Voice-over | Honesty check |
|---|---|---|---|---|---|
| 1 | 0:00 to 0:07 | Title card, then the app on the **Forest Cabin** still. Amber **DEMO · no keys** pill visible. | none | This is Shot Director: free previs, then one real render. Open source, built on the Comfy platform. (17 words) | Amber DEMO pill |
| 2 | 0:07 to 0:22 | README architecture diagram, then the Engine card (Demo selected, the **Free** cost line). | none | One preset is one camera move, plain JSON. It maps to a free simulated camera for previs, a ComfyUI graph, and a partner-model request through the Comfy Router. Every paid call gets a price, a hard cap, one confirmation, and is never retried. (43 words) | Say "maps to", never "has run on" |
| 3 | 0:22 to 0:35 | Pick **FPV Drone**, click **Previs this shot (free)**. The amber clip plays; the "Previsualised" callout shows. | SIMULATED previs (Demo engine) | Pick a still and a move. The preview is free and simulated: the amber badge says so. It is a preview of the move, not a generated video. (28 words) | Amber badge on screen |
| 4 | 0:35 to 0:55 | Click **Play the real render**. Green badge, then open its recipe (model id, request id, credits 135.78). | REAL (hero): `forest-cabin__fpv-drone__router-minimax-h3.mp4`, MiniMax H3 via Router, 8/10 | Happy with it? One real render. This is MiniMax H3 through the Comfy Router: green badge, a partner model, not open weights, unedited. A hundred and thirty-six credits. The camera swoops past the cabin and into the forest; the forest at the end is invented. (45 words) | Badge names model + Router + "not open weights" + "unedited" |
| 5 | 0:55 to 1:14 | Scroll the **Example outputs** gallery (14 real clips). Click the FLUX 3 Video arc clip (4/10) for 3 s, then the alley **Orbit Left** (Grok lite, 7/10). | REAL: gallery clips | The gallery has fourteen real clips with their credits. Grok lite costs forty-eight and is close behind. FLUX 3 Video cost two hundred and twenty-six credits and barely moves: four out of ten. Pick the model by what it obeys, not by price. (43 words) | Per-clip badge and credits |
| 6 | 1:14 to 1:25 | Pick **Rainy Alley**, **Get coverage**: six tiles, green board badge. | REAL: FLUX 3 Image edits (alley coverage) | Coverage: six angles of the alley, real FLUX 3 Image edits, eighty-seven credits in total. The orbit that free LTX could not do, Grok lite managed. (26 words) | Green coverage badge; the stage clip keeps its own badge |
| 7 | 1:25 to 1:36 | **+ All real clips**, then **Make my reel (16:9 + 9:16)**; play both outputs. | REAL clips only (ffmpeg cut, labelled) | Make my reel cuts the real clips into sixteen by nine and nine by sixteen, labelled with the model. No credits spent. (22 words) | Burned-in "REAL: model via Comfy Router" label |
| 8 | 1:36 to 1:46 | `docs/COSTS.md` credit log for 3 s, then the engine list. | none | About thirteen hundred credits were spent in total, every request is logged. Open-weights and Cloud engines are contract-tested only. No camera LoRA result exists. (24 words) | No claim that open-weights or Cloud ran live |
| 9 | 1:46 to 1:50 | End card: repo URL and the live Space URL (huggingface.co/spaces/BoltTmade/shot-director), `#OpenSourceHiggsfield`. Hold at most 4 s. | none | Shot Director. Built for Open Source Higgsfield. (7 words) | Repo link github.com/bolttmade/shot-director |

Timings follow about 146 words per minute with short pauses; the cut ends at 1:50, leaving 10 s under the 2:00 limit. If the take runs long, cut beat 8 first, then beat 7.

## (b) Capture plan

**Setup (once).** `DEMO=1 ./run.sh`, then `http://127.0.0.1:8000` in a clean browser profile. No `.env`, and `COMFY_API_KEY` not exported in the recording shell. The real clips in `examples/real/` appear in the gallery automatically. Leave Length, Size and the scene box at defaults and do not drop a custom image or angle (any change makes the app produce a simulated clip instead of replaying the real one).

**Resolution.** Check at 1280x720 first; 1920x1080 is untested. Do a 10 s test capture and confirm the badge text is readable.

**Order.** (1) beats 2 and 8 (README diagram, Engine card, `docs/COSTS.md`); (2) beats 1, 3, 4 in one take: Forest Cabin → FPV Drone → Previs → **Play the real render**; (3) beat 5: gallery; (4) beat 6: Rainy Alley → Get coverage; (5) beat 7: **+ All real clips** → **Make my reel**. Re-record a beat rather than editing it, and never edit the real clips (no speed changes, crops or filters).

## (c) Voice-over script (255 words)

**1 (0:00 to 0:07)** This is Shot Director: free previs, then one real render. Open source, built on the Comfy platform.

**2 (0:07 to 0:22)** One preset is one camera move, plain JSON. It maps to a free simulated camera for previs, a ComfyUI graph, and a partner-model request through the Comfy Router. Every paid call gets a price, a hard cap, one confirmation, and is never retried.

**3 (0:22 to 0:35)** Pick a still and a move. The preview is free and simulated: the amber badge says so. It is a preview of the move, not a generated video.

**4 (0:35 to 0:55)** Happy with it? One real render. This is MiniMax H3 through the Comfy Router: green badge, a partner model, not open weights, unedited. A hundred and thirty-six credits. The camera swoops past the cabin and into the forest; the forest at the end is invented.

**5 (0:55 to 1:14)** The gallery has fourteen real clips with their credits. Grok lite costs forty-eight and is close behind. FLUX 3 Video cost two hundred and twenty-six credits and barely moves: four out of ten. Pick the model by what it obeys, not by price.

**6 (1:14 to 1:25)** Coverage: six angles of the alley, real FLUX 3 Image edits, eighty-seven credits in total. The orbit that free LTX could not do, Grok lite managed.

**7 (1:25 to 1:36)** Make my reel cuts the real clips into sixteen by nine and nine by sixteen, labelled with the model. No credits spent.

**8 (1:36 to 1:46)** About thirteen hundred credits were spent in total, every request is logged. Open-weights and Cloud engines are contract-tested only. No camera LoRA result exists.

**9 (1:46 to 1:50)** Shot Director. Built for Open Source Higgsfield.

Read it aloud once with a timer before recording. Say the credit numbers only if the recipe on screen agrees (H3 135.78, Grok lite 48.28, FLUX 3 Video 226.3, coverage 86.9; total about 1,310).

## (d) Pre-flight checklist

- [ ] Fresh browser profile: no extensions, bookmarks, other tabs, autofill or signed-in avatar; notifications off.
- [ ] No real name, email, handle or avatar anywhere on screen (profile, OS user, hostname, terminal prompt, window titles, GitHub menu). Only the anonymous **bolt** / **bolttmade** identity and `bolttmade@users.noreply.github.com`.
- [ ] No API key visible: no `.env`, `env` output, shell history, or Comfy dashboard/account page.
- [ ] Recipes opened on screen hold no local paths or personal data; the `credits_note` fields show the account balance in USD cents (skip scrolling to them).
- [ ] SFW, no people, no logos/IP. Note the garbled emblem in the alley close-up coverage still; do not zoom on it.
- [ ] Badges readable at export size: amber **Demo fixture: simulated camera move, not model output** and the green **Real ... output** badges.
- [ ] App is in Demo mode (the pill says so); the end card shows github.com/bolttmade/shot-director.
- [ ] Nothing says or implies: camera-LoRA works, open-weights or Cloud engines ran live, amber clips are model output, or that the app itself generated the LTX clips.
- [ ] Total length at most 2:00; the video is **not** posted or submitted by the builder: the owner submits under their own name.
