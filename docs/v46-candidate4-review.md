# Left-eye candidate 4 — pending review

The production renderer/model are unchanged. Candidate 3 is preserved in commit f36c705a74c6174514b5d000a97cc40612ef84e1. This remains a left neutral eye experiment, not the finished v46 delivery.

## Changes

- The revealed skin receives a smooth colour residual from surrounding original cheek pixels and the registered original closed-eye reference. Hair/dark lash samples are excluded. This is colour correction only, not face displacement.
- Gaze now translates a premultiplied iris layer and reconstructs the original rest composite using the same layer. The previous separate registered-sclera replacement caused 221 pixels to change by more than 8 channel values at a gaze input of 0.00001 (maximum 235). The revised calculation has zero such pixels, maximum 3. It does not blend between two eye poses or scale the iris.
- Pale lower-rim sclera is assigned partial iris coverage; interior glints remain opaque. The original central-open image is still exact.
- The probe injects the candidate only into a dedicated AvatarRenderer instance, before the existing foreground hair ownership removal. Production behaviour is not switched. Whole-face images at native pixel scale now include five openings at roll -12/0/+12 degrees.

## Evidence and limits

`assets/parts/v46/left-probe/report.json` contains the final browser results, 61 opening samples, twelve combined gaze/blink samples, and a 270-frame 30fps CFR recording. The playback measurement is a dedicated headless video run, not a claim about all runtime performance. Native frames remain in `left-probe/frames` locally.

Review whole-face files `face-0-0.png`, `face-0-0.5.png`, `face-0-0.75.png`, and the rolled counterparts. Skin continuity and the fine hair/lash crossing still need independent visual acceptance. Only the neutral left eye has been integrated into this probe; right eye, smile-eye materials, all-expression controls and production UI are not complete.

No raster source was changed in candidate 4. Candidate3 PSD retains the source layers and is reused; the new colour residual and iris ownership are procedural compositor operations. The original closed-eye material already exists in that PSD. No new PSD version is claimed.

## Right-eye material handoff (independent of left acceptance)

Use the actual screen-right eye, never a mirror of the left:

- `assets/parts/v46/references/eye_screen_right_open.png`: 146x116, model rect [538,204,684,320], 27999 bytes; SHA256 4a43f45ed58338938f403b6eebc0f64ff7b4723c850d70fa71163639a0e3fda1.
- `assets/parts/v46/references/eye_screen_right_closed.png`: 173x145, model rect [526,192,699,337], 45881 bytes; SHA256 db067f50468c0cf4fdf9b504630129360788846b28cb73fe3dacc5468641c7dd.

Needed separate transparent candidates, aligned to the open-eye reference: (1) white sclera behind the original iris, no lashes; (2) skin under the eye/lashes, retaining the surrounding cheek gradient and blush without hair/brow/lash remnants; (3) full iris including hidden upper/lower cap, maintaining original amber colour, pupil and highlights. Existing visible pixels remain authoritative. The generated imagery must not redesign the eye or be substituted wholesale. Keep original canvases/anchors when possible; registration will still be verified.

The Windows reference-path imagegen input issue remains the already established material-generation handoff to the parent. No rejected operation was retried and no new permission request is needed. No upload has been attempted in this candidate.
