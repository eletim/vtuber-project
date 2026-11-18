# v40 candidate — arm axis, shallow face projection, stronger acting input

Baseline: 58b73ac7b8216e43b621fb08a66be68fc6462b59 (v39).

## Changes
- Wrist correction previously propagated across a 160 px distal span plus a proximal fade. The central forearm bowed by 11.5–20.8 model px in axis probes. Keep the shaft rigid, use an 80 px terminal arc and reduce authored-pose correction to 35 degrees at cheek contact. A separately reported surfaceWrist identifies the rendered wrist; wrist remains the projected rigid-bone reference.
- Preserve v36 hand-angle paint, finger-line transition and opaque cuff. No texture, PSD, shoulder or layering changes.
- A shallow common face surface projects yaw/pitch, carrying skin, eyes, mouth and their mask together. It supports subtle frontal turns, not a newly painted profile or full 3D head.
- Normal UI acting uses full +/-1 weight transfer (previously +/-0.88), anticipatory +/-7-degree yaw (previously +/-2), and a down/up pitch phrase. Existing joint-based happy bounces and hair spring response are retained; no limb length or torso scaling added.
- Existing shared controller/overlay protocol carries these same parameters without adding a new transport.

## Comparison conditions
cfr-review: new input applied identically to v39 and v40 rigs, isolating deformation changes.
performance-review: same camera/time, each version's own normal acting sequence, showing choreography plus rig changes.
acting-native: 1:1 source crop [180,50,600,950] from each 1086x1448 canvas; 9–16 s every 1/30 s, plus face/weight extrema. Original diagnostic probes also preserved in native-review.

## Limits
Shoulder redraw remains prohibited and untouched. Existing sleeve silhouette/shoulder boundaries are not claimed repaired. Foot contact and full knee flexion cannot be assessed from the cropped authored material. Facial projection remains shallow; large profile turns would require angle-specific artwork. Automatic temporal checks and headless playback metrics do not replace the native-image visual review described in the final results.

## Verification results
- Full JavaScript tests 202/202; relevant Python runtime suites 95/95. Initial fixed-width face assertion replaced with exact projected-chord preservation, not relaxed tolerance. Failed initial log retained outside repo.
- Headless two-context start/stop/repeated commands/mode change/reconnect and settle passed; manual expression and mouth ownership retained.
- Both 18.5 s outputs contain 555 exact 30 fps samples from fixed 60 Hz physics. All 555 decoded; no timestamp gaps/duplicates.
- 1x headless playback dropped frames: 76/555 after decode; isolated playback74/555, wall time18.7s. File timing is correct, but real-time smoothness here is NOT accepted as drop-free.
- Viewed all221 native samples as10 contact sheets; native-size checks at3,7,9.1,11.5s plus diagnostic11.5/14.5s;8-expression extremes on black/white contact sheet. No new visible arm split,double fingers,face-mouth misregistration or waist crack in this inspected range. Native frames remain for independent review; not every pixel of every frame was inspected at full size.
- Largest adjacent image changes at9.03-9.13s coincide with broad body motion in both versions; inspected9.1s native. Forearm has a straight shaft, with terminal wrist curvature remaining.
- Texture/PSD unchanged; source assets/parts/v36/koma_hand_angle_v36.psd. No PSD regeneration needed for geometry-only changes.
