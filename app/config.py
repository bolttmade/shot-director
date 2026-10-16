"""Runtime configuration from environment variables (and an optional local .env)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path | None = None) -> None:
    """Tiny .env loader (no dependency). Existing environment variables win."""
    path = path or ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip("'\"")
        if v and k not in os.environ:
            os.environ[k] = v


def _truthy(v: str | None) -> bool:
    return (v or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    demo: bool
    host: str
    port: int
    api_key_present: bool
    comfy_base_url: str  # "" means Comfy Cloud default
    max_credits_per_run: float
    outputs_dir: Path
    examples_dir: Path
    presets_dir: Path
    workflows_dir: Path
    web_dir: Path
    repo_url: str = "https://github.com/bolttmade/shot-director"
    real_dir: Path = ROOT / "examples" / "real"


def get_settings() -> Settings:
    load_dotenv()
    mc = os.environ.get("MAX_CREDITS_PER_RUN", "").strip()
    return Settings(
        demo=_truthy(os.environ.get("DEMO")),
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        api_key_present=bool(os.environ.get("COMFY_API_KEY", "").strip()),
        comfy_base_url=os.environ.get("COMFY_BASE_URL", "").strip(),
        max_credits_per_run=float(mc) if mc else 50.0,  # conservative default: ~$0.24 (one cheap 480p clip)
        outputs_dir=Path(os.environ.get("OUTPUTS_DIR", ROOT / "outputs")),
        examples_dir=ROOT / "examples",
        presets_dir=ROOT / "presets",
        workflows_dir=ROOT / "workflows",
        web_dir=ROOT / "web",
        repo_url=os.environ.get("REPO_URL", "").strip() or "https://github.com/bolttmade/shot-director",
        real_dir=Path(os.environ.get("REAL_DIR") or ROOT / "examples" / "real"),
    )
