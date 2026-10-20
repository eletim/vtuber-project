# PSD v8 reusable handoff status

> **2026-10-19 現況更新：** この文書は前回AWM実行時の引き継ぎ記録です。PR #13でv7/v8素材を `dev/v0.3.0` へ追加し、PR #14で現行制作原則を整理しました。旧「素材不足」「承認記録不足」は当時の状態です。現在はGit LFSを使わず、通常のGit checkoutと `sha256sum -c docs/v8-approved-assets.sha256` で登録済み素材を検証し、Issue #15 の制作を開始してください。実際の新しいPSD清書・視覚レビューはこれからです。


## Handoff result

The reusable v8 handoff remains **incomplete** because completed region
artwork, an integrated PSD, and current visual-audit evidence do not exist. The
five approved source assets are available and pass the input baseline; they are
not the finished handoff by themselves.

This status was updated on 2026-10-19 on `dev/v0.4.0`. Its tracked tree contains
the approved PSD, PNG, GIF, JSON, and README bundle contents as ordinary Git
blobs. The source ZIP remains intentionally untracked to avoid duplication.

## Verified reusable materials

| Material | Verified use and limitation |
| --- | --- |
| [`scripts/validate_approved_assets.py`](../scripts/validate_approved_assets.py) | Read-only input validator for the five source hashes, ordinary Git blobs, PSD structures, and required v8 layer count. |
| [`scripts/repair_expressions_v8.py`](../scripts/repair_expressions_v8.py) | Reproducible expression-repair entry point. It resolves the documented inputs and writes a separate candidate; rerunning it is not a substitute for visual review. |
| [`scripts/audit_psd.py`](../scripts/audit_psd.py) and [`scripts/psd_writer.py`](../scripts/psd_writer.py) | PSD reload, composite, audit, and write support used by the v8 regeneration path. Their availability does not establish artwork quality or Cubism readiness. |
| [`config/koma_regions.json`](../config/koma_regions.json) | Tracked region configuration. It is configuration only, not an approved artwork source or visual-review record. |
| [`v8-expression-psd-repair.md`](v8-expression-psd-repair.md) | Historical regeneration instructions, expected paths, and reported results. Current outputs still require visual review. |
| [`v8-input-baseline.md`](v8-input-baseline.md) and the region, integration, and visual-audit worklogs | Current gate evidence and fail-closed continuation requirements. The input gate passes; later deliverables remain outstanding. |
| [`tests/test_psd_writer.py`](../tests/test_psd_writer.py) | PSD writer regression check. Passing it does not establish artwork quality. |

The source, approved assets, and documentation listed above are reusable
materials, not a completed asset package. Generated replacement images must not
be presented as approved inputs or as the requested finished handoff.

## Verified input baseline

The five approved source assets, current design principles, and immutable
checksum manifest are present. Run `python3 scripts/validate_approved_assets.py`
before continuing. Never replace or overwrite the approved source PSD while
producing a regeneration or integration candidate.

## Required continuation

The registered files must continue to pass the validation sequence in
[`v8-input-baseline.md`](v8-input-baseline.md). Then the outstanding work must
proceed in order:

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
| Updated editable PSD | **Missing — blocked by region artwork and integration.** The approved 49-layer input PSD is available. |
| Drawn PNG sources | **Missing — no approved completed region artwork exists.** |
| Reproducible scripts | **Available.** Input validation and asset-dependent v8 execution can resolve their sources. |
| Initial/comparison/toggle/displacement/expression images | **Missing — visual audit not run.** |
| Regression GIFs | **Missing — visual audit not run.** |
| Audit report | **Missing — visual audit not run; historical claims are not a current report.** |
| Explicit unresolved findings | **Available in this file and the linked gate records.** |

The approved binaries retain their established repository visibility. No new
binary was generated while updating this handoff, and the unfinished artwork,
integration, and visual-audit gates were not promoted to a pass.
