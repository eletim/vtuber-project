# v48: intermediate upper-lash correspondence

## Cause and isolation
The v47 intermediate result is rejected. Frame 012 (0.4s), 147 (4.9s), 282 (9.4s) and 327 (10.9s) showed a diluted contour above the dark upper lash. This is not a harmless zoom-only detail.

A dedicated headless diagnosis removed the fixed foreground hair mask and then each of the two registered colour sources separately. Removing the mask did not remove the duplicate contour; removing the open-image contribution did. The neutral base itself was inspected and has no baked eyes, so exposure of an old eye through alpha was not the cause.

The old map matched only the bottom of the upper lash. Its entire upper strip was stretched from an outer skin anchor, so the ink at the upper edge of the open drawing and the ink at the upper edge of the closed drawing landed at different positions. Mixing their colours made the displaced open line gray. Premultiplied alpha alone could not fix that geometric mismatch.

## Correction
Measure the upper ink extent of each authored source, retain its independently registered lower edge, and interpolate both extents. The source strips are mapped between those two shared boundaries before colour interpolation. The outer skin maps to the shared upper boundary. This preserves one ink band instead of two separated colour contributions. Iris translation, eyelid aperture, expression openness normalization, native endpoints, and rigid head roll are unchanged.

## Scope and evidence
- All 8 expressions x 5 static opening conditions are generated in `audit/` against v45 at the same pose/camera. Full open and full closed endpoints remain exact (all channel differences zero).
- All 8 half-open face images were inspected at their original face-camera size. New 30fps v47/v48 comparison and full-body samples preserve the 360-frame input sequence.
- Inspect the four regression frames above and adjacent frames in `review/frames/` (retained locally, not included in Git). The saved videos and audit images are included in the checkpoint.
- A regression test uses two synthetic authored upper-lash bands with different positions and verifies an opaque single intermediate band, rather than accepting exact endpoints alone.
- Existing PSD and all source image bytes are unchanged; `psd-consistency.json` identifies the v47 source PSD used by the runtime. No additional material generation was performed.
- `ui-review/report.json` and `final-tests.json` retain the actual playback/sync and final regression results.

## Limits
Independent visual acceptance is still pending. Original hair/lash intersections and fine native raster detail are not promised to be flawless. The original big_smile closed-eye drawing remains an explicit exception to moving iris controls. No shoulder generation, external upload, push, installation or user-screen operation was performed.
