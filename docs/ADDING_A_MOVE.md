# Adding a camera move

A move is one JSON file in `presets/`. No code changes.

```json
{
  "$schema": "./_schema.json",
  "id": "tilt-up-reveal",
  "name": "Tilt Up Reveal",
  "category": "special",
  "description": "Camera tilts up from the ground to reveal the subject.",
  "prompt_template": "{scene} The camera tilts slowly upward, revealing the full height of the subject. {lens} {mood}",
  "negative": "camera shake, jitter, warping, morphing, flicker, scene cut, text, watermark",
  "duration": 5,
  "lora": null,
  "virtual_camera": { "keys": [ {"t": 0, "pitch": -6}, {"t": 1, "pitch": 6} ], "ease": "inout" },
  "engines": {
    "workflow": { "workflow": "ltx2_i2v_camera", "params": { "cfg": 4.0 } },
    "router":   { "model": "minimax/minimax-h3", "alternates": ["xai/grok-imagine-video-1.5-lite"], "body_overrides": {} }
  }
}
```

Fields (full rules in `presets/_schema.json`, enforced by `tests/test_presets.py`):

| Field | Meaning |
|---|---|
| `id` | kebab-case, also the thumbnail name `examples/presets/<id>.mp4` |
| `category` | `dolly`, `jib`, `orbit`, `special` or `static` (UI filter chips) |
| `prompt_template` | Describe the *destination* of the move (works best for LTX camera LoRAs). Slots: `{scene}`, `{lens}`, `{mood}` |
| `lora` | `null`, or an official LTX-2 camera LoRA: `{"name": "ltx-2-19b-lora-camera-control-<move>.safetensors", "strength": 1.0, "source": "Lightricks/LTX-2-19b-LoRA-Camera-Control-<Move>"}`. With `null` the LoRA nodes are removed from the graph |
| `virtual_camera` | Demo-engine path only. Channels: `right`, `up`, `forward` (metres, scene is 3-30 m deep), `yaw`, `pitch`, `roll` (degrees; pitch + = up), `zoom`. Optional `shake`, `motion_blur`, `rack` (`{"from": 0.2, "to": 0.8}`), `ease` (`linear|in|out|inout|snap`) |
| `engines.workflow` | Graph name in `workflows/` plus parameters |
| `engines.router` | Default model id, alternates, request-body overrides (see `docs/COSTS.md` for ids) |

Then:

1. `python scripts/make_fixtures.py --quick` (or render just your thumbnail) so the UI card shows a preview; the test suite requires `examples/presets/<id>.mp4`.
2. `pytest -q`.
3. Reload the app. Your move appears in the grid.

Tips: keep Demo moves under about 1.5 m of travel (one still cannot reveal what was never visible); for a LoRA that is not listed, set `"lora": null` and describe the move in the prompt.
