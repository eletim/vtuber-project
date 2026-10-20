# PSD v8 input baseline status

## Result

The required input baseline is **usable**. On 2026-10-19, the five approved
source assets in `dev/v0.4.0` were verified against
[`v8-approved-assets.sha256`](v8-approved-assets.sha256). They are complete
ordinary Git blobs, not Git LFS pointers or substitutes.

Both PSDs reload as layered PSD data. The approved v8 PSD contains 49 editable
layers, as required. This establishes input availability and structure; it does
not by itself approve unfinished hidden artwork, integration, visual quality,
or Cubism readiness.

## Verified inputs

| Input | Repository path | Validation status |
| --- | --- | --- |
| Approved PSD v8 | `assets/parts/v8/koma_expression_repaired_v8.psd` | **PASS.** SHA-256 matches, the full file is an ordinary Git blob, and the PSD reloads with 49 layers. |
| Confirmed image | `assets/original/koma_confirmed.png` | **PASS.** SHA-256 matches the approval manifest. |
| Closed-eye expression reference | `assets/expression_references/eyes_closed_mouth_open.png` | **PASS.** SHA-256 matches the approval manifest. |
| Closed-mouth expression reference | `assets/expression_references/eyes_open_mouth_closed.png` | **PASS.** SHA-256 matches the approval manifest. |
| Illustrated v7 underpainting | `assets/parts/v7/koma_illustrated_underlayers_v7.psd` | **PASS.** SHA-256 matches, the full file is an ordinary Git blob, and its layered PSD data reloads successfully. |
| Authoritative design principles | `docs/design-principles.md` | **Available.** This is the current specification assembled from project decisions and approved assets. |
| Regeneration path | `python3 scripts/repair_expressions_v8.py` | **Available.** It writes a separate candidate and must never overwrite the approved v8 source. |

The manifest also covers the four derived bundle outputs. They remain useful
provenance, but they are not part of this five-source input gate.

## Repeatable validation

Run the fail-closed validator from any normal checkout:

```bash
python3 scripts/validate_approved_assets.py
```

The command checks all five source hashes, rejects Git LFS pointer text,
requires each approved hash to match the full committed `HEAD` blob, parses both
PSD layer structures, and requires exactly 49 layers in the v8 PSD. It is
read-only and does not regenerate or overwrite approved sources.

After this gate passes, continue with the outstanding region artwork,
integration, and visual-audit worklogs. Any candidate regeneration must stay at
its separate candidate path and be compared with, never substituted for, the
approved v8 PSD.
