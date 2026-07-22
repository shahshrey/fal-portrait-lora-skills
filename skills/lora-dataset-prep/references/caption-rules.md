# Caption Rules

## Goal

Bind identity to the portrait trainer's `[trigger]` placeholder; put variable
attributes in the caption so the model does not bake them into the person.

## Format

```
[trigger], {shot type}, {clothing / accessories}. {pose / expression}. {setting / lighting}.
```

Example:

```
[trigger], portrait, wearing a blue suit and pink tie, smiling at the camera. Plain white studio background. Soft even lighting.
```

## Do

- Start every portrait-trainer caption with exact lowercase `[trigger]`
- Describe clothing, glasses/sunglasses, expression, camera angle, background, lighting
- Keep one caption per image, matching filename stem (`subject_001.jpg` ↔ `subject_001.txt`)
- Prefer concrete nouns over mood fluff

## Don't

- Use one identical caption for every image
- Lead with long facial identity essays (skin tone essays, age guesses)
- Include "the image is a portrait of a young man…" boilerplate
- Put the literal trigger phrase in portrait-trainer captions; pass it separately
  as `trigger_phrase` so fal replaces `[trigger]`

## Fallback

If captioning fails, use:

```
[trigger], portrait photo
```

Retry descriptive captions when possible.
