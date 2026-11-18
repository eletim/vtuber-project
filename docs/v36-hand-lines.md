# v36: transport finger creases before colour interpolation

The v35 hand morphed the outer contour, but the two paintings' interior creases occupied different positions. Averaging those samples produced two weak lines during the transition. v36 matches the creases and finger gaps inside each contour section before sampling colour.

The correspondence is monotonic, has fixed contour endpoints and limited local slope, and uses alpha, local ink contrast and luminance. A previous-section penalty and a longitudinal Gaussian filter make neighbouring sections agree. The first unregularized candidate produced small jagged strokes and was rejected after native-pixel review. The retained correspondence moves each matched feature to one interpolated position; it does not switch the whole texture, increase fade speed, or change layer opacity.

The wrist pin, outer-span interpolation, arm trajectory, v35 depth, head/chest response, weight movement and hair remain unchanged. The dorsal and oblique source PNGs are byte-identical to v35. The new PSD retains both editable paintings and updates its runtime reference preview; no shoulder artwork was modified.

Evidence is under `assets/parts/v36`: same-scenario v35/v36 CFR videos, 181 native frames from 10 to 16 seconds, native temporal audit/contact sheets, eight-expression extremes, and test logs. The focused visual intervals are 10.8–11.05, 11.6–11.8, 13.7–14.0 and 14.55–14.8 seconds, in addition to the full raise/lower sequence. The test fixture includes a deliberately displaced crease and requires one dark run, retained contrast, monotonic correspondence and an unchanged proximal wrist.

This remains a two-view illustration morph rather than a 3D anatomical hand. Small antialiasing/paint differences remain in the original-sized fingers; do not describe the result as perfect or general-purpose finger articulation. The shoulder redraw remains held, and no upload or push is part of this revision.
