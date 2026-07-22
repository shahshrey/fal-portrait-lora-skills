# Portrait Trainer Schema

Model ID: `fal-ai/flux-lora-portrait-trainer`

## Inputs

| Field | Type | Skill default | Notes |
|---|---|---|---|
| `images_data_url` | string | required | Uploaded flat ZIP URL |
| `trigger_phrase` | string | user supplied | Replaces `[trigger]` in captions |
| `learning_rate` | float | `0.00009` | Valid API range: 0.000001–0.001 |
| `steps` | integer | `2500` | Valid API range: 1–10000 |
| `multiresolution_training` | boolean | `true` | Preserve framing variety |
| `subject_crop` | boolean | `true` | Portrait-focused subject crops |
| `create_masks` | boolean | `false` | Enable only when explicitly requested |
| `data_archive_format` | string | inferred | Omit for uploaded ZIP |
| `resume_from_checkpoint` | string | omitted | Set only when resuming |

## Outputs

- `diffusers_lora_file`: trained `.safetensors` URL
- `config_file`: training configuration URL

## Caption contract

Each image must have a same-stem text file:

```text
subject_001.jpg
subject_001.txt
```

Caption example:

```text
[trigger], close-up portrait, wearing glasses, smiling outdoors.
```

Set `trigger_phrase` to the phrase users will include in generation prompts.
