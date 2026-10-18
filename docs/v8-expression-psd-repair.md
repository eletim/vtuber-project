# PSD v8 表情パーツ修正

> **履歴資料:** この文書は過去に報告された作業内容と結果を記録したものです。現在のリポジトリには検証に必要なPSD・元画像・表情参照画像がないため、以下の結果は独立に再検証されていません。現在のブロッカーと必要な入力は [`v8-input-baseline.md`](v8-input-baseline.md) を参照してください。

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

元画像・v7のPSD・承認済み閉じ目／口の元画像は、過去にはチャット内の `koma_v8_psd_expression_fix_bundle.zip` に同梱したと報告されていましたが、現在のチェックアウトでは入手できません。入力が供給され、[`v8-input-baseline.md`](v8-input-baseline.md) の条件を満たすまでは再生成できません。

必要な入力：

```
assets/original/koma_confirmed.png
assets/parts/v7/koma_illustrated_underlayers_v7.psd
assets/expression_references/eyes_closed_mouth_open.png
assets/expression_references/eyes_open_mouth_closed.png
```

想定出力：`assets/parts/v8/koma_expression_repaired_v8.psd`、`koma_expression_v8.gif`、4状態のPNGと監査JSON。これらは現在のチェックアウトにはありません。

## 未実施

Live2D Cubismのモデリング・変形パラメータ設定は未実施です。過去に生成したと報告されたGIFは、表情差分レイヤーの切り替えプレビューであり、現在は入手できません。髪・衣装の美術的な下地修正は別途残っています。
