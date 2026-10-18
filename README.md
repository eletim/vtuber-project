# VTuber Project — 羽月こま

確定済みの将棋VTuberキャラクターを、なるべく無料・AI主体でLive2D化するためのリポジトリです。人間モードとAIモードは後続工程です。

## PSD v2：閉じ目・閉じ口を改善

- 確定したキャラクター画像（1086×1448）は変更していません。
- **左右の閉じ目と閉じ口だけを描画し直しました。** その他の口形や表情は今回追加していません。
- 顔周辺の色を参照して、目と口の下に隠れている肌を近似的に補完しています。
- **33レイヤー** の編集可能なPSDを生成します。
- 初期表示は開いた目と口で、元画像の不透明領域とピクセル単位で一致することを確認しています。
- `.closed` レイヤーはPSD上で非表示、`.open` レイヤーは表示です。閉じた表情を見るときは該当部位の `.open` を隠し、`.closed` を表示してください。

閉じ目・口の描画と肌の補完はまだ試作段階です。Live2D CubismのArtMesh、パラメータ、変形や隠れた部位の清書は未実施です。

## 生成手順

Python 3.10以降を利用します。

```bash
python -m pip install -r requirements.txt
# 確定画像を assets/original/koma_confirmed.png に置く
python scripts/build_expression_v2.py assets/original/koma_confirmed.png
```

出力先 `assets/parts/v2/`：

- `koma_expression_refined.psd` — 編集可能な表情レイヤーPSD
- `initial_open_preview.png` — 元の初期表情
- `closed_eyes_preview.png` — 両目を閉じた状態
- `closed_mouth_preview.png` — 口を閉じた状態
- `closed_both_preview.png` — 両方を閉じた状態
- `expression_comparison.png` — 四状態の比較
- `build_info.json` — 現在の制約・レイヤー数

確定画像とPSD等のバイナリは会話内のZIPに収録し、GitHubには生成コード・設定・ドキュメントをコミットしています。

## 次の工程

表情レイヤーの品質確認後、元画像のパーツ境界と隠れた部分を補修し、Live2D Cubismでモデル化します。
