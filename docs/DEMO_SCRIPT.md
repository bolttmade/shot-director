# Demo script (target 1:45, hard limit 2:00)

**What the demo is about:** the *workflow*: a preset library of camera moves, a coverage board, an A/B player and a timeline that exports one cut, all on top of the Comfy platform. The generative model is one engine plugged into that workflow, not the pitch.

**Honesty rules for this video (non-negotiable):**

1. Two kinds of clips appear, and each is named out loud and on screen: **real** (green badge: real LTX-2.3, Comfy Cloud, *prompt-only, no camera LoRA, unedited*) and **simulated** (amber badge: the app's virtual camera over a still).
2. Never call an amber clip "AI-generated" or "model output".
3. Never show or imply camera-LoRA results: none exist. The controllable camera path (virtual camera, LoRA recipes) is demo/simulated or untested.
4. Say the quality of the real clips plainly: the dolly is smooth with some warping, the crane only partly works. The failed orbit is not shown.
5. Say that the open-weights, Cloud and Router engines are contract-tested but not run live.

**Setup:** `DEMO=1 ./run.sh` (or the Docker image), browser at 1280x720. Start on the `alley` frame. No keys needed. Keep the end card under 5 s so editing slop cannot push the cut past 2:00.

## Storyboard

| # | Time | On screen | Voice-over | Honesty check |
|---|---|---|---|---|
| 1 | 0:00 to 0:08 | Title card, then the app on the rainy-alley still. | "Shot Director: a shot-planning workflow for one still frame. Open source, built on the Comfy platform." | Amber **DEMO · no keys** pill visible. |
| 2 | 0:08 to 0:26 | The README architecture diagram (mermaid), highlighting preset → three backends, then the cost guard box. Cut to the engine panel and the **Free · exact** cost line. | "One preset is one camera move, as plain JSON. It maps to three backends: a ComfyUI graph with a camera LoRA through the Comfy SDK, a partner-model request through the Comfy Router, and a virtual camera for the offline demo. Every paid call gets a cost estimate first, a hard cap, one confirmation, and is never retried." | Say "maps to", not "has been run on". |
| 3 | 0:26 to 0:44 | Preset library (hover thumbnails); pick **Dolly In**; **Generate shot**. The **green** clip plays: "Real LTX-2.3 output (prompt-only, no camera LoRA), unedited". Open its recipe.json. | "This clip is real: LTX-2.3 on Comfy Cloud's free tier, from the official image-to-video template, with the move requested in the prompt only. A smooth dolly with some background warping. The recipe records the prompt and the workflow." | Green badge on screen; "prompt-only" said aloud. |
| 4 | 0:44 to 0:58 | Pick **Crane Up**: the green clip with "partial: rises but also pushes forward". | "The crane is only partly right: it rises, but also pushes forward. A prompt alone does not give reliable camera control; that is what camera LoRAs are for, and I have not been able to run them, so I will not show them." | Read the "partial" label. |
| 5 | 0:58 to 1:16 | **Orbit Left** on the alley: amber clip. **A/B** split of still vs clip. **Get coverage**: six tiles. | "For moves I could not run for real, the app uses its own simulated camera so you can see the workflow without a GPU; this badge says so. The A/B player compares still and clip, and the coverage board gives six angles from one frame." | Amber badge named: "simulated". |
| 6 | 1:16 to 1:30 | Add 3 clips to the timeline, reorder, **Export sequence**, play. | "Drop shots on the timeline, reorder, export one cut with crossfades. A cut that contains any simulated clip is flagged simulated." | Point at the "simulated" / "real" tag per timeline clip. |
| 7 | 1:30 to 1:40 | Engines list and the repo/licence line. | "The same presets drive open-weights ComfyUI, Cloud or the Router. Those engines are contract-tested but not yet run live." | No claim of live runs. |
| 8 | 1:40 to 1:45 | End card, `#OpenSourceHiggsfield`. | "Shot Director. Built for the Comfy Open Source Higgsfield contest." | Repo link: github.com/bolttmade/shot-director. |

249 spoken words (counted from the voice-over column): needs a brisk but clear read for 1:45. If it runs long, cut the last sentence of beat 2 first, then beat 6.

## What not to say

- Not "AI-generated" / "model output" for anything with the amber badge.
- Not "powered by LTX-2.3" for the app itself: the two real clips are plain LTX-2.3 prompts on Comfy Cloud, made in the Cloud web UI, not through this app's pipeline.
- Not that camera control works. The orbit prompt did not orbit; the crane partly worked.
- Not that the open-weights / Cloud / Router engines or the camera LoRAs "work" until they have been run live.

## Social post draft (DRAFT, not posted)

> Shot Director: one still in, camera moves, 6-angle coverage, A/B player, timeline cut out. Open source on @ComfyUI. 2 real clips (prompt-only LTX-2.3, Comfy Cloud); the app's moves are simulated/untested, labelled. https://github.com/bolttmade/shot-director #OpenSourceHiggsfield

(Attach the demo video. Repo link: https://github.com/bolttmade/shot-director, once the repo is public.)

(The draft is 279 characters including the URL and #OpenSourceHiggsfield, so it fits 280; X counts a URL as 23, so it is shorter there.)

Checks before posting: both badges are shown where they appear; the post does not say "camera LoRA" worked; the repo link works; the owner approves the post.
