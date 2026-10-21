# PSD v8 integration status

## Result

The editable, Cubism-oriented PSD integration remains **blocked on the
remaining completed region artwork**. The mandatory input gate in
[`v8-input-baseline.md`](v8-input-baseline.md) is now satisfied, but the
neck/clothing and sleeves/arms/hands region artwork does not exist in this
checkout. The completed hair/head candidate is available for integration.

The input status was rechecked on 2026-10-19 against `dev/v0.4.0`. The approved
source assets are ordinary Git blobs, their hashes match the immutable approval
manifest, and the v8 PSD reloads with 49 layers. This resolves the former input
blocker without changing the separate region-artwork and integration gates.

## Integration gate

| Requirement | Status |
| --- | --- |
| Every requirement in the input baseline | **PASS.** The five approved source assets match the manifest; both PSDs reload, and v8 has 49 layers. |
| Approved PSD v8 and expression references | **Available.** These inputs are ready for the later integration and visual-review gates. |
| Completed hair and head artwork | **Available.** [`koma_hair_head_cleaned_v8.psd`](../assets/parts/v8/koma_hair_head_cleaned_v8.psd) is the reproducible 51-layer candidate documented and audited in [`v8-hair-head-worklog.md`](v8-hair-head-worklog.md). |
| Completed neck and clothing artwork | **Missing.** [`v8-neck-clothing-worklog.md`](v8-neck-clothing-worklog.md) records that no region artwork was created. |
| Completed sleeves, arms, hands, and hidden-skin artwork | **Missing.** [`v8-sleeves-arms-hands-worklog.md`](v8-sleeves-arms-hands-worklog.md) records that no region artwork was created. |

The existing expression-regeneration script resolves the approved source
paths and writes a separate candidate. Its output must be compared without
overwriting the approved PSD and does not replace artwork or visual review.

## Work required after unblocking

After every baseline requirement is satisfied and all completed region artwork
is delivered, integration must:

1. validate the owner-supplied checksums or equivalent immutable approval
   record before opening the assets;
2. reload the approved PSD v8 and each completed region source, preserving
   editable layers and the approved initial appearance;
3. integrate the completed hidden artwork with Cubism-oriented layer naming,
   ordering, and separation without flattening it or replacing it with
   placeholder fills;
4. render and visually review the initial state, layer visibility and movement
   checks, and all expression states, including the existing natural closed-eye
   and closed-mouth artwork;
5. compare the initial composite with the confirmed image, rerun the PSD
   reload and audit path, and record any unresolved visual defects rather than
   treating a structural or pixel-only check as visual approval.

The result may be described only as a Cubism import candidate. Cubism
modeling, deformation parameters, and a `.cmo3` or `.moc3` rig remain a
separate phase, so an integrated PSD must not be represented as a rigged or
moving model.

## Scope preserved

No placeholder art, replacement expression, whole-character generation,
hidden-artwork edit, or Cubism rig was produced by this integration task.
Consequently, no new integration PSD, preview, GIF, or audit report can be
validly delivered until the remaining recorded gates are resolved.
