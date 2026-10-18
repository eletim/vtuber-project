# PSD v8 input baseline status

## Result

The required input baseline is **blocked**. No artwork, regeneration, or visual
approval work may begin from this checkout.

This status was verified on 2026-10-19 against `dev/v0.3.0` at
`bfdbdcff2dad00b405f4d923736d584a898020d6`. The repository paths, reachable
Git history and remote branches, GitHub issues and pull requests, and GitHub
releases contain no copies of the required binary artwork. The repository does
not expose an `assets/` tree. The issue and existing worklogs instead say that
the binaries were delivered in a conversation ZIP, which is not available in
this checkout.

## Required inputs

| Input | Expected location or source | Validation status |
| --- | --- | --- |
| Authoritative design principles | Owner-supplied original document or immutable authoritative identifier | **Missing.** `docs/design-principles.md` is a recovery/blocker record and explicitly is not the principles specification. |
| Approved PSD v8 | `assets/parts/v8/koma_expression_repaired_v8.psd` in `koma_v8_psd_expression_fix_bundle.zip` | **Missing.** Approval, layer count, editability, image fidelity, and file integrity cannot be independently validated. |
| Confirmed image | `assets/original/koma_confirmed.png` in the same bundle | **Missing.** The approved baseline pixels and dimensions cannot be validated. |
| Closed-eye expression reference | `assets/expression_references/eyes_closed_mouth_open.png` in the same bundle | **Missing.** Its approval and relationship to the confirmed image cannot be validated. |
| Closed-mouth expression reference | `assets/expression_references/eyes_open_mouth_closed.png` in the same bundle | **Missing.** Its approval and relationship to the confirmed image cannot be validated. |
| Illustrated v7 underpainting | `assets/parts/v7/koma_illustrated_underlayers_v7.psd` in the same bundle | **Missing.** Its reported 49-layer structure and underpainting cannot be reloaded or visually validated. |
| Regeneration path | `python3 scripts/repair_expressions_v8.py` | **Located but blocked.** The script resolves the four regeneration inputs above and writes `assets/parts/v8/koma_expression_repaired_v8_candidate.psd`, previews, a GIF, and audit JSON. The candidate path is separate from the owner-supplied approved PSD, but the script cannot run without the inputs. A successful regeneration would not by itself prove owner approval. |

The expected paths and bundle name come from
`docs/v8-expression-psd-repair.md`; the v7 provenance and unresolved art-review
status come from `docs/v7-underpainting-worklog.md`. These records are useful
handoff evidence, but they are not substitutes for the missing files or
owner-supplied approval evidence.

## Precise unblock requirements

The owner must provide, without changing their existing visibility, all of the
following:

1. the authoritative design-principles content or an immutable identifier for
   its authoritative copy;
2. the original `koma_v8_psd_expression_fix_bundle.zip`, or the five artwork
   files listed above through an equally controlled channel; and
3. an owner-supplied checksum or other immutable approval record identifying
   which PSD v8 and reference files are approved.

After controlled retrieval, validate checksums before opening the assets, then
reload and inspect the supplied PSDs, run the existing regeneration path, and
compare the regenerated candidate PSD with the approved PSD without replacing
it. Compare the initial composites with the confirmed image and inspect the
expression states visually. Until then, do not infer design principles, create
replacement inputs, begin hidden-artwork changes, claim input readiness, or
publish the assets to GitHub or another broader audience.
