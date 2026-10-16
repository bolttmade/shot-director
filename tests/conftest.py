import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DEMO", "1")
for k in ("COMFY_API_KEY", "COMFY_BASE_URL", "ALLOW_UNKNOWN_COST"):
    os.environ.pop(k, None)  # tests never see a real key


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "outputs"))
    for k in ("COMFY_API_KEY", "COMFY_BASE_URL", "ALLOW_UNKNOWN_COST", "MAX_CREDITS_PER_RUN"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("DEMO", "0")  # adapter tests run as 'live'; server tests re-enable DEMO


@pytest.fixture
def sample_source():
    from app.samples import sample_source as ss
    return ss("alpine-dusk")


@pytest.fixture
def preset():
    from app.presets import load_presets
    return load_presets()["dolly-in"]
