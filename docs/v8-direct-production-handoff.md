# 羽月こま v8 — 独立した画像監査と制作引き継ぎ

## 現在の成果の位置づけ

AWMの長時間連続実行を前提とせず、現在の成果を継承して人間・AIで画像確認と小さな修正を行う。

- [PR #20](https://github.com/eletim/vtuber-project/pull/20): 髪・頭部のPSD候補。dev/v0.4.0へマージ済み。Review上限時点で横髪・髪飾り・頭頂・後ろ髪の非表示状態に灰色パッチの未解決指摘あり。
- [PR #21](https://github.com/eletim/vtuber-project/pull/21): 首・衣装のPSD候補。dev/v0.4.0へマージ済み。ブラウスを6px動かした際の横切れ線・裾二重線と、ベスト非表示時の灰色くさび・途切れた襟が未解決。
- [PR #22](https://github.com/eletim/vtuber-project/pull/22): 袖・腕・手の63レイヤー候補。レビュー待ちのDraft。腕・袖口の描画PNG、PSD、プレビュー、再生成コード、テストがGit上にある。
- [PR #19](https://github.com/eletim/vtuber-project/pull/19): dev/v0.4.0 → dev/v0.3.0 の統合PR。まだDraftでマージしない。

どのPSDも、Cubismでのリギング済みモデルではありません。PR #20/#21のマージを美術的な完全合格とは扱いません。

## 監査コマンド

```bash
python3 -m pip install -r requirements.txt

# 承認済みソースPSDだけで監査スクリプトを動作確認
python3 tests/test_review_v8_candidate.py

# PR #22がマージ済み・またはその作業ブランチにいる場合
python3 scripts/review_v8_candidate.py \
  --psd assets/parts/v8/koma_sleeves_arms_hands_cleaned_v8.psd \
  --original assets/original/koma_confirmed.png \
  --baseline-psd assets/parts/v8/koma_expression_repaired_v8.psd \
  --out artifacts/v8_visual_review

# 気になる部位だけを短く再監査
python3 scripts/review_v8_candidate.py --groups side_hair_left side_hair_right vest blouse sleeves hands
```

実際の出力は `artifacts/v8_visual_review/` に保存し、承認済み入力PSDを上書きしない。出力には、4表情の元解像度PNG・GIF、パーツごとの元解像度「非表示・移動」画像、3枚を並べたレビュー用画像、測定値を記録する `review.json` が含まれる。

## 重要な検証上の注意

`assets/original/koma_confirmed.png` は**背景を含む不透明RGB画像**であり、PSDは**背景透明**である。両者をそのままRGBA比較すると、背景のアルファ差で不正な失敗となる。スクリプトでは原画との比較は**PSD前景のRGBのみ**、透明領域・アルファは**承認済みPSD v8を基準**に比較する。前景画素とアルファが一致しても、美術的な品質が合格とは限らない。

すべての `group.visual_review` とトップレベルの `visual_review` は自動的に `PENDING`。自動チェックで画像の質を承認しない。

## 未解決の確認項目

1. **髪**：各髪パーツを隠す/移動したときに、灰色の矩形・顔や衣装のコピー・蛍光色・髪の途切れがないこと。
2. **衣装**：ベスト非表示時の左側灰色領域、切れたラペル、ブラウス・腰の裾や重複線を重点的に確認する。
3. **袖・手**：PR #22最新の腕と手首の接合、袖口内部、袖移動・手移動時の重複輪郭と不自然な衣装断片を確認する。素材PNGに存在する余分な描画と、**最終PSD上で実際に露出する描画**を区別する。PR #22は編集済みPSDとテストを含むが、まだレビュー承認なし。
4. **統合・全体**：3領域の修正を同一候補に適用して比較。4表情の崩れがないことを再確認。実画像での不具合が残る場合は修正して再監査。

### 運用上の方針

AWMの継続再試行に頼らず、差分が小さく再現できる単位で作業する。未解決事項は消さず、PSD本体と再生成コードの履歴を維持する。最終的なCubism導入可否は、この画像監査とPSD編集可能性の確認後に判断する。
