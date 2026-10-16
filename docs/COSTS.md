# Costs

Credits are **211 per US dollar** (Comfy's published rate). Prices below were read from docs.comfy.org on 2026-10-16 and were then **checked against real spend** (see the log): the app asks Router's `/estimate` first, but that endpoint answered "not enabled" for this workspace on every run, so it fell back to the static table below, which now carries the measured rates.

| Engine | You pay | Notes |
|---|---|---|
| Demo | $0 | Local CPU only: the free **previs** |
| Open weights | $0 | Your GPU and electricity |
| Cloud / API deployment | GPU-seconds | **No pre-run quote**: refused unless `ALLOW_UNKNOWN_COST=1` |
| Router | per request | The one real render; capped and confirmed, below |

## Router prices used for the static fallback table

| Model | Role | Published | Measured by balance delta (2026-10-16) |
|---|---|---|---|
| `xai/grok-imagine-video-1.5-lite` | cheapest image-to-video for testing | $0.0286/s at 480p, $0.0429/s at 720p | **$0.0458/s at 720p** (48.28 credits per 5 s, 5 runs). The table **under-reported by about 7%** until it was updated to this. 480p: one run, about 33 credits per 5 s |
| `minimax/minimax-h3` | default video model | $0.1287/s at 768P | **$0.1287/s: exact** (135.78 credits per 5 s, 5 runs) |
| `bfl/flux-3-video` | image-to-video (FLUX bonus) | about $0.243/s at hd in Comfy's pricing UI (billed per GPU-second) | **$0.2145/s** (226.3 credits for one 5 s hd clip, 12% below the UI figure; one run) |
| `bfl/flux-3-image` | stills, angle re-shoots, coverage | usage-based (GPU-seconds) | **14.48 credits per 1K still** (9 requests: 3 text-to-image and 6 coverage edits, 86.9 / 6 = 14.48) |
| `byteplus/dreamina-seedance-2-5-260628` | alternate | see `/estimate` (no static price) | not run |
| `ltx/ltx-2-5-fast` / `-pro` | text-to-video only (no image input) | $0.1287/s / $0.1716/s at 720p | not run |

A 5 s MiniMax H3 clip is about $0.64 (136 credits), which is **over the default cap of 50 credits**: raise `MAX_CREDITS_PER_RUN` in `.env` to allow it, or pick Grok Imagine lite (5 s at 720p is 48 credits). The six-still coverage board is about 87 credits.

## Guard rails

`MAX_CREDITS_PER_RUN` (default 50), `ALLOW_UNKNOWN_COST`, mandatory confirmation, no automatic retries, immediate downloads. Details in [HOW_IT_WORKS.md](HOW_IT_WORKS.md#cost-safety-router-and-cloud). The batch scripts used here (`scripts/smoke_real.py`, `scripts/router_still.py`, `scripts/router_coverage.py`) read the balance (`GET https://api.comfy.org/customers/balance`, read-only) before and after each run, set a per-run `--max-credits` cap, run one request at a time and never retry a submit. No card charge or top-up was made for any of it.

## Credit log (what was actually spent)

Everything below happened on **2026-10-16** through the Comfy Router API with the account's existing credits. "Estimate" is the app's static-table number; "balance delta" is the measured charge (balance in USD cents before → after, 211 credits per USD).

### Earlier runs (first two real clips)

| Where | What | Estimate | Measured | Request id |
|---|---|---|---|---|
| Comfy Cloud web UI (free tier) | 3 LTX-2.3 prompt-only runs + 1 discarded pilot | 0 | 0 | n/a |
| Router | Grok lite `alley` + `dolly-in`, 5 s at 480p | 30.17 | about 33.2 (balance before the run was **not** read; the start was presumed to be 1,000 cents, so 30-33) | `f98c1931-c864-4678-9671-60d4f9d9df48` |
| Router | Grok lite `alley` + `crane-up`, 5 s at 720p | 45.26 | **48.27** (984.27 → 961.39 cents) | `01e36596-d4d5-47dd-91bc-7bac11f57373` |

### Input stills (FLUX 3 Image, text-to-image)

| What | Model | Estimate | Balance (cents) | Measured credits | Request id |
|---|---|---|---|---|---|
| `forest-cabin` still | FLUX 3 Image 1K, text-to-image | 14.77 | 961.39 → 954.526 | **14.48** | `790c6435-8964-47b2-8a23-4798061df895` |
| `retro-diner` still | FLUX 3 Image 1K, text-to-image | 14.77 | 954.526 → 947.662 | **14.48** | `d334369c-5954-49e7-a406-ac801678a62a` |
| `coast-lighthouse` still | FLUX 3 Image 1K, text-to-image | 14.77 | 947.662 → 940.798 | **14.48** | `f10cc1e7-9f2a-4f73-86ac-02ca347df836` |

### Video clips (image-to-video, 5 s each, one request each)

| Input + preset | Model | Estimate | Balance (cents) | Measured credits | Request id |
|---|---|---|---|---|---|
| `forest-cabin` + `dolly-in` | MiniMax H3 768P | 135.78 | 940.798 → 876.448 | **135.78** | `65771eb4-a475-4eb3-abbc-646a30610c0b` |
| `coast-lighthouse` + `orbit-right` | MiniMax H3 768P | 135.78 | 876.448 → 812.098 | **135.78** | `53e79d78-6119-4aa1-b7bb-1f12959d3734` |
| `retro-diner` + `dolly-right` | MiniMax H3 768P | 135.78 | 812.098 → 747.748 | **135.78** | `f6969912-9290-47a2-ad2f-bf1ac60746c7` |
| `retro-diner` + `dolly-in` | Grok lite 720p | 45.26 | 747.748 → 724.868 | **48.28** | `82c84619-f861-4d5a-8c6f-7c401d40b8e8` |
| `forest-cabin` + `push-in-rack` | Grok lite 720p | 45.26 | 724.868 → 701.988 | **48.28** | `a6bec79a-c78e-4efe-b41c-88472c9afcae` |
| `alley` + `orbit-left` | Grok lite 720p | 45.26 | 701.988 → 679.108 | **48.28** | `de69601b-34fd-4c89-8545-45bd0fa74edc` |
| `coast-lighthouse` + `jib-up` | Grok lite 720p | 45.26 | 679.108 → 656.228 | **48.28** | `98ed7f71-41ab-4312-83f2-d015b454f9a1` |
| `alley` + `crane-up` | MiniMax H3 768P | 135.78 | 656.228 → 591.878 | **135.78** | `31b4c758-be46-48bc-9ca0-c6df3e778e00` |
| `forest-cabin` + `fpv-drone` | MiniMax H3 768P | 135.78 | 550.694 → 486.344 | **135.78** | `ccca0eb9-4969-4ae4-987d-926daddd2f71` |
| `retro-diner` + `arc` | FLUX 3 Video hd | 256.36 | 486.344 → 379.09401 | **226.3** | `71a822c0-01bb-4ffe-8923-9353249ce156` |

### Coverage (FLUX 3 Image edits of the alley still)

| What | Model | Estimate | Balance (cents) | Measured credits | Request ids |
|---|---|---|---|---|---|
| `alley` coverage (6 stills) | FLUX 3 Image edits, 6 requests | 86.85 | 591.878 → 550.694 | **86.9** | wide `b45cf408-b7ee-4de1-b601-5658603c1b28`, medium `898192f6-ce15-45f6-84a0-d3315f019359`, close `417c4883-a63a-4e31-a14c-02f323dade03`, low `2f79329d-b4b9-40e5-ba85-2b45791acc0f`, high `5092db8d-5ed2-4212-926c-d4c460e11cb3`, profile `07804877-ce57-4fcd-bb97-048ce89960e3` |

### Browser test of the Space's "run it yourself" panel

| What | Model | Estimate | Balance (cents) | Measured credits | Request id |
|---|---|---|---|---|---|
| Static page, own-key panel, driven in headless Chrome (origin `http://127.0.0.1`), `forest-cabin` + dolly-in, 2 s | Grok lite 480p | 13.3 | 379.094 → 371.944 | **15.09** | `d8674baa-a97f-4931-966b-eb6a43d22670` |

CORS from a browser origin works; one POST, status polls, one result read, no retry. A 2 s 480p clip cost 7.5 credits/s, above the 6.65/s of the 5 s runs, so very short Grok clips seem to carry a small minimum.

### Totals and balance

* New spend in this round (stills + 10 clips + coverage): 43.4 + 678.9 (5 H3) + 193.1 (4 Grok) + 226.3 (FLUX 3 Video) + 86.9 = **1,228.7 credits** (about $5.82). Add the two earlier real clips (about 33 and 48.3) and the grand total of Router spend is about **1,310 credits (about $6.21)**, plus 15.1 credits for the browser test of the static page's own-key panel (about 1,325 in all).
* **Balance now: 371.94 cents (about $3.72, about 785 credits)** from `GET https://api.comfy.org/customers/balance`, kept above the 200-credit floor. The $10 top-up was made earlier by the owner; no further card charge was made.
* Every request above was submitted exactly once and never retried; no 402 and no failed Router call occurred (0 of the 3 allowed failures used).

### Estimate vs measured

* **MiniMax H3**: the table was exact (135.78 estimate, 135.78 measured, 5/5).
* **Grok lite 720p**: estimate 45.26, measured 48.28 (+6.7%). The table now uses the measured rate. 480p is a single data point.
* **FLUX 3 Image**: the static value was an assumption (up to $0.03 per still); measured 14.48 credits ($0.0686) per still, so the table now carries that.
* **FLUX 3 Video**: estimated 256.4 from the pricing UI, measured 226.3 (-12%): billing is per GPU-second so it may drift. The table now carries the measured rate for `hd`.
* **Balance lag**: on one run (H3 `forest-cabin` + `fpv-drone`) the balance read straight after the run still showed the old value (delta 0.0); a few minutes later it had dropped by exactly 135.78 credits. Read the balance again after a short wait if a delta looks like zero.

`/estimate` was never enabled for this workspace, so no estimate in the UI came from the Router; every one came from the static table, and each is labelled that way in the app.
