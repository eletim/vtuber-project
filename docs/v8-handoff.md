# PSD v8 reusable handoff status

> **2026-10-19 現況更新：** この文書は前回AWM実行時の引き継ぎ記録です。PR #13でv7/v8素材を `dev/v0.3.0` へ追加し、PR #14で現行制作原則を整理しました。旧「素材不足」「承認記録不足」は当時の状態です。現在はGit LFSを使わず、通常のGit checkoutと `sha256sum -c docs/v8-approved-assets.sha256` で登録済み素材を検証し、Issue #15 の制作を開始してください。実際の新しいPSD清書・視覚レビューはこれからです。


## Handoff result

The reusable v8 handoff is **blocked and documentation-only**. The verified
repository materials below are the complete handoff currently available; no
asset archive was created because the required approved binaries, completed
region artwork, integrated PSD, and visual-audit evidence do not exist in this
checkout.

This status was consolidated on 2026-10-19 on `dev/v0.3.0`. The release head
includes the input, artwork, integration, visual-audit, and handoff gate
records. Its tracked tree contains no `assets/` directory and no PSD, PNG, GIF,
or ZIP artifact.

## Verified reusable materials

| Material | Verified use and limitation |
| --- | --- |
| [`scripts/repair_expressions_v8.py`](../scripts/repair_expressions_v8.py) | Reproducible expression-repair entry point. It resolves the documented inputs and outputs but cannot run without the missing artwork. Its prior reported results are not a substitute for rerunning and visually reviewing the recovered inputs. |
| [`scripts/audit_psd.py`](../scripts/audit_psd.py) and [`scripts/psd_writer.py`](../scripts/psd_writer.py) | PSD reload, composite, audit, and write support used by the v8 regeneration path. Their availability does not establish artwork quality or Cubism readiness. |
| [`config/koma_regions.json`](../config/koma_regions.json) | Tracked region configuration. It is configuration only, not an approved artwork source or visual-review record. |
| [`v8-expression-psd-repair.md`](v8-expression-psd-repair.md) | Historical regeneration instructions, expected paths, and reported results. The claims cannot be independently revalidated until the referenced binaries are supplied. |
| [`v8-input-baseline.md`](v8-input-baseline.md) and the region, integration, and visual-audit worklogs | Current gate evidence and fail-closed continuation requirements. These records describe missing deliverables; they are not those deliverables. |
| [`tests/test_psd_writer.py`](../tests/test_psd_writer.py) | Source-only PSD writer regression check. Passing it does not validate the absent v8 PSD or artwork. |

The source and documentation listed above are the reusable materials currently
available in the release head; they are not a completed asset package. Creating
an empty ZIP, generated replacement images, or a manifest that presents missing
files as delivered would produce a substitute bundle rather than the requested
handoff.

## Owner-supplied unblock requirements

The owner must supply all of the following through a controlled channel that
does not change the assets' existing visibility:

1. the authoritative design-principles content, or an immutable identifier for
   its authoritative copy;
2. the original `koma_v8_psd_expression_fix_bundle.zip`, or these five files
   individually at their documented paths:
   - `assets/parts/v8/koma_expression_repaired_v8.psd`;
   - `assets/original/koma_confirmed.png`;
   - `assets/expression_references/eyes_closed_mouth_open.png`;
   - `assets/expression_references/eyes_open_mouth_closed.png`; and
   - `assets/parts/v7/koma_illustrated_underlayers_v7.psd`; and
3. an owner-supplied checksum or equivalent immutable approval record that
   identifies the approved PSD v8 and reference files.

The blocker document at `docs/design-principles.md`, descriptions in existing
worklogs, and files reconstructed from those descriptions do not satisfy these
requirements.

## Required continuation after supply

The supplied files and approval record must first pass the validation sequence
in [`v8-input-baseline.md`](v8-input-baseline.md). Then the outstanding work
must proceed in order:

1. complete and review the hair/head, neck/clothing, and
   sleeves/arms/hands/hidden-skin artwork recorded in the three region
   worklogs;
2. integrate those completed sources into a reloadable, editable PSD while
   preserving the approved initial image and expression states, as specified
   by [`v8-integration-worklog.md`](v8-integration-worklog.md); and
3. produce and visually review every initial-state, visibility-toggle,
   displaced-part, expression, comparison, GIF, RGB/alpha, and audit artifact
   required by [`v8-visual-audit-worklog.md`](v8-visual-audit-worklog.md).

Only after those gates pass can a controlled handoff contain the updated PSD,
drawn PNG sources, comparisons, GIFs, and audit report. The integrated PSD may
then be described only as a Cubism import candidate; Cubism modeling,
parameters, `.cmo3`, and `.moc3` output remain separate work. Until that point,
this handoff makes no claim of artwork completion, visual approval, Cubism
readiness, or rigging.

## Unresolved deliverables

| Requested handoff item | Status |
| --- | --- |
| Updated editable PSD | **Missing — blocked by inputs, region artwork, and integration.** |
| Drawn PNG sources | **Missing — no approved completed region artwork exists.** |
| Reproducible scripts | **Available as source, but asset-dependent v8 execution is blocked.** |
| Initial/comparison/toggle/displacement/expression images | **Missing — visual audit not run.** |
| Regression GIFs | **Missing — visual audit not run.** |
| Audit report | **Missing — visual audit not run; historical claims are not a current report.** |
| Explicit unresolved findings | **Available in this file and the linked gate records.** |

No binary was copied, generated, published, or made more broadly visible while
preparing this handoff. No main-branch content was merged, and the existing
blocked status was not promoted to a pass.
