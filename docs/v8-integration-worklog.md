# PSD v8 integration status

## Result

The editable, Cubism-oriented PSD integration is **blocked**. No PSD was
created or modified because the mandatory input gate in
[`v8-input-baseline.md`](v8-input-baseline.md) is not satisfied and the
required completed region artwork does not exist in this checkout.

This status was rechecked on 2026-10-19 against `dev/v0.3.0` at
`9e2783f771e1f8279a23f1017fb7fe3ce70ac0c6`. The worktree, reachable Git
history and remote branches, GitHub issue and pull-request records, and GitHub
releases contain no owner-supplied artwork bundle, authoritative design
principles, or immutable approval record. Pull request #2 only records that the
binary inputs were delivered in a conversation ZIP; it does not make those
inputs available from this checkout.

## Integration gate

| Requirement | Status |
| --- | --- |
| Every unblock requirement in the input baseline | **Blocked.** The authoritative design principles, approved artwork inputs, and owner-supplied checksum or equivalent approval record remain missing. |
| Approved PSD v8 and expression references | **Missing.** The initial composite, editability, natural closed-eye state, and natural closed-mouth state cannot be reloaded or visually verified. |
| Completed hair and head artwork | **Missing.** [`v8-hair-head-worklog.md`](v8-hair-head-worklog.md) records that no region artwork was created. |
| Completed neck and clothing artwork | **Missing.** [`v8-neck-clothing-worklog.md`](v8-neck-clothing-worklog.md) records that no region artwork was created. |
| Completed sleeves, arms, hands, and hidden-skin artwork | **Missing.** [`v8-sleeves-arms-hands-worklog.md`](v8-sleeves-arms-hands-worklog.md) records that no region artwork was created. |

The existing expression-regeneration script cannot resolve the absent source
paths. Running it without the approved sources, or manufacturing substitutes,
would not satisfy the artwork, approval, or visual-review requirements.

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

No placeholder art, inferred design principle, replacement expression,
whole-character generation, hidden-artwork edit, binary publication, or
Cubism rig was produced. Consequently, no integration PSD, preview, GIF, or
audit report can be validly delivered until the recorded gates are resolved.
