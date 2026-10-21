# PSD v8 表情パーツ修正

> **履歴資料:** この文書は過去に報告された作業内容と結果を記録したものです。検証に必要なPSD・元画像・表情参照画像は現在のリポジトリに登録され、[`v8-input-baseline.md`](v8-input-baseline.md) の入力検証に合格しています。以下の過去の結果を現在の成果として扱うには、別の候補へ再生成し、改めて比較・目視確認する必要があります。

## 内容

v7 の PSD 49レイヤーをそのまま継承し、承認済みの表情イラストから**閉じ目（左右）と閉じ口**を正確な座標に切り出して差し替えました。キャラクター全体の新規画像生成は行っていません。

- `eye_screen_left.closed` — 左閉じ目
- `eye_screen_right.closed` — 右閉じ目
- `mouth.closed` — 閉じ口

閉じたレイヤーは初期非表示です。使用時は、必要な `.closed` を表示します。対応する `.open` は元画像のまま残し、閉じたパーツを上から被せます。両方閉じた状態では口のレイヤーを最前面に置き、重なり不具合を修正しました。

## 過去に報告された確認結果

- PSD独立再読み込み：49レイヤー
- 初期表情と確定画像との差分：RGB 0画素、アルファ0画素
- 4状態：通常／閉じ目／閉じ口／両方閉じ
- 各状態で変更範囲外の画素変化0、透明穴0
- PSDから再合成したGIFプレビューを生成したとの報告

## 再生成

`python scripts/repair_expressions_v8.py`

元画像・v7のPSD・承認済み閉じ目／口の元画像は、現在のチェックアウトに通常のGit blobとして登録されています。再生成前に `python3 scripts/validate_approved_assets.py` を実行し、[`v8-input-baseline.md`](v8-input-baseline.md) の検証を維持してください。再生成先は別の候補とし、承認済みPSDを上書きしません。

必要な入力：

```
assets/original/koma_confirmed.png
assets/parts/v7/koma_illustrated_underlayers_v7.psd
assets/expression_references/eyes_closed_mouth_open.png
assets/expression_references/eyes_open_mouth_closed.png
```

現在の再生成先：`assets/parts/v8/koma_expression_repaired_v8_candidate.psd`、`koma_expression_v8.gif`、4状態のPNGと監査JSON。候補PSDは、登録済みの承認済み `assets/parts/v8/koma_expression_repaired_v8.psd` を上書きせず、比較検証するための別ファイルです。候補PSDと4状態の個別PNGは現在のチェックアウトにはありません。

## 未実施

Live2D Cubismのモデリング・変形パラメータ設定は未実施です。登録済みのGIFは表情差分レイヤーの切り替えプレビューであり、Live2Dモデルの動作確認ではありません。髪・衣装の美術的な下地修正は別途残っています。
