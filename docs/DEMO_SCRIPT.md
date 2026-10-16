# Demo script (target 1:45, hard limit 2:00)

> **The shot list, capture plan, voice-over and pre-flight checklist now live in [DEMO_VIDEO_PLAN.md](DEMO_VIDEO_PLAN.md)** (it adds the 720p Router crane-up as the hero clip). This file keeps the honesty rules, the "what not to say" list and the social-post draft, which still apply.

**What the demo is about:** the *workflow*: a preset library of camera moves, a coverage board, an A/B player and a timeline that exports one cut, all on top of the Comfy platform. The generative model is one engine plugged into that workflow, not the pitch.

**Honesty rules for this video (non-negotiable):**

1. Two kinds of clips appear, and each is named out loud and on screen: **real** (green badge: real LTX-2.3 on Comfy Cloud, or Grok Imagine 1.5 lite via the Comfy Router, *prompt-only, no camera LoRA, unedited*) and **simulated** (amber badge: the app's virtual camera over a still).
2. Never call an amber clip "AI-generated" or "model output".
3. Never show or imply camera-LoRA results: none exist. The controllable camera path (virtual camera, LoRA recipes) is demo/simulated or untested.
4. Say the quality of the real clips plainly: the LTX dolly is smooth with some warping, the LTX crane only partly works, and the Router crane-up is clean but its revealed walls are invented. The failed orbit is not shown.
5. Say that the open-weights and Cloud engines are contract-tested but not run live, and the Router engine was run live twice (two Grok Imagine 1.5 lite clips, about 30 and about 48 credits). The 720p Router crane-up is the hero clip: it is the cleanest real clip, and it is a partner model, not open weights, not LTX.

**Setup:** `DEMO=1 ./run.sh` (or the Docker image), browser at 1280x720. Start on the `alley` frame. No keys needed. Keep the end card under 5 s so editing slop cannot push the cut past 2:00.

## Storyboard

See [DEMO_VIDEO_PLAN.md](DEMO_VIDEO_PLAN.md#a-shot-list-145) (nine beats, 256 spoken words). Summary: intro, architecture and cost guard, real LTX dolly, partial LTX crane, **real Router crane-up (hero)**, simulated orbit + A/B + coverage, timeline export, engine honesty line, end card.

## What not to say

- Not "AI-generated" / "model output" for anything with the amber badge.
- Not "powered by LTX-2.3" for the app itself: the two real LTX clips are plain LTX-2.3 prompts on Comfy Cloud, made in the Cloud web UI, not through this app's pipeline.
- Not "open weights" or "LTX" for the Router clips: Grok Imagine 1.5 lite is a partner model.
- Not that camera control works. The orbit prompt did not orbit; the crane partly worked.
- Not that the open-weights / Cloud engines or the camera LoRAs "work" until they have been run live (the Router has run live twice, for two clips).

## Social post draft (DRAFT, not posted)

> Shot Director: one still in, camera moves, 6-angle coverage, A/B player, timeline cut out. Open source on @ComfyUI. Real clips (LTX-2.3 on Cloud, Grok Imagine via Router) are labelled; the rest is simulated. https://github.com/bolttmade/shot-director #OpenSourceHiggsfield

(Attach the demo video. Repo link: https://github.com/bolttmade/shot-director, once the repo is public.)

(The draft is 270 characters including the URL and #OpenSourceHiggsfield, so it fits 280; X counts a URL as 23, so it is shorter there.)

Checks before posting: both badges are shown where they appear; the post does not say "camera LoRA" worked; the repo link works; the owner approves the post.
