# Reproduce the v19 independent-layer preview

This is an offline OpenGL re-render, not a browser or application recording. It uses the actual exported runtime mesh arrays, ordered body layer plan, expression transitions, and mouth pixel helper. It does not use the earlier single whole-body texture/mesh path.

Requirements already used in the task environment: Python 3 with NumPy and Pillow, Node.js, ffmpeg/ffprobe with libx264/AAC, Mesa EGL/OpenGL shared libraries, Noto Sans CJK fonts. No paid service or new voice synthesis is used.

Copy these scripts into a new writable output directory (do not overwrite delivered previews):

- prepare_source.py
- generate_layered_frames.mjs
- measure_isolation.py
- layered_egl.py
- test_egl.py
- test_layer_alpha.py
- render_v19.py
- verify_video.py
- check_neutral_edges.py
- render_face_checks.py
- generate_arm_extremes.mjs
- render_arm_extremes.py
- review_shoulders.py

Run from that directory after the runtime/model/art revision is frozen:

```sh
python prepare_source.py --source /path/to/vtuber-project
node generate_layered_frames.mjs
OPENBLAS_NUM_THREADS=1 python measure_isolation.py
OPENBLAS_NUM_THREADS=1 python test_layer_alpha.py
OPENBLAS_NUM_THREADS=1 python check_neutral_edges.py --supersample 2
KOMA_OUTPUT_WIDTH=652 KOMA_OUTPUT_HEIGHT=869 OPENBLAS_NUM_THREADS=1 python check_neutral_edges.py --supersample 2
LP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 python render_v19.py --frames-only
node generate_arm_extremes.mjs
LP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 python render_arm_extremes.py
LP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 python render_face_checks.py
python review_shoulders.py
```

Inspect the diagnostic sheet, all lossless raw avatars, black/white join sheet, torso-only invariance and foreground visibility masks before encoding. If those pass:

```sh
LP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 python render_v19.py
OPENBLAS_NUM_THREADS=1 python verify_video.py
```

Outputs are written next to the scripts. The source snapshot is immutable for a render. Retain source-provenance.json with output hashes, exact manifest ordering, independent role arrays, and the matching repository/artwork revision. If source changes, create a new output directory/snapshot rather than claiming that an old render reflects it.

## Timeline and evidence

- 0–5 s: left arm only, torso/head/skirt fixed.
- 5–10 s: right arm only, torso/head/skirt fixed.
- 10–16 s: skirt only, waist anchored and other parts fixed.
- 16–18 s: resting pose.
- 18–48 s: natural combined motion, eight expressions, then settle.

Each isolated scene initializes a neutral rig and then evaluates every chronological 1/30 s step. The natural section uses one continuously stepped motion controller and rig. The original 8.1707-second VOICEVOX sample is reused in full at 18.5, 28.5, and 38.5 s; no new dialogue. The art coverage limit controls actual skirt excursion and must not be raised merely to make the preview more dramatic.

The synthetic alpha test exercises actual crop/discard, source-over and head-FBO draw paths. The torso check compares lossless RGBA before H.264, with foreground masks allowing only real cover/reveal. The encoded frames and full decode/audio checks are separate. PSD semantic ownership and authored reveal coverage still require independent artwork inspection; passing mesh tests alone is insufficient.

## Alpha sampling parity

The final model must select `bodySampling: "coverage-2x"`. The generator imports the actual `bodySamplingPlan` helper. Every separately warped layer, including head and rear hair, uses NEAREST sampling into a 2x-output premultiplied FBO; the assembled avatar is LINEAR-resolved exactly once. The native face canvas and mouth pixel helper are unchanged. This prevents the 0.5 + 0.5 source-over = 0.75 alpha defect of independently LINEAR-filtered complementary cuts. The neutral-edge audit compares a full-source diagnostic reference and the independent sprites through identical sampling/resolve paths at 900x1200 and 652x869. The reference is never used in the deliverable video.

## Final evidence and optional candidate reuse

`verify_video.py` decodes the completed MP4 and extracts the actual encoded diagnostic peaks, one-second motion windows, and all eight expressions at closed, small, and wider mouth openings. Check those images, especially the surprised-expression skin and both shoulder/cuff connections. It verifies full decode, dimensions, duration, frame count, a file size below 20 MB, and decoded audio against the original timeline.

The neutral-edge reports bind the exact model, production renderer, and body sprite hashes. Their zero-deficit result applies to that source snapshot at the two recorded resolutions, not to arbitrary later artwork.

`reuse_fixed_motion.py` is an optional development helper, not required for a clean rerun. It reuses already generated pose/mesh/audio streams only after asserting all motion helpers, expressions, and voice are unchanged; it refreshes changed crop metadata and validates source images. Do not use it to conceal a changed motion implementation. For a clean reproducible run, always run `generate_layered_frames.mjs` instead.
