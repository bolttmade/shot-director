# Workflows

**Status: UNTESTED.** Neither graph has been run in ComfyUI (the machine this was built on has no GPU). They were assembled from the official examples (LTX-2 `I2V_Full_wLora`, and the Qwen-Image-Edit-2511 multi-angle example) and are checked statically by `tests/test_open_weights.py`: every node id in `*.meta.json` exists, and every field it names is an input of that node. Expect to fix model file names or node versions on first real run.

Both graphs are ComfyUI **API format** (export with *Save (API Format)*). They use only ComfyUI core nodes and Lightricks LTXV nodes: no partner/API nodes (`scripts/check_open_weights.py`). Rebuild them with `python scripts/build_workflows.py`.

## `ltx2_i2v_camera.json` (LTX-2 19B image-to-video + camera LoRA)

| Input | Node id | Field |
|---|---|---|
| source image | 4 (`LoadImage`) | `image` |
| prompt | 8 (`CLIPTextEncode`) | `text` |
| negative prompt | 9 | `text` |
| seed | 24, 33 (`RandomNoise`) | `noise_seed` |
| width / height | 12 | `width`, `height` |
| frames (8n+1) | 20 (`PrimitiveInt`) | `value` |
| fps | 10, 18, 39 | `frame_rate` / `fps` |
| camera LoRA | 5, 7 (`LoraLoaderModelOnly`) | `lora_name`, `strength_model` |
| CFG | 22 | `cfg` |
| **output** | **40 (`SaveVideo`)** | |

Moves with no LoRA: the app removes nodes 5 and 7 through `Workflow.remove_node`.

## `qwen_edit_angle.json` (Qwen-Image-Edit-2511 + Multiple-Angles LoRA)

| Input | Node id | Field |
|---|---|---|
| source image | 41 (`LoadImage`) | `image` |
| angle prompt (`<sks> …`) | 112 (`TextEncodeQwenImageEditPlus`) | `prompt` |
| seed | 106 (`KSampler`) | `seed` |
| angle LoRA strength | 109 | `strength_model` |
| **output** | **9 (`SaveImage`)** | |

The machine-readable version of these tables is each graph's `.meta.json`; the workflow adapter reads it, so node ids are never hard-coded in Python. Model files: [docs/MODELS.md](../docs/MODELS.md).

## `ltx23_i2v_official_template.json` (reference, UI format with a subgraph)

An **unmodified copy of Comfy Org's official "LTX-2.3: Image to Video" template** (MIT, attribution in [`ltx23_i2v_official_template.NOTICE.md`](ltx23_i2v_official_template.NOTICE.md)). Unlike the two graphs above it is the UI/workflow format (nodes live in a subgraph), has no `.meta.json`, and the app does not drive it. `scripts/check_open_weights.py` scans both formats and finds no partner/API node in it.

## `real/` (the workflows behind the real clips)

Exports of the Comfy Cloud runs that made `examples/real/*.mp4`: see [`real/README.md`](real/README.md) and [`docs/REAL_RUN.md`](../docs/REAL_RUN.md).
