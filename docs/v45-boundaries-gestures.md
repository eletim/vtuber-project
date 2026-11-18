# v45: source-boundary diagnosis and selectable gestures

Baseline: v44 baca3eaeaf50ae54db0d1a1329abc155254dc8b2. Rigid 2D face roll remains unchanged.

## Boundary diagnosis and unresolved source limitation
At 2.47s, isolated draws show a rectangular ledge in the original arm_screen_right alpha and a cropped endpoint in side_right_outer. The neighboring rear hair has a separate hard source edge. The left shoulder support also has a straight cut. These exist in the source pixels, not a face roll deformation or transient alpha fade. Original v19 painted hair reveals and the existing hidden shoulder underpaint were inspected. They do not provide a directly usable continuous overlap at the moving cut. Removing the hidden underpaint exposed a triangular background gap; attaching the shoulder crop to head geometry exposed thin gaps. These trials were rejected, without altering active source pixels.

Moving rear pieces above arms alone did not remove the cuts. Shifting existing rear hair inward produced new slab-like edges and was rejected. Those candidate images are kept for diagnosis. An original PSD layer was extracted only into an unused diagnostic PNG; no active shoulder source image was generated, painted, clipped or replaced; the prior refused operation was not retried.

The accepted local change shares the displacement across rear strand cut edges while preserving independent tail lag inside each strand. It prevents extra separation at those source edges. It does NOT repair the prominent static rectangular shoulder cut; the same-input comparison must not be described as having solved that source problem. A coherent authored shoulder/hair overlap with hidden continuation is still needed for a complete repair. No claim is made that the prominent cut was fixed. The previously denied generation was not retried.

## Gestures
The normal UI now offers original, curious (neck tilt + cheek), and joyful (two small bounces + cheek) phrases. All use the same 18.5s server epoch. Variant identity is sent over the existing WebSocket and retained on late join and reconnect. Duplicate start/variant changes cannot replace an active epoch. Selector is disabled during playback/release. Manual pose interrupts; mouth and explicitly owned expression remain authoritative. No yaw/pitch is added by the new variants, and no torso scale is introduced.

No source pixels changed, so PSD artwork is unchanged; mesh attachment and temporal controls are runtime data. Existing separate arm/clothing/waist/skirt layers remain intact.
