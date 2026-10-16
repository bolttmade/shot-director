# Costs

Credits are **211 per US dollar** (Comfy's published rate). Prices below were read from docs.comfy.org on 2026-10-16 and may change: the app asks Router's `/estimate` first and only uses this table as a labelled fallback.

| Engine | You pay | Notes |
|---|---|---|
| Demo | $0 | Local CPU only |
| Open weights | $0 | Your GPU and electricity |
| Cloud / API deployment | GPU-seconds | **No pre-run quote**: refused unless `ALLOW_UNKNOWN_COST=1` |
| Router | per request | Estimated and capped, below |

## Router prices used for the fallback table

| Model | Role | Price |
|---|---|---|
| `xai/grok-imagine-video-1.5-lite` | cheapest image-to-video for testing | $0.0286/s at 480p, $0.0429/s at 720p |
| `minimax/minimax-h3` | default video model | $0.1287/s at 768P |
| `byteplus/dreamina-seedance-2-5-260628` | alternate | see `/estimate` (no static price) |
| `ltx/ltx-2-5-fast` / `-pro` | text-to-video only (no image input) | $0.1287/s / $0.1716/s at 720p |
| `bfl/flux-3-image` | angle re-frames and coverage stills | usage-based (GPU-seconds); app assumes up to $0.03 per still |

A 5 s MiniMax H3 clip is about $0.64 (about 136 credits), which is **over the default cap of 50 credits**: raise `MAX_CREDITS_PER_RUN` in `.env` to allow it, or pick Grok Imagine lite (5 s at 480p about $0.14, 30 credits). Coverage (six stills) is assumed to cost up to about $0.18.

## Guard rails

`MAX_CREDITS_PER_RUN` (default 50), `ALLOW_UNKNOWN_COST`, mandatory confirmation, no automatic retries, immediate downloads. Details in [HOW_IT_WORKS.md](HOW_IT_WORKS.md#cost-safety-router-and-cloud).

The development of this project spent **$0**: no key was available, and the Router and Cloud paths have never been called live.
