# Visual QC Checklist

1. Run `scripts/qc_flags.py` and open `qc_flags.json`.
2. Use image vision to review every file in `contact_sheets/`.
3. Open every suspicious output and its original source at full resolution.
4. Manually recrop failures, record the crop in `manifest.json`, regenerate the
   relevant contact sheet, and verify the correction.

Automated face detection is advisory. A detection failure, small detected face,
or distant subject is not by itself a reason to discard a user-curated image.

## Reject

- [ ] Wrong subject / bystander cropped instead of target
- [ ] Face off-center at frame edge
- [ ] Eyes, forehead, or hair heavily clipped
- [ ] Torso-only / chin-only / no usable face
- [ ] Extreme low-angle selfie that hides identity
- [ ] Heavy blur / motion smear
- [ ] Near-duplicate burst (keep best 1–2)

Prefer correcting a crop over rejecting a valid source photo.

## Keep variety

- [ ] With and without glasses/sunglasses (if both exist)
- [ ] Multiple expressions and angles
- [ ] Indoor + outdoor lighting
- [ ] Different outfits

## Target mix

Aim for mostly head-and-shoulders. A few tighter close-ups are fine; avoid many zoomed-out full-body crops where the face is tiny.
