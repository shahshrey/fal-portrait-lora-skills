# FLUX LoRA Inference Schema

Model ID: `fal-ai/flux-lora` — FLUX.1 [dev] with LoRA support.
API reference: <https://fal.ai/models/fal-ai/flux-lora/api>

## Inputs

| Field | Type | API default | Skill default | Notes |
|---|---|---|---|---|
| `prompt` | string | required | required | Must contain the trigger phrase to apply the identity |
| `loras` | list of LoraWeight | `[]` | one entry | Multiple entries merge together |
| `image_size` | enum or object | `landscape_4_3` | `portrait_4_3` | Portraits are judged on faces, so default vertical |
| `num_inference_steps` | integer | `28` | `28` | |
| `guidance_scale` | float | `3.5` | `3.5` | Higher tracks the prompt more literally |
| `seed` | integer | random | omitted | Fix it to compare prompts or scales fairly |
| `num_images` | integer | `1` | `1` | |
| `output_format` | enum | `jpeg` | `jpeg` | `jpeg` or `png` |
| `enable_safety_checker` | boolean | `true` | left at API default | |
| `acceleration` | enum | `none` | `none` | `regular` trades quality for speed |
| `sync_mode` | boolean | `false` | unused | Returns a data URI and skips request history |

### LoraWeight

| Field | Type | Default | Notes |
|---|---|---|---|
| `path` | string | required | Public URL to `.safetensors` weights |
| `scale` | float | `1` | Identity strength; see below |

### `image_size` enum values

`square_hd`, `square`, `portrait_4_3`, `portrait_16_9`, `landscape_4_3`,
`landscape_16_9`. For a custom size pass an object:

```json
{ "image_size": { "width": 1280, "height": 720 } }
```

## Outputs

| Field | Notes |
|---|---|
| `images` | List of `{ url, width, height, content_type }` |
| `timings` | Server-side timing breakdown |
| `seed` | The seed used, whether passed or generated |
| `has_nsfw_concepts` | One boolean per image |
| `prompt` | The prompt as used |

Image URLs on fal media hosts are not guaranteed to persist. Download anything
worth keeping; `generate_lora_images.py` does this automatically.

## LoRA scale

`scale` multiplies the adapter before it merges into the base model.

| Range | Effect |
|---|---|
| `0.6–0.8` | Weaker identity, more prompt freedom and style range |
| `0.9–1.1` | Usual working range for a well-trained portrait LoRA |
| `1.2–1.5` | Stronger identity; artifacts, texture crunch, and pose lock-in appear |

If likeness only arrives above ~1.2, the LoRA is undertrained. If faces look
plastic or every pose collapses toward the training set at `1.0`, it is
overtrained — retrain with fewer steps rather than fighting it at inference.

## Prompting a portrait LoRA

The trigger phrase carries the identity, so it must appear in the prompt. A
prompt without it renders a generic person even with the LoRA loaded.

```text
himanibhavsar, close-up portrait, soft window light, navy blazer, sharp focus
```

Describe what should change — framing, light, wardrobe, setting, expression —
and leave the face to the LoRA. Do not describe the subject's features; that
competes with the trained identity.
