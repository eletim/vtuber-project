# v43: shallow face directions with shared hair boundaries

This version adds small left/right/up/down facial direction cues to the normal renderer and overlay. It does not provide a full side view or anatomically complete 3D head. The range is deliberately limited to the supplied portrait and candidate materials; v41's curved depth cap is not restored.

The face skin, fixed hair, and twelve moving strands share one correspondence field. Eye interiors and the mouth center translate rigidly; a broad normalized transition joins the surrounding skin. Four endpoint displacement fields are prepared once, then combined within a bounded envelope. Existing head spring commands drive the angles, including interruption/return behavior. Hand, arm, torso, waist, skirt, expression, and speech-control code is unchanged. A separate reconnect fix discards a stale RAF interval when a fresh authoritative acting snapshot resumes the same epoch; it does not reset the pose or override blocked speech/manual input.

Generated candidates supply direction landmarks and a small registered nose material region. The generated head/eyes are never crossfaded as complete images. Nose highlights and tips are registered to the original portrait before blending, including mixed yaw/pitch. The original expression patches and partial mouth-opening routine remain active.

Rejected experiments are retained locally. Separate skin/hair warps opened ownership seams. Narrow transitions around rigid eyes inverted one render triangle at left yaw; the final wide normalized collar passes actual mesh tests. The face field also terminates above the collar/shoulder source boundary to avoid opening a seam during body motion. Incorrect nose registration produced a duplicate line in mixed angles and was corrected using source pixels.

Validation artifacts and exact scope are recorded in assets/parts/v43/FINAL-REVIEW.json and the delivery manifest. Dense local PNG sequences are reproducible with scripts/validate_face_angles_v43.mjs. CFR output and successful headless video decoding alone do not establish real-time runtime performance on a user's visible browser.

The v43 PSD preserves the v36 layer tree and default composite, and adds hidden registered nose overlays matching runtime sampling. Facial animation correspondence remains code, not a claim that an angle-specific full head painting has been completed. Source Library IDs are preserved under assets/parts/v43/library-input.

Known limits: large yaw/pitch needs coherent angle-specific facial contours and eye/ear/hair occlusion artwork. Foot contact remains unverified because feet are not present. The previously denied shoulder edit was not retried. No external uploads, push, installations, authentication changes, or user desktop interaction were performed.
