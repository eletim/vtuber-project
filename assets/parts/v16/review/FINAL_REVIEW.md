# v16 independent mouth-pixel review

Geometry, texture, and actual encoded-video review: PASS within the tested scope.

- Reviewed all eight expressions at head tilt -8, 0, +8 degrees and mouth openings 0, .15, .20, .25, .35, .65, 1 (168 cases), plus .141, .160, .214 near the closure/blend boundaries (72 additional cases). Total: 240.
- The mouth keeps its authored oblique direction relative to the tilted face. Intermediate states no longer collapse toward a horizontal stripe.
- No reproduced detached dark corner flecks, doubled/ghosted contours, dark rectangular halos, or restoration slits in the checked final cases. The small connected corner curvature in tiny displeased openings is not detached/doubled and is not a blocker.
- All 240 mouth regions remain fully opaque (minimum alpha 255). All 48 closed/fully-open endpoint face images are pixel-identical to v15. Body rig, controls, performance, model manifest, and skinning hashes remain unchanged.
- The cached-helper optimization was checked separately. It changes only sparse centerline antialias samples, not lip geometry; the exact final frozen source was rerendered for all 240 retained cases.

Frozen runtime:
- expressions.js: 1e67114be41e7f0309d148428be96fa4e281f30c4bb8657e96fc66c7318f1d01
- renderer.js: d9e5a89872fbe719d110631b157a59b0361f4248875de652c52c3f555fa501e9

The v15 fault was reproduced in the actual supplied encoded video, especially frames 360 (12.000 s) and 390 (13.000 s). Its original global-Y mouth compression altered the local lip axis and crushed the dark authored corners. The opaque base and pre-encoding FBO evidence rule out transparent-black bleed and H.264 as the reproduced root cause.

Evidence is retained in before/, after/, threshold/, and encoded_examples/. Complete numeric scope and hashes are in FINAL_REVIEW.json. The reproducible scripts, including PNG-to-RGBA fixture export and exact-helper RGBA-to-PNG conversion, are in scripts/; follow scripts/RERUN_REVIEW.txt.

Method: actual runtime JavaScript RGBA helper plus shared body mesh, rendered offline with EGL/llvmpipe. This is not browser UI/E2E capture. The final encoded video was independently checked at the same original defect frames and 24 additional intermediate-opening frames across all eight expressions.


## Actual encoded-video signoff

- Final video SHA256: 395ba4940ae0dfc6a5a16d4f68acbfa9d44d73ba5ce47e67bb5949c43b14b3a8.
- Same-frame before/after comparisons at 6, 6.5, 7, 12, 12.5, and 13 seconds pass.
- Independently decoded 24 additional frames covering all eight expressions near mouth amounts .20, .35, and .65. All sampled mouth contours remain connected and correctly oriented; the reproduced old defects are absent. Exact frame numbers, timestamps, actual amplitudes, and head tilts are retained in encoded_examples/all8_actual_encoded_intermediate_states.json.
- Independently checked all 1,260 pose arrays for exact equality, mesh binary SHA equality, and timeline WAV SHA equality against the original v15 regeneration. Motion and audio were not reduced or removed.
- The video worker additionally reports full H.264 decode PASS and decoded audio correlation 0.9999623686. This is separate from the manual pixel review.

The signoff covers the controlled 240-case matrix and specified encoded samples, not an assertion that every pixel in every video frame was manually inspected.
