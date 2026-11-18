# v41 candidate: readable turns and motion-driven long hair

Baseline b7a01cf08839c2e504037efe3970ccc80c662ee5 (v40). No source artwork, shoulder regeneration, or PSD changes.

- Preserve v40 straight forearm and v36 side-hand/finger-line rendering.
- Acting cheek target0.965 lowers fingertip contact slightly. No shortening of arm bones or new wrist deformation.
- Face depth is now a bounded quartic cap,140px deep and230px radius. Its smooth slope returns to zero at the silhouette, avoiding singular edge derivatives and folding. Eye/mouth/skin share this geometry. Normal acting yaw reaches+/-14 degrees; pitch-6/+5. This is still a shallow frontal view, not a painted profile.
- Pelvis travel+/-72px, with normalized support, hip inclination and chest counter-rotation retained. Direction reversal is condensed from1.3s to0.9s; head leads it by0.35s. No torso/leg length scaling. Tried stronger torso angle but rejected it because existing shoulder boundaries became more conspicuous; angular command stays atv40 amplitude.
- Only long outer rear strands receive52px travel room instead of38px, driven by measured root acceleration. Other strand limits, roots and damping unchanged.

Performance comparison uses the same camera/start time with each version's normal acting controller: includes both rig and choreography changes. Native comparison applies the same new input to both rigs to isolate geometry. The earlier candidate is preserved outside the repo at ../v41-before-linear-step, including exploratory probes with stronger torso angle. Final images are in acting-native/review.

Prior playback diagnosis is at delivery-v40/playback-diagnosis-summary.json: unchangedv39 also dropped73/555;v40 hardware77/555 and software76/555. Periodic presentation timing/host environment suspected, root cause unresolved. CFR correctness is not a runtime throughput pass.


Pelvis spring now integrates a linearly varying command exactly between samples, so larger travel does not amplify low-frame-rate endpoint-hold bias. The existing20/30/60/120fps gesture comparison passed with its original3.6px tolerance; it was not loosened. The final renders are regenerated after this fix.

For a true three-quarter/profile turn beyond the shallow+/-15-degree projection, new consistent left/right facial silhouettes, nose/cheek occlusion, far-eye/eyelid shapes, ear/temple reveals and compatible8-expression eye/mouth layers would be needed. The present frontal paint cannot supply those hidden contours. This candidate does not claim that capability.


Visible limitations: the existing shoulder/neck boundary can still show a small background-colored wedge in the4s turned pose, including the v40 rig driven by the new input. This is not claimed repaired; shoulder repaint remains prohibited. The more readable movement should not be mistaken for a new anatomically complete profile illustration. No new black mouth patch or separated finger lines observed in sampled native frames.

Final validation: JavaScript 204/204 and Python 95/95 passed. All 555 frames decoded with 30fps timestamps (18.5s, no missing/duplicate timestamps). Dedicated 1x HTML video playback still dropped 74/555: presentation performance remains unresolved, despite correct CFR. Two-context start/stop/repeat/mode/join/reconnect and manual-expression/mouth priority passed with no browser errors. During the instrumented two-avatar capture, controller rendered about52.75fps and overlay57.10fps; this includes capture/readback overhead and is not isolated throughput.

Visual inspection: selected native full-size frames and contact sheets spanning arm ascent/hold/descent, decoded overview frames at2.4/3.6/11.5/14.4s in white/black/teal, plus all8 expressions at both extrema in a contact sheet. Not every native frame was individually inspected at full size. Dense native interval9-16s is available at30fps (211 frames plus10 landmarks). Automated temporal checks supplement, not replace, these observations. Readable turn and body-driven hair changes were seen; existing shoulder wedge and shallow-profile limits remain as above.
