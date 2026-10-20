# PSD v8 sleeves, arms, and hands artwork

## Candidate

`assets/parts/v8/koma_sleeves_arms_hands_cleaned_v8.psd` builds on the
neck/clothing-cleaned candidate. It contains 63 editable layers. The initial
RGBA composite is pixel-identical to its input; the approved source assets
remain unchanged. This implements the sleeves/arms/hands portion of Issue #15,
not the separate integration, release audit, or Cubism modelling work.

The new artwork is in `arms_painted_underlayer_v8.png` and
`inner_cuffs_painted_underlayer_v8.png`. These are localized painted assets,
not a regenerated character. The adjacent candidate PNG shows the default,
sleeves hidden/moved, hands hidden/moved, and both groups hidden. The JSON
records paint checksums and scene measurements.

## Artwork and ownership

- Replaced the straight placeholder arms with painted tapered arms, elbow
  shading, forearms and wrist overlaps beneath the approved sleeves.
- Extracted the complete visible sleeve and hand artwork using explicit
  boundaries in `config/koma_sleeves_v8.json`. Removed in-bound duplicates
  from inherited underpainting and body layers, including stray cuff/ribbon
  fragments that previously remained behind when a part moved.
- Kept the approved finger poses and hand outlines. Hand hiding removes the
  palm and fingers; it does not reveal another fixed hand.
- Added small shaded inner-cuff overlaps behind the hands. Move/hide each
  `*_inner_cuff` with its `*_arm_sleeve`.
- Kept `*_torso_join` separate from `*_arm_wrist_join`, so clothing behind a
  sleeve stays fixed when the arm and hand are moved together. For limb motion,
  move the corresponding hand and arm/wrist layers together. The existing
  exposed shoulder is the attachment point.
- Preserved all out-of-bound source pixels and all expression layers. Original
  part records with remaining out-of-bound pixels have `.outside_ownership`
  names; these are residual coverage, not the movable part controls.

## Verification and visual review

Run:

```sh
python3 scripts/validate_approved_assets.py
python3 scripts/clean_sleeves_arms_hands_v8.py
python3 tests/test_clean_sleeves_arms_hands_v8.py
```

The regression checks the complete PSD round trip, deterministic reproduction,
unchanged initial pose and four expression states, independent left/right
ownership, continuous painted forearm coverage, absence of fixed palms, and
agreement between hidden artwork and pixels vacated by movement.

The comparison was inspected after correcting floating cloth fragments and
shoulder boundaries. Sleeve hiding now reveals shaped arms and clothing joins;
hand hiding exposes cuff interiors without duplicate fingers. Original wrist
contact shadows are retained with the hands. The recorded movement check is
8 pixels outward and 4 pixels upward, not a claim of arbitrary deformation.
Removing an outer sleeve or hand legitimately exposes transparent background;
a zero-hole count across the old silhouette would incorrectly require ghosts.
The new artwork still requires the project's separate integration/art review
and Cubism mesh testing before release.

## Painting provenance

Used the built-in imagegen tool with a crop of the existing candidate spanning
`(0, 470, 1086, 1448)`. No head or whole-character generation was requested.
Outputs were resized to that crop's coordinate system and restricted to the
consumed, fully occluded part regions; their generated alpha was preserved.
The checked-in paint PNGs are the reproducible builder inputs. Generation is
not required to rebuild the PSD.

Arm prompt: “Keep the exact crop, positions, pose, hands, torso and style.
Remove only the two large white hanging bell sleeves and their arm ribbons,
revealing naturally drawn bare arms from existing shoulders to existing wrists
and hands. Paint tapered upper arms, subtle elbows and forearms, warm pale
skin, delicate outline and matching cel shading. Reconstruct the small clothing
areas behind the sleeves. Transparent outside the figure; no new character.”

Cuff prompt: “Keep the exact crop, pose, white tiered sleeves, torso and all
clothing at identical coordinates. Remove only both visible hands and wrists.
Finish the open sleeve ends with curved white inner-cuff fabric, warm grey/pink
shaded hollow interiors and thin hem lines. Do not extend sleeves downward or
add arms/hands. Transparent where hands were; no whole-character regeneration.”
