import json

import jsonschema

from app.config import ROOT
from app.presets import build_prompt, load_options, load_presets
from app.vcam import CameraPath


def test_at_least_14_presets_and_all_validate():
    presets = load_presets()
    assert len(presets) >= 14
    schema = json.loads((ROOT / "presets" / "_schema.json").read_text())
    for p in sorted((ROOT / "presets").glob("*.json")):
        if p.name.startswith("_"):
            continue
        jsonschema.validate(json.loads(p.read_text()), schema)


def test_every_preset_is_wired_to_both_backends_and_a_virtual_camera():
    for pid, p in load_presets().items():
        assert p["engines"]["workflow"]["workflow"] and (ROOT / "workflows" / f"{p['engines']['workflow']['workflow']}.json").is_file(), pid
        assert "/" in p["engines"]["router"]["model"], pid
        CameraPath.from_spec(p["virtual_camera"])  # parses
        assert (ROOT / "examples" / "presets" / f"{pid}.mp4").is_file(), f"missing thumbnail for {pid}"


def test_build_prompt_fills_slots():
    p = load_presets()["orbit-left"]
    opts = load_options()
    out = build_prompt(p, scene="A red barn.", lens="35", mood="noir", options=opts)
    assert "A red barn." in out and "35mm" in out and "noir" in out.lower() and "{" not in out
    bare = build_prompt(p, scene="", lens=None, mood=None, options=opts)
    assert "{" not in bare and bare.strip()


def test_lora_names_are_official_ltx_camera_loras():
    for p in load_presets().values():
        if p.get("lora"):
            assert p["lora"]["name"].startswith("ltx-2-19b-lora-camera-control-")
            assert p["lora"]["source"].startswith("Lightricks/")
