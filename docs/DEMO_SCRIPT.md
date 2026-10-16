# Demo script (target 1:45, hard limit 2:00)

> **The shot list, capture plan, voice-over and pre-flight checklist now live in [DEMO_VIDEO_PLAN.md](DEMO_VIDEO_PLAN.md)** (hero: the MiniMax H3 FPV drone render). This file keeps the honesty rules, the "what not to say" list and the social-post draft, which still apply.

**What the demo is about:** the *workflow*: a preset library of camera moves, a coverage board, an A/B player and a timeline that exports one cut, all on top of the Comfy platform. The generative model is one engine plugged into that workflow, not the pitch.

**Honesty rules for this video (non-negotiable):**

1. Two kinds of clips appear, and each is named out loud and on screen: **real** (green badge naming the model: LTX-2.3 on Comfy Cloud, or MiniMax H3 / Grok Imagine 1.5 lite / FLUX 3 Video / FLUX 3 Image via the Comfy Router, *prompt-only, no camera LoRA, unedited*) and **simulated** (amber badge: the app's free virtual-camera previs over a still).
2. Never call an amber clip "AI-generated" or "model output". It is a preview of the move.
3. Never show or imply camera-LoRA results: none exist.
4. Say the quality plainly with the own ratings: the hero H3 FPV swoop is 7/10 (blurry mid-swoop, invents its ending), FLUX 3 Video barely moves (4/10), the LTX clips are 5/10. The failed LTX orbit is not shown.
5. **Router beat + credit log.** Say that the Router ran live (12 video clips and 9 FLUX image requests, about 1,310 credits in total, every request logged in `docs/COSTS.md`), that these are partner models, not open weights and not LTX, and show the credit log briefly. Say that the open-weights and Cloud engines are contract-tested but not run live, and that `/estimate` was not enabled (the static price table was used).

**Setup:** `DEMO=1 ./run.sh` (or the Docker image), browser at 1280x720. Start on the `alley` frame. No keys needed. Keep the end card under 5 s so editing slop cannot push the cut past 2:00.

## Storyboard

See [DEMO_VIDEO_PLAN.md](DEMO_VIDEO_PLAN.md#as-built-shot-list) (twelve beats, about 235 spoken words, built by `scripts/make_demo_video.sh`). Summary: real hero clip first, concept, free previs then the real render, gallery comparison across models, real FLUX 3 coverage with A/B, Make my reel, the Space, the platform facts, the credit log and the end card. The captions-only file is the primary cut (the piper voice's data licence is research-only, see the plan).

## What not to say

- Not "AI-generated" / "model output" for anything with the amber badge.
- Not "powered by LTX-2.3" for the app itself: the two real LTX clips are plain LTX-2.3 prompts on Comfy Cloud, made in the Cloud web UI, not through this app's pipeline.
- Not "open weights" or "LTX" for the Router clips: MiniMax H3, Grok Imagine 1.5 lite and FLUX 3 are partner models.
- Not that prompt-only camera control is reliable (ratings 4-8/10; the LTX orbit failed, the FLUX 3 Video arc barely moved).
- Not that the open-weights / Cloud engines or the camera LoRAs "work": they have not been run live. The Router has (see COSTS.md).

## Social post draft (DRAFT, not posted)

> Shot Director: free previs, then one real render. Preview a camera move free, render it once with MiniMax H3, Grok or FLUX 3 via Comfy Router, cut a 16:9 + 9:16 reel. 14 real clips, labelled; the rest simulated. https://github.com/bolttmade/shot-director #OpenSourceHiggsfield

(Attach the demo video. Repo link: https://github.com/bolttmade/shot-director. Live static demo (free Hugging Face Space, nothing to install): https://huggingface.co/spaces/BoltTmade/shot-director , worth adding to the post or its reply if there is room: it does not fit in the 280 characters above. The draft is 276 characters including the URL and the hashtag, so it fits 280 (X counts a URL as 23). "14 real clips" = 2 LTX-2.3 + 12 Router clips in `examples/real/`.)

Checks before posting: both badges are shown where they appear; the post does not say "camera LoRA" worked; the repo link works; the owner approves the post.
