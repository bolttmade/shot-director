#!/usr/bin/env python3
"""Open-weights compliance check for the workflows in workflows/.

Comfy's "Open Weights Only" category forbids partner / API nodes (nodes that call a hosted model and cost
credits). This script fails if any workflow node looks like one, and prints every node type it did find so a
human can double-check the list. It is a static check: it cannot prove which weights a server has installed.

    python scripts/check_open_weights.py            # exit 1 on a violation
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Partner ("API") node class-name patterns from ComfyUI's comfy_api_nodes package.
PARTNER_PATTERNS = [
    r"^OpenAI", r"^Gemini", r"^Kling", r"^Luma", r"^Runway", r"^Minimax", r"^Veo", r"^BFL", r"^Flux(Pro|Ultra|Fill|Canny|Depth|Kontext(Pro|Max))",
    r"^Ideogram", r"^Stability", r"^Pika", r"^Pixverse", r"^Vidu", r"^Recraft", r"^Moonvalley", r"^Tripo", r"^Rodin", r"^ByteDance", r"^Seedance",
    r"^Seedream", r"^Sora", r"^Grok", r"^Xai", r"^Hunyuan3D.*API", r"^Wan.*(API|Partner)", r"^Ltxv?.*API", r"^Anthropic", r"^Claude", r"^Topaz",
    r"^Magnific", r"^Hailuo", r"^Midjourney", r"^PrimeTranslate", r"^Dreamina", r"^Comfy(Router|Api)", r"Partner", r"APINode", r"ApiNode",
]
PARTNER_RE = re.compile("|".join(PARTNER_PATTERNS), re.I)


def node_types(graph: dict) -> dict[str, int]:
    """Count node class types in either ComfyUI format.

    * API format: {"<id>": {"class_type": ..., "inputs": {...}}}
    * UI/workflow format (templates, "Export"): {"nodes": [...{"type": ...}], "definitions": {"subgraphs": [...]}};
      subgraph definitions are descended into, and the subgraph wrapper nodes (UUID types) are not counted.
    """
    out: dict[str, int] = {}

    def add(t: str) -> None:
        out[t] = out.get(t, 0) + 1

    if isinstance(graph.get("nodes"), list):
        sub_ids = {sg.get("id") for sg in graph.get("definitions", {}).get("subgraphs", [])}

        def walk(nodes: list) -> None:
            for n in nodes:
                if isinstance(n, dict) and n.get("type") and n["type"] not in sub_ids:
                    add(n["type"])

        walk(graph["nodes"])
        for sg in graph.get("definitions", {}).get("subgraphs", []):
            walk(sg.get("nodes", []))
        return out
    for node in graph.values():
        if isinstance(node, dict) and "class_type" in node:
            add(node["class_type"])
    return out


def check_graph(graph: dict) -> list[str]:
    return sorted(t for t in node_types(graph) if PARTNER_RE.search(t))


def check_dir(wdir: Path = ROOT / "workflows") -> dict[str, list[str]]:
    bad: dict[str, list[str]] = {}
    for p in sorted(wdir.rglob("*.json")):
        if p.name.endswith(".meta.json"):
            continue
        hits = check_graph(json.loads(p.read_text()))
        if hits:
            bad[str(p.relative_to(wdir))] = hits
    return bad


def main() -> int:
    wdir = ROOT / "workflows"
    files = [p for p in sorted(wdir.rglob("*.json")) if not p.name.endswith(".meta.json")]
    if not files:
        print("No workflows found", file=sys.stderr)
        return 2
    for p in files:
        types = node_types(json.loads(p.read_text()))
        print(f"{p.name}: {sum(types.values())} nodes, {len(types)} types")
        print("   " + ", ".join(sorted(types)))
    bad = check_dir(wdir)
    if bad:
        for name, hits in bad.items():
            print(f"FAIL {name}: partner/API nodes: {', '.join(hits)}", file=sys.stderr)
        return 1
    print("\nOK: no partner/API nodes found in any workflow (static check; see docs/MODELS.md for the weights and licences).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
