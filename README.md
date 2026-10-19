# VTuber Project — 羽月こま

## 2026-10-19 更新：制作素材をGitに登録済み

PSD v7/v8・確定画像・表情参照画像は、PR #13により `dev/v0.3.0` に登録済みです。PSD本体はGit LFSで管理します。新規ワークツリーでは `git lfs pull` を実施し、`sha256sum -c docs/v8-approved-assets.sha256` で確認してください。以前の「素材不足によるブロック」はこの登録以前の状況です。現行の制作原則は `docs/design-principles.md` を参照してください。次の実制作は Issue #15 で進めます。


将棋VTuberキャラクターをLive2D化する制作プロジェクトです。人間モードとAIモードの両方に対応させる予定です。

## 現在の工程

PSD v8 のリリース作業は**入力素材不足のためブロック中**です。リポジトリには再生成・監査用のソースと、確認できている不足事項だけがあり、承認済みPSD、元画像、表情参照画像などのバイナリはありません。必要な入力と再開時の検証手順は [PSD v8 input baseline](docs/v8-input-baseline.md)、引き継ぎ状況は [PSD v8 reusable handoff](docs/v8-handoff.md) を参照してください。

- v8 の表情修正スクリプトはありますが、必要な入力素材がないため現状では実行・再検証できません
- 髪・頭部、首・衣装、袖・腕・手などの美術修正、統合、視覚監査は未完了です
- Live2D Cubismのモデリング・リギングも未実施です

過去の v6 の性能改善と検証範囲は [PSD生成の性能レビュー](docs/psd_performance_review_20261018.md)、v8 表情修正の過去の報告は [履歴資料](docs/v8-expression-psd-repair.md) として残しています。どちらも現在の v8 リリースが検証済みであることを示すものではありません。

## 再生成・監査

Python 3.10以降。無料のオープンソースライブラリを利用します。

```bash
python -m pip install -r requirements.txt

# 元画像がなくても動くPSDエクスポート回帰テスト
python tests/test_psd_writer.py
```

素材の供給後も、次のゲートを順番に満たす必要があります。

1. [input baseline](docs/v8-input-baseline.md) に従って入力を検証し、`python scripts/repair_expressions_v8.py` で表情修正を別の候補PSDへ再生成して、承認済みPSDを上書きせずに比較・確認する
2. 髪・頭部、首・衣装、袖・腕・手・隠れた肌の各領域の素材を完成させ、レビューする
3. [integration worklog](docs/v8-integration-worklog.md) に従って編集可能なPSDへ統合し、初期画像と表情を維持できていることを確認する
4. [visual audit worklog](docs/v8-visual-audit-worklog.md) に定めた全成果物を生成し、視覚監査する

入力がない現状では最初のゲートを通過できず、表情修正コマンドを正常完了させることも v8 の出力を保証することもできません。
