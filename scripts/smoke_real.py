#!/usr/bin/env python3
"""Live smoke test of the Router path, for someone with their own Comfy API key and credits. Not run by the authors.

    COMFY_API_KEY=... python scripts/smoke_real.py --dry-run     # estimate only: nothing is submitted
    COMFY_API_KEY=... python scripts/smoke_real.py               # estimate, ask for confirmation, ONE tiny request

What it does, in this order (the same guard the app uses):
  1. Builds the cheapest sensible request: the `alley` frame, the `dolly-in` preset, Grok Imagine 1.5 lite, 480p, 2 s.
  2. Asks the Router for a price (`/estimate`); falls back to the static table and says so. An unknown price is refused.
  3. Refuses if the estimate is over the cap (`--max-credits`, default min(MAX_CREDITS_PER_RUN, 10)).
  4. Prints the model, estimate and cap and asks you to type `yes` (or pass `--yes`).
  5. Submits exactly ONCE. It never retries a submit (a retry could be billed twice); on any error it stops and prints it.
  6. Saves the clip and its recipe.json under outputs/smoke/ (the recipe says simulated=false and names the model).

The key is read from the environment only; it is never printed or written to a file.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_MODEL = "xai/grok-imagine-video-1.5-lite"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="One tiny, capped, confirmed Router request.")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Router model id (default {DEFAULT_MODEL}, the cheapest image-to-video)")
    ap.add_argument("--input", default="alley", help="sample frame id from examples/inputs/")
    ap.add_argument("--preset", default="dolly-in")
    ap.add_argument("--duration", type=int, default=2, help="seconds (model minimums apply)")
    ap.add_argument("--resolution", choices=["480p", "720p"], default="480p")
    ap.add_argument("--max-credits", type=float, default=None, help="hard cap for this run (default min(MAX_CREDITS_PER_RUN, 10))")
    ap.add_argument("--dry-run", action="store_true", help="estimate only; submit nothing")
    ap.add_argument("--yes", action="store_true", help="skip the interactive confirmation (the cap still applies)")
    ap.add_argument("--out", type=Path, default=ROOT / "outputs" / "smoke")
    a = ap.parse_args(argv)

    if not os.environ.get("COMFY_API_KEY", "").strip():
        print("COMFY_API_KEY is not set. Create a key in the Comfy dashboard and export it (never commit it).", file=sys.stderr)
        return 2
    os.environ.pop("DEMO", None)  # the demo switch would disable the Router engine

    from app.config import get_settings
    from app.engines.router import RouterEngine
    from app.presets import build_prompt, load_presets
    from app.samples import sample_source
    from app.types import ShotRequest

    cap = a.max_credits if a.max_credits is not None else min(get_settings().max_credits_per_run, 10.0)
    presets = load_presets()
    preset = presets.get(a.preset) if isinstance(presets, dict) else next((p for p in presets if p["id"] == a.preset), None)
    if not preset:
        print(f"unknown preset {a.preset!r}", file=sys.stderr)
        return 2
    try:
        source = sample_source(a.input)
    except KeyError:
        print(f"unknown input {a.input!r}", file=sys.stderr)
        return 2

    eng = RouterEngine(cap=cap)
    req = ShotRequest(source=source, preset=preset, duration=a.duration, resolution=a.resolution, model=a.model, prompt=build_prompt(preset))
    est = eng.estimate("shot", req)
    cost = "unknown" if est.credits is None else f"{est.credits:g} credits" + (f" (~${est.usd:.3f})" if est.usd is not None else "")
    print(f"model      : {a.model}\nrequest    : {a.input} + {a.preset}, {a.duration}s @ {a.resolution}\nestimate   : {cost} ({'exact' if est.exact else 'estimate'})\ncap        : {cap:g} credits\nnote       : {est.note or '-'}")
    if est.credits is None:
        print("Refusing: the price is unknown. Set ALLOW_UNKNOWN_COST=1 only if you accept that.", file=sys.stderr)
        if os.environ.get("ALLOW_UNKNOWN_COST") != "1":
            return 3
    if est.over_cap:
        print(f"Refusing: the estimate is over your cap of {cap:g} credits. Raise --max-credits deliberately, or pick a cheaper model/shorter clip.", file=sys.stderr)
        return 3
    if a.dry_run:
        print("Dry run: nothing submitted.")
        return 0
    if not a.yes:
        if input("Submit ONE request and spend credits? Type 'yes': ").strip().lower() != "yes":
            print("Cancelled. Nothing submitted.")
            return 1
    a.out.mkdir(parents=True, exist_ok=True)

    def emit(ev: dict) -> None:
        msg = ev.get("message")
        if msg:
            print("  ·", msg)

    try:
        res = eng.run_shot(req, emit, a.out)   # one submit; the engine and this script never retry it
    except Exception as e:  # noqa: BLE001  (print and stop: no retry)
        print(f"FAILED (not retried): {getattr(e, 'message', None) or e}", file=sys.stderr)
        return 4
    for art in res.artifacts:
        print("saved:", art.path)
    print("credits used:", res.credits_used if res.credits_used is not None else "unknown", "| recipe simulated =", res.recipe.get("simulated"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
