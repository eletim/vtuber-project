# v37: head and hair follow

Baseline: v36 a1d0cdb098182eaf5c6495d7a262500723066f2a.

The neck now filters subsequent authored head commands without changing the initial head pose. Head inertia responds to the actual chest and pelvis rotations. Pelvis response leads the chest slightly more; shift and bounce amplitudes are unchanged. Each hair spring measures acceleration at its own pinned root instead of sharing the centre-head sensor. Existing strand limits and damping are retained. No hand, shoulder, artwork, face, mouth, waist geometry or texture changes.

## Comparison conditions

Both versions receive identical input at 60 Hz and are sampled at 30 fps, 555 frames / 18.5 seconds. Diagnostic videos retain the original stop-and-settle sequence. Separate acting videos use performance-sequence.js on BOTH versions: earlier head preparation, overlapping happy settling/hand preparation, accepted soft-smile/blink sprites and residual loading during lowering. This helper is exported and used by the capture; it is not automatically selected by the application UI. Head orientation is not independent pupil gaze. Do not attribute the new acting input to rig-only improvement.

## Validation

191 tests pass, including initial-pose preservation, continuous head response and separate root acceleration. Four MP4s decode all 555 frames with exact timestamps. Dedicated headless Chrome 1x playback reports 555 frames and zero drops for each. Live app happy gesture/reset and eight expressions at both extremes pass without page errors.

187 unscaled paired renders cover every 30 fps frame in 2.2–4.8, 8.6–10.2, 11.6–12.3 and 15.4–16.6 seconds. All contact sheets were inspected; selected original pairs at 3.2, 3.6 and 9.6 seconds were viewed separately. Contact inspection shows no new obvious waist split, face damage or detached parts. This is not a claim that every raw frame was individually inspected at native scale. Playback was measured in headless Chrome; visual judgement used decoded images and contact sequences, not a human watching a desktop player.

Maximum diagnostic shift stays 43.165 px and bounce 4.945 px in both versions. New root forcing changes outer-hair peaks (left 34.217→29.972, right 38→36.538 px), although amplitude parameters were not reduced. The most visible difference is head return after the happy phrase; pelvis/chest timing improvement remains subtle at full-body scale. Existing hand side/material correspondence is unchanged.

## Remaining limits

Shoulder boundary/redraw remains held; no retry or alternate edit was performed. No knee/foot artwork exists, so contact and convincing full-leg loading cannot be established. Two short cropped strands (side_right_front and side_left_outer) still follow the head without independent tip bending because their crop ends before the effective pinned root. No new facial art, brow rig or pupil gaze. Small edge/matte imperfections and the 2.5D illustration limits remain; this is a review candidate, not a claim of perfect naturalness.

PSD assets/parts/v36/koma_hand_angle_v36.psd remains the correct unchanged artwork source; no duplicate PSD was generated. No external upload, push, authentication change, installation, main merge or user-screen operation.
