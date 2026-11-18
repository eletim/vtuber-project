# v44: rigid 2D head roll

The user rejected v43 facial deformation and requested 2D roll only. v43 approval is withdrawn.

The renderer no longer imports the angle rig, loads the angle materials, or paints a replacement nose. The original v42 face, expression, mouth and hair source configuration is identical. Archived angle candidates remain on disk and in history but are not used at runtime.

All facial pixels use one rigid neck-pivot rotation, followed by rigid chest and pelvis rotations/translations. Eye/eyebrow/mouth sprites share that geometry; only existing expression, blink and mouth-opening controls act locally. The legacy head texture also contains neck and shoulder pixels: below model y=450 those attach smoothly to the original torso surface by y=565. This region is below the face. Hair roots inherit the rigid head region; long hair keeps the existing lower-body attachment field and strand physics, preserving coverage over the limited shoulder underpainting. The reveal layer follows the same field.

The ordinary acting sequence now explicitly tilts left and right. Controller and overlay use the same rendering path and existing synchronization. No external streaming was started.

PSD pixels have not changed. The original accepted v36 PSD used by v42 remains the active source; v43 overlays are archived, not active. See assets/parts/v44/psd-consistency.json.

Verification artifacts record rigid distance preservation, full tests, 84 expression/blink/mouth/background conditions, 30fps CFR near-view and whole-body captures, and two-context start/stop/reconnect/switch verification. Visual checks are reported separately from numerical success. No anatomical yaw/pitch is claimed or pursued.
