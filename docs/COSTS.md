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

## Credit log (what was actually spent)

| Date (UTC) | Where | What | Credits | Source of the number |
|---|---|---|---|---|
| 2026-10-16 | Comfy Cloud web UI (free account) | 3 LTX-2.3 prompt-only runs (dolly-in, crane-up, orbit-left) + 1 discarded pilot | 0 | free tier |
| 2026-10-16 | Router API | `scripts/smoke_real.py --duration 5`: `xai/grok-imagine-video-1.5-lite`, `alley` + `dolly-in`, 5 s @ 480p, ONE request (id `f98c1931-c864-4678-9671-60d4f9d9df48`), not retried | **30.17 (estimate), ~33.2 implied by balance** | `/estimate` answered "not enabled", so the app used its static price table (30.17 credits, about $0.143). The balance read afterwards was 984.27 cents; against a presumed 1,000 cents before (the top-up was $10.00, and the balance before the run was NOT read) that is 15.73 cents, about 33.2 credits at 211 per USD. True charge unverified: roughly 30-33 credits |
| 2026-10-16 | Router API | **Hero clip.** `scripts/smoke_real.py --preset crane-up --duration 5 --resolution 720p`: `xai/grok-imagine-video-1.5-lite`, `alley` + `crane-up`, 5 s @ 720p, ONE request (id `01e36596-d4d5-47dd-91bc-7bac11f57373`), not retried | **45.26 (estimate), ~48.3 measured by balance** | `/estimate` again "not enabled", so the static table gave 45.26 credits (about $0.214). Balance read **before** the run 984.27 cents, **after** 961.39 cents: 22.88 cents, about 48.3 credits at 211 per USD. The static table under-reports by about 7% |

Balance after the hero run: **961.39 cents (about $9.61, about 2,028 credits)** from `GET https://api.comfy.org/customers/balance` (read-only). Total Router spend so far: about 78-82 credits (about 30-33 for the dolly-in plus about 48.3 for the crane-up) of the 2,110 credits (the $10 top-up); the balance is far above the 1,700-credit floor the builders set for this task, and no further card charge has been made. Only the crane-up charge was measured against a balance read taken before the run; the dolly-in figure used an assumed starting balance. Credits come from a top-up by the owner.

The Router `/estimate` endpoint answered "not enabled" for this workspace (both runs), so the static table above is what is shown to users. It was within about 10% of what the balance implied both times, and it under-reports: budget about 10% above the table's number.
