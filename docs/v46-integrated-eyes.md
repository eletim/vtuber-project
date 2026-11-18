# v46 integrated eyes — review candidate

Both screen-side eyes now have independently registered native source partitions: iris/pupil/highlights, sclera, upper lash/lid, lower lash/lid, fixed surrounding pixels, foreground-hair coverage and hidden skin/iris supplements. The right is not mirrored. Generated material is retained with Library provenance under `assets/parts/v46/imports/right`; visible iris pixels come from the original. Iris translation does not scale the iris. Eyelids change the aperture and occlude it.

The normal renderer loads these components via model.json. Seven expressions use the shared aperture with their original open-eye pixels. **big_smile deliberately retains its original authored closed smile eyes**, including its original eyebrow/lash relationship. It does not receive a fabricated open eyeball or gaze. Mouth rendering is unchanged. Face/head geometry remains rigid 2D roll; no yaw/pitch facial warp was added.

UI sliders `視線・左右` and `視線・上下` use the existing control/WebSocket transport. The overlay receives the same values. Tests cover horizontal and vertical updates, reconnect, all eight manual expression choices and mouth input remaining at 0.7 while gaze remains 0.6.

## Right-eye review corrections

The first right candidate accidentally included sclera in the upper-lash sampling band. Its contour anchors were corrected against a coordinate grid of the native image. The closed curve was smoothed to remove its outer angular bend. Right hidden-skin colour is registered to the original closed-eye cheek as a continuous colour plane; a temporary per-pixel substitution which produced vertical seams was rejected. Right foreground intersections use neighbours sampled along the lash contour, instead of horizontal neighbours which could include hair or sclera. The accepted left sampler was retained.

The surprised drawing has a higher upper lid than neutral. Native-frame inspection exposed rough intersections when it reused the neutral aperture. It now has its own raised upper contour and contour-following hidden-lash sampling; neutral left remains unchanged. This is a local eye aperture adjustment, not a head/face warp.

## Roll-test correction

Candidate4's nominal -12/0/+12 stills reused time zero, so springs never advanced: the parent correctly found only five distinct images. Those images are not roll evidence. `pair-probe/report.json` now lists the authoritative nine final stills: three openings and actual supported -8/0/+8 roll inputs, each settled through 60 fixed time steps. The script fails if the three roll images have equal hashes. Older unlisted gaze stills remain historical, not final evidence.

## Validation and viewing

- `integrated-review/report.json`: central-open identity and near-zero gaze continuity for each eye; 360-frame, 30fps, same-input v45/v46 comparison and full-body clip; overlay gaze/reconnect results.
- `integrated-review/frames`: every native comparison frame, retained locally. The left panel is v45 and right panel v46. Eight expressions each occupy 1.5 seconds; moving gaze, blink, mouth and roll are combined. White background changes to dark teal at six seconds.
- `ui-review/report.json`: eight manual expressions with mouth/gaze priority, black-background face images and actual 1x video playback measurement.
- `psd-runtime-v46.json` and `psd-integrated.json`: source PSD hash and roundtrip. Original merged artwork remains byte-identical; new editable eye-source groups are hidden because the runtime compositor selects their layers and performs procedural aperture/matting/colour operations.
- JavaScript final suite and runtime Python suite have dedicated logs. Full Python discovery also has a separate log: four legacy imports require unavailable SciPy, and the legacy v19 raw-byte preservation check fails on CRLF in v10/integration.json. `legacy-test-diagnosis.json` confirms the Git blob is unchanged from its baseline and the checkout matches after newline normalization. No dependencies or Git settings were changed to hide those failures.

## Remaining limits

This is an integrated review candidate, not an assertion of perfect facial quality. Fine hair/lash intersections still need independent close-up review, especially on the new right eye and expression transitions. The generated supplements and curve registration do not replace angle-specific animation artwork. Existing shoulder cut boundaries are unchanged and outside this eye task. No shoulder image generation, external upload, installation, push or merge was performed.
