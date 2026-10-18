# VTuber Project — 羽月こま

将棋VTuberキャラクターをLive2D化し、将来的に人間/AIモード両方で操作できるようにするプロジェクトです。

## 現在の工程：PSD v3（顔の肌レイヤー修正）

**v1とv2の顔パーツ構造には問題がありました。** 目や口の下に、顔全体へ連続した肌色レイヤーがなかったためです。

v3で、以下の構造に修正しました（上から表示順）：

1. `eye_screen_left.open/.closed` — 左目
2. `eye_screen_right.open/.closed` — 右目
3. `mouth.open/.closed` — 口
4. `skin_shading_under_expressions` — 表情部位の肌色・陰影
5. `face_details_and_front_hair` — 目・口以外の顔・前髪の描画
6. **`face_skin_FULL_beneath_eyes_mouth` — 顔全体を覆う肌レイヤー**
7. 残りの髪・服・身体（顔の目口は下層から除外）

閉じた目・口はレイヤーとして独立し、初期状態では非表示です。開いた目・口の表示が元画像の前景と一致すること、目と口の下に肌レイヤーが存在することを確認しています。

**PSD v3はレイヤー修正版の試作です。** 表情部分の肌やまつ毛の清書、Live2Dのメッシュ・パラメータ・モデリングはまだ残っています。

## ローカル再生成

```bash
python -m pip install -r requirements.txt
# 確定済み画像を assets/original/koma_confirmed.png に保存する
python scripts/build_expression_v3.py assets/original/koma_confirmed.png
```

生成場所：`assets/parts/v3/koma_expression_skin_base_corrected.psd`

元画像、修正PSD、画像プレビューなどのバイナリ成果物は制作ZIPにまとめて渡しています。GitHubにはスクリプトと文書を保存しています。

## 次工程

顔のベースの清書・目口の境界修正後、Live2D CubismでArtMesh・デフォーマ・まばたき・口パクを設定します。デザインの再生成は行いません。
