# v46 eye separation: diagnosis and exact material request

Baseline af26c3a34bd12b90721eadb90423f0f661bb3993. Branch codex/koma-v46-eye-components.

## Confirmed current structure
The active v36 PSD contains 116 eye-named layers including expression copies and archived originals. They are open/closed composites; no independently named iris, pupil or sclera layer exists. Inspected neutral open/closed pixels include surrounding skin, lashes and hair. Runtime featureOpening switches eye state at 0.4 and uses scale=1: the defect is abrupt sprite substitution, not current whole-eye vertical scaling. Expression defaults multiply openness; no independent gaze texture is present. Face BodyRig and runtime remain unchanged at this checkpoint.

## First required edit: screen-left neutral eye only
Reference files are byte-identical copies under assets/parts/v46/references. Their model rectangles and hashes are recorded in eye-diagnosis.json. Open target is eye_screen_left_open.png (179x125 pixels, model rectangle 356,229,535,354). Closed reference is eye_screen_left_closed.png (203x150, rectangle 344,217,547,367); it is not aligned to the open crop without these offsets. Right eye is a later separate target, not a mirrored left eye.

Use the original open image as the edit target, closed image only as a skin/lash reference. Produce separate transparent PNG assets, keeping original eye tilt, amber color, lash shape, and coordinate registration. Do not redesign, enlarge, round, or make the character younger. Keep source reference immutable. Start with this one eye to validate neutral identity before all expressions.

1. SCLERA UNDERPAINT: remove iris/pupil/highlights only inside the existing eye aperture and complete the hidden off-white sclera behind them. Keep the aperture outline and original surrounding pixels fixed. No new lashes. We will extract only the registered aperture and discard regenerated surrounding pixels.
2. SKIN UNDERPAINT: fill the eye aperture and lash region with matching surrounding skin, preserving the brow/hair and original light/blush. This is an occluded backing, not a new visible face. Do not introduce dark outlines. Used to cover the eyeball during lid travel without moving surrounding skin.
3. IRIS DISC: isolated original amber iris/pupil/highlights on transparent background, complete only the portion hidden by upper lashes. Preserve original visible iris shape and markings. No sclera, lashes, brow or surrounding skin. Keep its original native radius; metadata/registration needed if generation changes canvas size.

Original upper/lower lash contours should be extracted from original pixels, not redesigned by generation. Lid motion should deform only a narrow lid skin/lash band, with original eye-corner anchors fixed. Sclera and iris are clipped to a continuously closing aperture; iris translation changes gaze, never its scale. Full closure uses the original closed lash shape after registration, with no double-line alpha crossfade. Smile eye must retain the original big_smile reference. Brow remains separate from eyeball ownership.

## Integration / validation after material return
First one neutral eye: recomposite open at center and compare against original; inspect gaze center/left/right/up/down without iris scaling; 61 openness steps with opaque lid coverage and fixed eye corners. Then other eye and eight expression eye shapes, independent blink, mouth and roll combinations. Keep v45 body/hand/2D rigid face unchanged. Add explicit gaze controls to existing UI/control transport only after source pixels pass. PSD stores original backups plus sclera/iris/lids/skin/masks as independent layers. Final deliverables remain pending; no candidate animation is claimed complete.

## Tool limitation
The existing executor history established that imagegen cannot resolve this Dell Windows local path (AbsolutePathBuf input resolution error, before generation). Per parent instruction, this known failing input was not repeated. Parent can edit the exact references through the established Library route. No new safety refusal occurred here, no API fallback or installation attempted, and no shoulder generation was requested. This is a pending material handoff, not an authorization question.

## Follow-up after left material import
Three left-eye candidates were materialized with official unmodified helper in the same Dell WSL. IDs and original WSL paths are retained in imports/identity.json. A left-only compositor prototype and hidden candidate PSD groups are saved, not enabled in the active model. See candidate-status.json and left-probe/report.json. No production quality or all-expression completion is claimed.

Next required assets: screen-right white sclera underpaint, skin underpaint, and iris hidden cap, using references/eye_screen_right_open.png (146x116, model rect 538,204,684,320) as edit target, references/eye_screen_right_closed.png (173x145, rect 526,192,699,337) as reference. Same original-pixel priority as left; do not mirror the left image or redesign eyelashes. Right-eye source hashes and sizes are in eye-diagnosis.json. Left half-eye contour still requires refinement/review, independently of this right-side material dependency.

## Candidate 3 review response
Replaced per-column skin correction with a smooth 2D color fit to avoid vertical bands. Main foreground hair and its thin crossing strand now have separate coverage; reference underlay uses the same area weights, preventing a near-open pop. The lower lid follows a curved finite-speed path, not a flat linear cut. The moving iris excludes 92 contaminating sclera/skin edge pixels while retaining native highlight regions. Generated pixels remain supplementary; original visible source is preferred.

Latest probe contains 61 openness samples, 12 blink/gaze combinations, and a 9-second 270-frame CFR clip with simultaneous gaze/blink in its final three seconds. All 270 native frames are retained locally under left-probe/frames. See candidate2-vs3.png for same-pose comparison. Browser playback is measured independently; the recording is not a production approval. Candidate PSD3 preserves all original groups, with eye candidate layers hidden. Right eye, eight-expression integration and normal UI remain pending.
