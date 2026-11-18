# Independent v15 mouth-defect reproduction

Date: 2026-10-21. Reviewer: independent pixel audit. Source frozen from restored repository before v16 work. No production code or art changed by this audit.

## Findings

1. The lip axis changes with mouth opening even when the head pose is fixed. This is not a missing global head rotation. The old `featureBands` compresses mouth-core Y around a horizontal anchor (y=356), so the authored oblique mouth axis collapses toward canvas X as opening falls. The shared body mesh subsequently rotates face and mouth together, but it cannot recover the lip tilt already lost locally.
2. Intermediate states are the problem. All eight expressions were rendered at head Z = -8, 0, +8 degrees (the runtime's actual limits) and mouth amounts 0, .15, .35, .65, 1: 120 pixel-reviewed cases, with full-face images retained. Closed and fully open endpoints are insufficient to validate the fix. In particular, M=.15 and M=.35 show the axis collapse and a different mouth shape/line.
3. The suspicious dark mouth-adjacent marks in the supplied encoded video are reproduced, especially big_smile frame 360 (12.000 s) and frame 390 (13.000 s). They are dark brown authored lip/interior corners compressed into small isolated-looking flecks/triangles, together with an observable rectangular restoration/skin-tone boundary. They are not demonstrated to be literal black pixels or a transparency hole.
4. Every original base is fully opaque throughout source-mouth ROI x=500:605, y=325:390. All 120 offline rendered mouth ROIs have minimum alpha 255. The separate video worker also reproduced the corner marks before the mesh and H.264 stages, with mouth-FBO alpha 255. This rules out transparent-black sampling and video encoding as the root cause of these reproduced marks.

## Exact encoded-video examples

Input: `/workspace/scratch/f1d5e45451e6/recovered_v15/koma-v15-expression-motion.mp4`
SHA256: `412db3116f740f600c4f15a4cdf865b5bf21615c943e1a253d6f7dd1d02d8fa1`
1600 x 1080, 30 fps, 1,260 frames, 42.000 seconds.

- Frame 180 / 6.000 s, soft_smile. Head Z -1.140869 deg; mouth .385690; feature scale .328545. The mouth is much flatter than the painted tilted face.
- Frame 210 / 7.000 s, soft_smile. Head Z -1.473525 deg; mouth .379783; scale .322088.
- Frame 360 / 12.000 s, big_smile. Head Z +1.462210 deg; mouth .252234; scale .182675. Thin horizontal lip with dark corner flecks.
- Frame 390 / 13.000 s, big_smile. Head Z -.098415 deg; mouth .350359; scale .289928. Dark triangular left corner and incorrect local lip angle.
- Frame 780 / 26.000 s, bashful. Head Z +.225745 deg; mouth .385690; scale .328545.

All actual-video closeups are decoded from the delivered MP4, not idealized source frames. Diagnostic cropping enlarges defects for review; full-face contact sheets and original video remain available, and the corrected deliverable must not hide defects by cropping or removing motion.

## Evidence

- `v15_actual_video_contact_1.jpg`, `v15_actual_video_contact_2.jpg`, `v15_actual_video_contact_3.jpg`: actual encoded frames every 0.5 s, 84 total.
- `actual_v15_frame_0360_mouth.png`, `actual_v15_frame_0390_mouth.png`: enlarged actual-frame defect examples.
- `v15_authored_mouth_endpoints.png`: original authored closed/open mouths, composited over original bases.
- `v15_base_mouth_alpha.png`: base restoration pixels and alpha inspection.
- `v15_grid/*_matrix.png`: 120-case offline OpenGL pixel matrix, eight full-face sheets.
- `v15_grid/stats.json`: per-case alpha and literal dark-pixel check.
- `v15_pipeline/`: frozen original runtime, exact JS helpers, original video pipeline plus repeatable review-grid generation/rendering scripts.

## Limitations and release gate

The controlled matrix is offline EGL/llvmpipe rendering using the original exported runtime geometry, not browser UI/E2E capture. The actual delivered encoded video was separately decoded and visually reviewed. Final v16 approval is pending a frozen corrected helper, the same 120-case intermediate-state matrix, and independent review of the actual new encoded frames. No claim of browser E2E has been made.
