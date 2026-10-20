# 羽月こま — 閉じ目・閉じ口 v9（2026-10-20）

## 結果

表情の4状態（通常、閉じ目、閉じ口、両方閉じ）をPSDから再合成して確認した。
閉じ目のまつげ・まぶた、閉じ口の線・口角、両方閉じの組み合わせに、見える隙間・二重線・肌の欠落は確認されない。
目口をすべて隠した顔の肌も実画像で確認し、旧下地の多角形状の色面・境界線を解消した。
今回の表情修正は完了。PSD全体の美術品質、Cubismモデリングの完了を意味しない。

## 継承元と変更

- `feat/v8-independent-visual-audit-20261020`（dev/v0.4.0と同じ先端）の成果を継承。
- 入力PSD: `assets/parts/v8/koma_neck_clothing_cleaned_v8.psd`（53レイヤー）。
- 出力PSD: `assets/parts/v9/koma_expressions_v9.psd`（54レイヤー）。
- 既存PSD・承認済み原画・閉じ目/閉じ口・髪/衣装レイヤーは上書きしていない。
- PR #22 の袖・腕・手のDraft成果はブランチ上に保持し、このPSDには未統合。

v8では閉じた絵を上に被せた4表情は自然だったが、開いた目口を非表示にすると、肌の下地に広い色面と境界線が露出していた。
既存の顔の切り抜きを対象に、画像編集で目・口を除いた肌を描画した。キャラクター全身の再生成・デザイン変更はしていない。
この描画から、既存の目口のマスクとその周辺16px以内だけを採用した。
境界の合成は8pxで接続するが、下地そのものは単色やぼかしによる穴埋めではなく描画素材である。

`face_expression_painted_skin_v9` を目口の下に追加し、通常顔の復元領域を既存の `.open` に格納した。
通常顔は入力PSDとRGBA全画素で一致し、目口以外の既存レイヤーも全画素・表示状態が一致する。
閉じ目・閉じ口のイラストは既存の承認済み差分をそのまま使用する。

## 切り替え

| 状態 | 非表示 | 表示 |
|---|---|---|
| 通常 | 3個の `.closed` | 3個の `.open` |
| 閉じ目 | 左右の `eye_screen_*.open` | 左右の `eye_screen_*.closed` |
| 閉じ口 | `mouth.open` | `mouth.closed` |
| 両方閉じ | 3個の `.open` | 3個の `.closed` |

`face_expression_painted_skin_v9` は表示したまま使う。画面左右はPSDレイヤー名に従う。

## 検証

```bash
python scripts/build_expressions_v9.py
python tests/test_expressions_v9.py
python tests/test_review_v8_candidate.py
python tests/test_psd_writer.py
```

- PSDを独立デコーダで再読み込みし、4状態の再合成と書き出し前の一致を確認。
- PillowによるPSDの統合画像読み込みと通常合成の一致を確認。
- 左右の片目閉じを含む8通りで、アルファの欠落0、対象パーツ範囲外の変化0。
- `four_expressions.png`、各状態の元解像度PNG、顔拡大GIF、`skin_reveal_detail.png` を出力。
- 画像を実際に目視して上記の表情と肌下地を判断。コードのPASSから美術合格を自動判定していない。
- GIFは共通パレットを使用する。
- GitHub転送容量に合わせ、PSDのレイヤーチャンネルをZIP level 9、統合画像をPackBits RLEで可逆圧縮。Pillowによる再読み込み一致も再確認済み。

## 継承した未解決項目

入力の髪・衣装候補は承認済み元絵との前景RGB差分が25,541画素あり、既存監査はFAILになる。
この差分は今回増やしていない。顔のクロップにも髪の境界等の既存差分6,105画素が含まれるため、「元絵との顔全域の差分0」とは報告しない。
髪の外周、髪/衣装の非表示・移動時の下地品質、PR #22の袖・手の統合が次の作業対象。
今回の肌は目口の表示切り替えを確認したもの。大きな変形・中間まばたき・口の連続変形はCubism工程で未検証。

## 描画素材の来歴

`assets/parts/v9/face_skin_painted_source.png` は組み込み画像編集で生成した候補から採用。
入力は承認済み `koma_confirmed.png` の `(305,130,730,480)` を850×700に拡大した顔クロップ。
生成素材を425×350へ戻し、元の座標へ配置する。元データをGitに保存し、再ビルドは画像生成を呼ばない。

使用プロンプト:

> Use case: precise-object-edit. Edit this existing cropped illustration as a Live2D FACE SKIN UNDERLAYER. Remove BOTH eyes completely (irises, whites, lashes, eyelids and all eye outlines), and remove the entire mouth including lip lines and mouth shine. Paint continuous natural blank facial skin where these features were, preserving the existing soft warm blush, detailed skin shading and nose. This is intentionally an eyeless and mouthless underlayer, NOT a new character portrait. Keep exact same framing, dimensions, face silhouette, nose, hair, eyebrows, ears, neck, clothes and colors. No closed-eye lines, no mouth lines, no new objects. The skin must be smooth continuous professionally painted anime skin without patch edges or flat cutout shapes. Preserve every remaining detail exactly.
