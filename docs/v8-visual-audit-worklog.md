# PSD v8 visual audit status

## Result

The visual PSD audit is **blocked and not run**. The mandatory input gate in
[`v8-input-baseline.md`](v8-input-baseline.md) is satisfied, but there is no
completed integrated PSD to audit.

The input gate was rechecked on 2026-10-19 against `dev/v0.4.0`. The approved
source assets and checksum manifest are available as ordinary Git blobs. The
completed region artwork and integrated PSD required for this later audit are
still outstanding.

## Audit evidence

| Required evidence | Status |
| --- | --- |
| Initial-state image | **NOT RUN — BLOCKED.** The approved confirmed image is available, but there is no completed integrated PSD to export and compare. |
| Visibility-toggle images | **NOT RUN — BLOCKED.** The completed hidden artwork and integrated editable layers do not exist in this checkout. |
| Displaced-part images | **NOT RUN — BLOCKED.** There is no completed integrated PSD whose independently editable parts can be moved and visually reviewed. |
| Expression images | **NOT RUN — BLOCKED.** The approved expression references are available, but the integrated PSD is not. |
| Expression regression GIFs | **NOT RUN — BLOCKED.** There is no completed integrated PSD from which to generate current regression evidence. |
| RGB fidelity | **NOT VERIFIED.** The approved confirmed image is available, but the required integrated PSD is not. |
| Alpha fidelity | **NOT VERIFIED.** The approved confirmed image is available, but the required integrated PSD is not. |
| Visible art quality | **NOT REVIEWED.** There are no valid exports to inspect for natural lines, fills, seams, overlaps, or continuity. |

No row above is a pass. In particular, the existing structural audit's
zero-hole result would be only a mechanical check and would not establish
visible art quality. Missing evidence and a retry-limit warning must remain
failures or unresolved findings; they must never be promoted to PASS.

## Required sequence after unblocking

Run this audit only after the input baseline remains satisfied, all region
artwork is completed, and the editable integrated PSD is reloaded successfully.
Then:

1. export the initial state and compare its RGB and alpha channels with the
   approved confirmed image;
2. export representative visibility-toggle and displaced-part states for all
   integrated regions;
3. export every approved expression state and the expression regression GIFs;
4. visually inspect the actual exports for natural hidden artwork, joins,
   seams, duplicate lines, overlaps, and expression quality; and
5. record each defect with its location and evidence, fix and rerun the audit,
   and leave any missing evidence or retry-limit warning unresolved rather than
   reporting a pass.

Mechanical pixel and hole checks may support this review, but they cannot
replace review of the exported artwork. The audit may pass only when all
required evidence exists, RGB and alpha fidelity are verified, and the visible
art review has no unresolved defects.

## Scope preserved

No substitute input, placeholder art, hidden-artwork edit, PSD modification,
binary publication, audit image, or GIF was created. This status does not
claim that the PSD is visually approved, ready for Cubism import, or rigged.
