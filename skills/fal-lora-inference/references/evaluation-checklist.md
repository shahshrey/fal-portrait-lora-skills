# LoRA Evaluation Checklist

How to tell whether a freshly trained portrait LoRA is usable, and what to
change when it is not.

## Run a scale sweep first

Before judging anything, generate one fixed-seed prompt across several scales:

```bash
--prompt "TRIGGER, close-up portrait, soft window light" \
--lora-scale 0.7 0.9 1.1 1.3 --seed 12345
```

A fixed seed keeps composition constant so scale is the only variable.

## Then vary the prompt, not the scale

Once a working scale is found, hold it and push variety: shot distance,
lighting, wardrobe, setting, expression. A LoRA that only works on the framing
it was trained on is overfit, not finished.

## What to look for

| Check | Passing | Failing |
|---|---|---|
| Likeness | Recognizable at `0.9–1.1` | Only recognizable above `1.2` |
| Skin | Pores and texture survive | Waxy, plastic, or over-smoothed |
| Eyes | Symmetric, consistent color | Drifting color, mismatched shape |
| Prompt control | Wardrobe and setting obey the prompt | Prompt ignored; training outfits reappear |
| Pose variety | Distinct poses across seeds | Every seed converges on one pose |
| Backgrounds | Match the prompt | Training-set backgrounds bleed through |
| Text and hands | Base-model quality | Noticeably worse than base FLUX |

## Reading failures

| Symptom | Likely cause | Fix |
|---|---|---|
| Weak likeness at any scale | Undertrained, or too few distinct images | More steps, or more varied sources |
| Training outfits and backgrounds persist | Overtrained, or captions too sparse | Fewer steps; more descriptive captions |
| Identity leaks onto other people in frame | Trigger phrase too generic | Retrain with a rarer trigger token |
| Faces good, bodies distorted | Dataset was face crops only | Add some wider shots to the dataset |
| Prompt has no effect | Trigger missing, or scale far too high | Confirm the trigger; drop the scale |

Captions decide how much the prompt can steer: whatever stays undescribed
across the dataset gets absorbed into the trigger. That is why
`lora-dataset-prep` writes descriptive per-image captions.

## Reviewing the output

Open `contact_sheet.jpg` and inspect it as an image, then open individual files
at full resolution before judging skin, eyes, and hands. A downscaled grid hides
exactly the artifacts that matter.
