#!/usr/bin/env python3
"""Run the six-shot COVERAGE board live through the Comfy Router (FLUX 3 Image edits of one still). Costs credits (6 requests).

    COMFY_API_KEY=... python scripts/router_coverage.py --input alley --max-credits 100 [--yes]

Same engine path as the app's "Get coverage" button on the Router engine: estimate, cap check, then one `submit` per angle (never retried).
The six stills go to --out; the recipe lists every request id and prompt. A JSON report with the balance before/after (read-only call)
is written next to them. The key comes from the environment only and is never printed.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="One capped coverage board (6 FLUX 3 Image edits) via the Comfy Router.")
    ap.add_argument("--input", default="alley")
    ap.add_argument("--max-credits", type=float, default=100.0)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    if not os.environ.get("COMFY_API_KEY", "").strip():
        print("COMFY_API_KEY is not set.", file=sys.stderr)
        return 2
    os.environ.pop("DEMO", None)
    from app.engines.router import RouterEngine
    from app.samples import sample_source
    from app.types import CoverageRequest
    from smoke_real import read_balance_cents  # type: ignore

    out = a.out or ROOT / "outputs" / "runs" / f"coverage-{a.input}"
    eng = RouterEngine(cap=a.max_credits)
    req = CoverageRequest(source=sample_source(a.input))
    est = eng.estimate("coverage", req)
    print(f"estimate: {est.credits} credits (cap {a.max_credits:g}) | {est.note}")
    if est.over_cap:
        print("Refusing: over the cap.", file=sys.stderr)
        return 3
    if not a.yes and input("Run 6 FLUX 3 Image edits? Type 'yes': ").strip().lower() != "yes":
        return 1
    before = read_balance_cents()
    try:
        res = eng.coverage(req, lambda ev: print("  ·", ev.get("message")) if ev.get("message") else None, out)
    except Exception as e:  # noqa: BLE001
        print(f"FAILED (not retried): {getattr(e, 'message', None) or e}", file=sys.stderr)
        return 4
    after = read_balance_cents()
    delta = round((before - after) * 211 / 100, 2) if before is not None and after is not None else None
    rep = {"input": a.input, "estimate_credits": est.credits, "balance_cents_before": before, "balance_cents_after": after, "credits_by_balance": delta, "recipe": res.recipe, "files": [str(x.path) for x in res.artifacts]}
    (out / "report.json").write_text(json.dumps(rep, indent=2, default=str))
    print("saved:", *[x.path.name for x in res.artifacts], "| credits by balance:", delta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
