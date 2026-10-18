# VTuber Project — 羽月こま

確定した将棋VTuberキャラクターをLive2D化するプロジェクトです。将来的に人間モードとAIモードを切り替えられるようにします。

## 現在の成果（PSD v1）

- キャラクターデザイン確定（1086×1448 px）。デザイン変更・追加画像生成はしません。
- 26レイヤーの初期PSD（v0）を作成。
- **v1では左右の目と口の開閉用レイヤーを追加**。計32レイヤーのPSDと12フレームの簡易まばたき・口パクGIFを生成しました。
- v1のPSDはPhotoshop形式として再読み込みでき、初期表示が確定画像とピクセル単位で一致することを検証しています。

**制作ステータス：表情素材の初稿。** 閉じ目と閉じ口は画像処理で合成した暫定描画で、精度改善が必要です。パーツ分割もまだ粗く、隠れた髪・顔の描き足しや、Cubismのメッシュ・デフォーマ・パラメータ・書き出しは未実施です。GIFは画像レイヤーの切り替えテストであり、Live2Dモデルの動作ではありません。

## 再生成

Python 3.10以降で実行します。

```bash
python -m pip install -r requirements.txt
# 確定画像を assets/original/koma_confirmed.png に配置
python scripts/build_psd.py assets/original/koma_confirmed.png
python scripts/build_expression_psd.py assets/original/koma_confirmed.png
```

v1の出力は `assets/parts/v1/` です。

- `koma_expression_draft.psd` — 開閉レイヤーを含むPSD
- `initial_open_preview.png` — 初期状態
- `blink_closed_preview.png` — 閉じ目・閉じ口の仮描画
- `blink_talk_preview.gif` — 表情切り替えテスト
- `build_info.json` — 生成情報と限界

素材画像・PSDなどのバイナリはチャット側で制作データとして渡しています。現在、リポジトリに入れているのはスクリプト・設定と文書です。画像ファイルをGitで追跡する場合はGit LFSなどを検討します。

## 次の工程

1. 目・口の閉じた形の自然さ、色と輪郭の継ぎ目を改善する
2. 顔・髪・衣装の分割境界を整え、隠れた部分を補完する
3. Live2D CubismでArtMesh・デフォーマ・顔の回転、まばたきと口パクを作る
4. 人間・AIの制御接続を作る

作業の方針は無料ツールとAI主体です。
