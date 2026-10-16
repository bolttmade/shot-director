#!/usr/bin/env python
"""Generate the ComfyUI API-format workflows in workflows/ (+ a .meta.json describing their inputs).

STATUS: UNTESTED. There is no GPU on the dev box. The graphs were assembled by hand from
  * Lightricks/ComfyUI-LTXVideo  example_workflows/2.0/LTX-2_I2V_Full_wLora.json  (subgraph flattened)
  * fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA  (the multiple-angles ComfyUI workflow JSON)
and from the node definitions in ComfyUI core / ComfyUI-LTXVideo. Widget names for nodes whose
UI export stores only positional `widgets_values` were inferred; verify in ComfyUI before first use.

    python scripts/build_workflows.py
"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "workflows"


def node(class_type: str, title: str | None = None, **inputs):
    n = {"class_type": class_type, "inputs": inputs}
    if title:
        n["_meta"] = {"title": title}
    return n


def ltx2_i2v_camera() -> tuple[dict, dict]:
    ckpt = "ltx-2-19b-dev.safetensors"
    cam = "ltx-2-19b-lora-camera-control-dolly-in.safetensors"
    g = {
        "1": node("CheckpointLoaderSimple", "LTX-2 checkpoint", ckpt_name=ckpt),
        "2": node("LTXVAudioVAELoader", "Audio VAE", ckpt_name=ckpt),
        "3": node("LTXVGemmaCLIPModelLoader", "Gemma text encoder", gemma_path="gemma-3-12b-it-qat-q4_0-unquantized/model-00001-of-00005.safetensors", ltxv_path=ckpt, max_length=1024),
        "4": node("LoadImage", "INPUT: first frame", image="input.png"),
        "5": node("LoraLoaderModelOnly", "Camera LoRA (stage 1)", model=["1", 0], lora_name=cam, strength_model=1.0),
        "6": node("LoraLoaderModelOnly", "Distilled LoRA 0.6", model=["1", 0], lora_name="ltx-2-19b-distilled-lora-384.safetensors", strength_model=0.6),
        "7": node("LoraLoaderModelOnly", "Camera LoRA (stage 2)", model=["6", 0], lora_name=cam, strength_model=1.0),
        "8": node("CLIPTextEncode", "INPUT: prompt", clip=["3", 0], text="The camera dollies in smoothly."),
        "9": node("CLIPTextEncode", "INPUT: negative", clip=["3", 0], text="blurry, low quality, still frame, watermark, overlay, titles, subtitles"),
        "10": node("LTXVConditioning", frame_rate=24.0, positive=["8", 0], negative=["9", 0]),
        "11": node("ImageScaleBy", "half-res for stage 1", image=["12", 0], upscale_method="bicubic", scale_by=0.5),
        "12": node("EmptyImage", "INPUT: output size (multiples of 64)", width=1280, height=704, batch_size=1, color=0),
        "13": node("GetImageSize", image=["11", 0]),
        "14": node("EmptyLTXVLatentVideo", width=["13", 0], height=["13", 1], length=["20", 0], batch_size=1),
        "15": node("ResizeImagesByLongerEdge", images=["4", 0], longer_edge=1536),
        "16": node("LTXVPreprocess", image=["15", 0], img_compression=33),
        "17": node("LTXVImgToVideoInplace", "first frame (stage 1)", vae=["1", 2], image=["16", 0], latent=["14", 0], strength=0.6, bypass=False),
        "18": node("LTXVEmptyLatentAudio", audio_vae=["2", 0], frames_number=["20", 0], frame_rate=24, batch_size=1),
        "19": node("LTXVConcatAVLatent", video_latent=["17", 0], audio_latent=["18", 0]),
        "20": node("PrimitiveInt", "INPUT: frame count (8n+1)", value=121),
        "21": node("LTXVScheduler", steps=20, max_shift=2.05, base_shift=0.95, stretch=True, terminal=0.1, latent=["19", 0]),
        "22": node("CFGGuider", "INPUT: cfg (stage 1)", model=["5", 0], positive=["10", 0], negative=["10", 1], cfg=4.0),
        "23": node("KSamplerSelect", sampler_name="euler"),
        "24": node("RandomNoise", "INPUT: seed (stage 1)", noise_seed=42),
        "25": node("SamplerCustomAdvanced", noise=["24", 0], guider=["22", 0], sampler=["23", 0], sigmas=["21", 0], latent_image=["19", 0]),
        "26": node("LTXVSeparateAVLatent", av_latent=["25", 1]),
        "27": node("LTXVLatentUpsampler", samples=["26", 0], upscale_model=["28", 0], vae=["1", 2]),
        "28": node("LatentUpscaleModelLoader", model_name="ltx-2-spatial-upscaler-x2-1.0.safetensors"),
        "29": node("LTXVImgToVideoInplace", "first frame (stage 2)", vae=["1", 2], image=["16", 0], latent=["27", 0], strength=1.0, bypass=False),
        "30": node("LTXVConcatAVLatent", video_latent=["29", 0], audio_latent=["26", 1]),
        "31": node("ManualSigmas", sigmas="0.909375, 0.725, 0.421875, 0.0"),
        "32": node("CFGGuider", "cfg 1 (stage 2, distilled)", model=["7", 0], positive=["10", 0], negative=["10", 1], cfg=1.0),
        "33": node("RandomNoise", "seed (stage 2)", noise_seed=420),
        "34": node("SamplerCustomAdvanced", noise=["33", 0], guider=["32", 0], sampler=["35", 0], sigmas=["31", 0], latent_image=["30", 0]),
        "35": node("KSamplerSelect", sampler_name="euler"),
        "36": node("LTXVSeparateAVLatent", av_latent=["34", 1]),
        "37": node("LTXVSpatioTemporalTiledVAEDecode", vae=["1", 2], latents=["36", 0], spatial_tiles=4, spatial_overlap=4, temporal_tile_length=16, temporal_overlap=4, last_frame_fix=False, working_device="auto", working_dtype="auto"),
        "38": node("LTXVAudioVAEDecode", samples=["36", 1], audio_vae=["2", 0]),
        "39": node("CreateVideo", images=["37", 0], audio=["38", 0], fps=24.0),
        "40": node("SaveVideo", "OUTPUT", video=["39", 0], filename_prefix="video/shot-director", format="auto", codec="auto"),
    }
    meta = {
        "name": "ltx2_i2v_camera",
        "status": "UNTESTED (no GPU on the dev box). Assembled from the official LTX-2_I2V_Full_wLora example; see workflows/README.md",
        "engine": "open-weights",
        "core_video_model": "LTX-2 19B (Lightricks)",
        "output_node": "40",
        "output_kind": "video",
        "inputs": {
            "image": [["4", "image"]],
            "prompt": [["8", "text"]],
            "negative": [["9", "text"]],
            "seed": [["24", "noise_seed"], ["33", "noise_seed"]],
            "width": [["12", "width"]],
            "height": [["12", "height"]],
            "frames": [["20", "value"]],
            "fps": [["10", "frame_rate"], ["18", "frame_rate"], ["39", "fps"]],
            "lora_name": [["5", "lora_name"], ["7", "lora_name"]],
            "lora_strength": [["5", "strength_model"], ["7", "strength_model"]],
            "cfg": [["22", "cfg"]],
        },
        "lora_nodes": ["5", "7"],
        "rules": {"frames": "8n+1 (121 = 5 s @ 24 fps)", "size": "width/height divisible by 64", "resolutions": {"480p": [768, 448], "720p": [1280, 704]}},
    }
    return g, meta


def qwen_edit_angle() -> tuple[dict, dict]:
    g = {
        "108": node("UNETLoader", "Qwen-Image-Edit-2511", unet_name="qwen_image_edit_2511_bf16.safetensors", weight_dtype="default"),
        "109": node("LoraLoaderModelOnly", "Multiple-Angles LoRA", model=["108", 0], lora_name="qwen-image-edit-2511-multiple-angles-lora.safetensors", strength_model=0.9),
        "102": node("LoraLoaderModelOnly", "Lightning 4-step LoRA", model=["109", 0], lora_name="Qwen-Image-Edit-2511-Lightning-4steps-V1.0-bf16.safetensors", strength_model=1.0),
        "94": node("ModelSamplingAuraFlow", model=["102", 0], shift=3.1),
        "98": node("CFGNorm", model=["94", 0], strength=1.0),
        "93": node("CLIPLoader", clip_name="qwen_2.5_vl_7b_fp8_scaled.safetensors", type="qwen_image", device="default"),
        "95": node("VAELoader", vae_name="qwen_image_vae.safetensors"),
        "41": node("LoadImage", "INPUT: still", image="input.png"),
        "107": node("FluxKontextImageScale", image=["41", 0]),
        "112": node("TextEncodeQwenImageEditPlus", "INPUT: angle prompt", clip=["93", 0], prompt="<sks> front view eye-level shot medium shot", vae=["95", 0], image1=["107", 0]),
        "100": node("TextEncodeQwenImageEditPlus", "negative (empty)", clip=["93", 0], prompt="", vae=["95", 0], image1=["107", 0]),
        "97": node("FluxKontextMultiReferenceLatentMethod", conditioning=["112", 0], reference_latents_method="index_timestep_zero"),
        "96": node("FluxKontextMultiReferenceLatentMethod", conditioning=["100", 0], reference_latents_method="index_timestep_zero"),
        "105": node("VAEEncode", pixels=["107", 0], vae=["95", 0]),
        "106": node("KSampler", "INPUT: seed", model=["98", 0], positive=["97", 0], negative=["96", 0], latent_image=["105", 0], seed=42, steps=4, cfg=1.0, sampler_name="euler", scheduler="simple", denoise=1.0),
        "103": node("VAEDecode", samples=["106", 0], vae=["95", 0]),
        "9": node("SaveImage", "OUTPUT", images=["103", 0], filename_prefix="shot-director/angle"),
    }
    meta = {
        "name": "qwen_edit_angle",
        "status": "UNTESTED here; derived from the LoRA author's own ComfyUI workflow (fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA)",
        "engine": "open-weights",
        "output_node": "9",
        "output_kind": "image",
        "inputs": {"image": [["41", "image"]], "prompt": [["112", "prompt"]], "seed": [["106", "seed"]], "lora_strength": [["109", "strength_model"]]},
        "lora_nodes": [],
        "rules": {"prompt": "<sks> [azimuth] [elevation] [distance], see app/angles.py", "grid": "8 azimuths x 4 elevations x 3 distances"},
    }
    return g, meta


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for fn in (ltx2_i2v_camera, qwen_edit_angle):
        g, meta = fn()
        (OUT / f"{meta['name']}.json").write_text(json.dumps(g, indent=2) + "\n")
        (OUT / f"{meta['name']}.meta.json").write_text(json.dumps(meta, indent=2) + "\n")
        print("wrote", meta["name"], len(g), "nodes")


if __name__ == "__main__":
    main()
