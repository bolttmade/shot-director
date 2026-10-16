# Models, downloads and licences

Weights are **never bundled or redistributed** by this repo. Check each licence yourself before use; the notes below are a summary read on 2026-10-16, not legal advice.

## Open-weights engine (`open`, and the same graphs on `cloud`)

### Video: `workflows/ltx2_i2v_camera.json` (UNTESTED)

| File (as named in the graph) | What | Source | Licence |
|---|---|---|---|
| `ltx-2-19b-dev.safetensors` | LTX-2 19B checkpoint (video + audio VAE) | [Lightricks/LTX-2](https://huggingface.co/Lightricks/LTX-2) | LTX-2 Community License (free for orgs under US$10M revenue; use restrictions; not an OSI licence) |
| `ltx-2-19b-distilled-lora-384.safetensors` | distilled LoRA | same repo | same |
| `ltx-2-spatial-upscaler-x2-1.0.safetensors` | x2 spatial latent upscaler | same repo | same |
| `gemma-3-12b-it-qat-q4_0-unquantized/…` | text encoder | Google Gemma 3 12B (QAT) on Hugging Face | Gemma Terms of Use |
| `ltx-2-19b-lora-camera-control-<move>.safetensors` | official camera-motion LoRAs (dolly-in/out/left/right, jib-up/down, static) | `Lightricks/LTX-2-19b-LoRA-Camera-Control-<Move>` | base LTX-2 licence |

Nodes: ComfyUI core LTXV nodes and [Lightricks/ComfyUI-LTXVideo](https://github.com/Lightricks/ComfyUI-LTXVideo) (`LTXVGemmaCLIPModelLoader`, `LTXVAudioVAELoader`, …). Which move names have a published LoRA is listed per preset (`presets/*.json`, `lora.source`); moves without one run on prompt alone.

### Angles: `workflows/qwen_edit_angle.json` (UNTESTED)

| File | What | Source | Licence |
|---|---|---|---|
| `qwen_image_edit_2511_bf16.safetensors` | Qwen-Image-Edit-2511 | Comfy-Org / Qwen on Hugging Face | Apache-2.0 (verify on the model card) |
| `qwen-image-edit-2511-multiple-angles-lora.safetensors` | 96-pose camera-angle LoRA, trained on Gaussian-splat renders | [fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA](https://huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA) | Apache-2.0 per its model card |
| `Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors` | 4-step Lightning LoRA | Lightx2v on Hugging Face | check model card |
| `qwen_2.5_vl_7b_fp8_scaled.safetensors`, `qwen_image_vae.safetensors` | text encoder, VAE | Comfy-Org repackaged files | Apache-2.0 (verify) |

Prompt grammar: `<sks> <azimuth> <elevation> <distance>`, for example `<sks> front-right quarter view elevated shot close-up`. 8 azimuths x 4 elevations (`low-angle`, `eye-level`, `elevated`, `high-angle`) x 3 distances.

### Hardware

**Unverified.** LTX-2 19B and Qwen-Image-Edit (about 20B) are large. Expect to need a 24 GB+ NVIDIA GPU or fp8/GGUF variants, plus lots of disk (tens of GB). Nobody has run these graphs on the machine this repo was built on.

### Open Weights Only check

`python scripts/check_open_weights.py` fails if any workflow node looks like a partner/API node (Kling, OpenAI, Veo, BFL API, MiniMax, …) and prints every node type for review. It is static: it cannot prove which weights a server holds. Shipped graphs use only ComfyUI core nodes and the Lightricks LTXV nodes.

## Router engine (`router`): partner models, credits

`minimax/minimax-h3` (default), `byteplus/dreamina-seedance-2-5-260628`, `xai/grok-imagine-video-1.5-lite`, `bfl/flux-3-image` (stills). These are hosted partner models: **not** eligible for the Open Weights Only category. `ltx/ltx-2-5-*` on Router accepts text only, so it is never used for image-to-video.

## Demo engine

No model. See `examples/CREDITS.md`.
