# v35: authored oblique hand

The middle of the cheek gesture now uses an authored oblique hand with overlapping fingers, rather than only projecting the same dorsal illustration. The original dorsal PNG is unchanged. Both paintings are separately editable in `assets/parts/v35/koma_hand_angle_v35.psd`; the full received PNG and its provenance are saved beside it.

The hand was materialized by the unchanged Library helper in existing Ubuntu-22.04 WSL. Windows Python failed on `os.setxattr`; WSL succeeded and verified `user.library-file-id` and version 0. The metadata-bearing source remains at `/home/koji/koma-v35-library-import/exec-402d1d9f-09fe-4fa9-a65f-a33bc599640c.png` on the same Dell. Its SHA256 is `7ec3d949672336d1e805c91566eac65052e7027479c031726ca47da7b060756f`.

`prepare_hand_v35.py` performs only similarity registration and antialiased resampling of the received image. Wrist and middle-tip anchors are recorded in `hand-source.json`. In the renderer, scanline silhouette correspondence moves the outline between the paintings and samples colour on that moving surface. This is one texture on one opaque hand layer, not two alpha-faded draw layers. The proximal wrist remains the accepted original. The angle amount is continuous and returns to the dorsal endpoint at rest and at the cheek. Existing depth projection is reduced where the oblique painting already contains foreshortening, preventing double thinning.

Validation:

- 187 tests passed, including a registered-contour/core-opacity/wrist-pinning test.
- Dedicated headless Chrome: eight expressions at both body extremes; happy movement and reset. One parallel verification run hit the reset's 10-second timeout; rerunning alone passed. The final report records the successful isolated run.
- Same input and camera as v34: 60 Hz physics, 30 fps output, 555 frames, 18.5 seconds for both videos. All timestamps unique and evenly spaced; all frames decoded. Both 1x video playback runs reported 555 total frames and 0 dropped.
- Native 1086 x 1448 rendering, unscaled 500 x 900 comparisons: 181 consecutive frames from 10 through 16 seconds. The six hand contact sheets cover every frame; four original-size comparisons are tracked, all 181 remain locally. Visual review found no new wrist separation, sudden material switch, transparent duplicate hand, or waist/face break. The strongest temporal changes were 10.9 and 14.767 seconds, during arm travel; they were inspected in the sequence.
- White/black/teal video panels retain the existing face, waist and hair rendering. PSD reparse matches its saved composite exactly. Both editable hand source layers remain independent of the arm/torso.

Limits: this is a two-angle illustration morph with shallow depth, not a complete 3D hand or individual articulated fingers. At intermediate angles internal finger lines soften as the registered paintings interpolate; the oblique painting has stronger contours than the dorsal one. Independent review is still appropriate for subjective naturalness. The refused shoulder redraw remains untouched. Missing knee/foot artwork and the two short hair crops without independent tail bending are unchanged limitations.

Reproduce with `capture_v35_cfr.mjs`, `native_review_v35.mjs`, `verify_v35_app.mjs`, `verify_video_v35_cfr.mjs` (set `CFR_COMPARISON=1` for comparison), `audit_native_v35.py`, and `export_psd_v35.py`. These use existing Python, Playwright, and a dedicated headless Chrome; no software installation is needed.
