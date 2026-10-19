# PSD v8 neck and clothing artwork cleanup

## Result

The neck and clothing artwork task is **completed as a cleaned PSD candidate**
at `assets/parts/v8/koma_neck_clothing_cleaned_v8.psd`. The approved source and
the preceding hair/head candidate remain unchanged.

The 53-layer candidate retains the approved visible costume pixel-for-pixel.
Its two new painted underlayers and replaced vest-movement reveal complete the
occluded neck, collar, blouse, vest-edge, corset, belt, and waist artwork. They
are separate editable layers rather than approximate white/gray fill patches.

## Artwork changes

1. The 166,699-pixel white/gray vest reveal is replaced with continuous
   pin-tucked blouse, shaded corset, belt, and waist artwork in the approved
   brown, cream, and orange palette.
2. A fixed neck/collar underlayer supplies painted skin, ruffle, linework, and
   shading when the neck part is hidden or displaced.
3. A fixed torso underlayer supplies continuous fabric beneath the blouse,
   vest, and waist parts during modest translation, without leaving the
   duplicated visible costume in their vacated silhouettes.
4. The default candidate remains pixel-identical to the hair/head-cleaned
   input: RGB difference 0 and alpha difference 0.

The painted source is stored at
`assets/parts/v8/neck_clothing_underpainting_v8.png`. It was produced as a
precise edit of the approved illustration, then constrained to hidden
underpainting and reveal layers. It does not replace or redesign the approved
visible costume.

## Reproduction and review

Run:

```bash
python3 scripts/validate_approved_assets.py
python3 scripts/clean_neck_clothing_v8.py
python3 tests/test_clean_neck_clothing_v8.py
```

`assets/parts/v8/neck_clothing_comparison_v8.png` contains the approved pose
and full-resolution-derived hidden and displaced neck, vest, blouse, and waist
scenes. `assets/parts/v8/neck_clothing_audit_v8.json` records the immutable
painted-source digest, changed-pixel provenance, default-pose comparison, lost
alpha checks, and vacated-silhouette checks. Every displaced part must reveal
the same artwork as its hidden underpainting and must leave no transparent
holes.

This is artwork preparation, not Cubism rigging. It does not claim that the
candidate is already a rigged or Cubism-ready model.
