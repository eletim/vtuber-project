# PSD v8 hair and head artwork cleanup

## Result

The hair and head artwork task is **completed as a cleaned PSD candidate** at
`assets/parts/v8/koma_hair_head_cleaned_v8.psd`. The approved v8 source remains
unchanged.

The candidate keeps the 49 source layers plus one fixed boundary-underpainting
layer, and its initial composite is pixel-for-pixel identical to the approved
v8 appearance. The repaired artwork comes only from the approved v8 rendering
and the illustrated v7 underlayers; no flat fill, blur, or whole-character
regeneration is used.

## Artwork changes

1. The illustrated scalp/hairline reveal is placed beneath the movable bangs
   and side hair so it remains present when the bangs are hidden or displaced.
2. The broad v7 scalp reveal is clipped to the fully occluded bang silhouette,
   cleaning its boundary without covering crown or facial detail.
3. Saturated yellow/green segmentation remnants at the bangs, side-hair,
   crown, and accessory underpaint boundaries are repainted with corresponding
   approved top-layer pixels.
4. Redundant extraction overlap is removed from each movable hair group;
   copied shoulder and garment pixels are retained as real approved artwork in
   a fixed underpainting instead of travelling with the side hair.
5. Fully occluded deep-hair pixels beneath the bangs, side hair, rear hair,
   crown, and accessory are replaced with detailed painted pixels from the
   approved v8 appearance or the corresponding v7 hidden state.
6. Side-hair and accessory reveal states no longer expose the bright green and
   yellow boundary remnants visible in the v7 work layer.
7. Side and rear hair use their v7 hidden-state underdrawing rather than a copy
   of the visible hair. The remaining v7 marker-colored boundary pixels are
   replaced with nearby painted pixels from the same illustrated hair base.

## Reproduction and review

Run:

```bash
python3 scripts/validate_approved_assets.py
python3 scripts/clean_hair_head_v8.py
python3 tests/test_clean_hair_head_v8.py
```

`assets/parts/v8/hair_head_comparison_v8.png` shows the approved pose plus
hidden and displaced bangs, side-hair, crown, rear-hair, and accessory states.
`assets/parts/v8/hair_head_audit_v8.json` records pixel provenance, the exact
initial comparison, and lost-alpha checks for every review state.
The audit also requires side/rear hidden states to differ from the default and
requires every vacated displaced-silhouette pixel to match the hidden
underdrawing rather than the original visible silhouette.

This is artwork preparation, not Cubism rigging. It does not claim that the
candidate is already a rigged or Cubism-ready model.
