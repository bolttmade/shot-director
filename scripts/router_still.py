#!/usr/bin/env python3
"""Generate ONE still image with FLUX 3 Image through the Comfy Router (text-to-image). Costs credits.

    COMFY_API_KEY=... python scripts/router_still.py --prompt "..." --name forest-cabin [--max-credits 30] [--yes]

Estimates first (static table: /estimate may not be enabled), refuses over the cap, submits exactly ONCE (never retried),
downloads at once, resizes to 1280x720 JPEG (no metadata) into --out and writes <name>.still.json with the request id and the
credit balance before/after (read-only balance call). The key comes from the environment only and is never printed.
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
    ap = argparse.ArgumentParser(description="One capped FLUX 3 Image text-to-image request via the Comfy Router.")
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--name", required=True, help="file stem, lowercase-hyphen (becomes the sample id)")
    ap.add_argument("--max-credits", type=float, default=30.0)
    ap.add_argument("--resolution", default="1k")
    ap.add_argument("--out", type=Path, default=ROOT / "outputs" / "stills")
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    if not os.environ.get("COMFY_API_KEY", "").strip():
        print("COMFY_API_KEY is not set.", file=sys.stderr)
        return 2
    os.environ.pop("DEMO", None)
    from PIL import Image

    from app.engines.router import RouterEngine
    from smoke_real import read_balance_cents  # type: ignore

    eng = RouterEngine(cap=a.max_credits)
    if not a.yes and input(f"Generate '{a.name}' with FLUX 3 Image (cap {a.max_credits:g} credits)? Type 'yes': ").strip().lower() != "yes":
        print("Cancelled.")
        return 1
    before = read_balance_cents()
    try:
        raw, info = eng.generate_still(a.prompt, a.out, lambda ev: print("  ·", ev.get("message") or ev.get("estimate") or "") if ev.get("message") or ev.get("estimate") else None, stem=a.name + ".raw", resolution=a.resolution)
    except Exception as e:  # noqa: BLE001
        print(f"FAILED (not retried): {getattr(e, 'message', None) or e}", file=sys.stderr)
        return 4
    after = read_balance_cents()
    im = Image.open(raw).convert("RGB")
    native = im.size
    im = im.resize((1280, 720), Image.LANCZOS) if abs(im.width / im.height - 16 / 9) < 0.02 else im.crop((0, (im.height - int(im.width * 9 / 16)) // 2, im.width, (im.height + int(im.width * 9 / 16)) // 2)).resize((1280, 720), Image.LANCZOS)
    jpg = a.out / f"{a.name}.jpg"
    im.save(jpg, "JPEG", quality=92)
    delta = round((before - after) * 211 / 100, 2) if before is not None and after is not None else None
    rep = {**info, "name": a.name, "prompt": a.prompt, "native_size": list(native), "balance_cents_before": before, "balance_cents_after": after, "credits_by_balance": delta, "file": str(jpg)}
    (a.out / f"{a.name}.still.json").write_text(json.dumps(rep, indent=2))
    print("saved:", jpg, "| native", native, "| credits by balance:", delta, "| request", info.get("router_request_id"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
