# VTuber Project — 羽月こま

将棋VTuberキャラクターをLive2D化する制作プロジェクトです。人間モードとAIモードの両方に対応させる予定です。

## 現在の工程

確定したキャラクター画像をPSDとしてレイヤー分割しています。**v6 は生成速度とPSD構造監査の改善版**です。

- 35レイヤー。開いた顔の合成は元画像と一致（0画素差分）
- 目、口、髪、衣装、腕、首などの下地を持つ
- PSD書き出しは従来のタイムアウトを解消
- 独立したPSDデコーダによるレイヤー表示・非表示テストを実施

**注意**: 現状の下地画像は自動補完した試作です。レイヤーを非表示にすると色面状の不自然な部分が出るため、Live2D用アートとして完成したわけではありません。Cubismモデリング・リギングは未実施です。

## 再生成・監査

Python 3.10以降。無料のオープンソースライブラリを利用します。

```bash
python -m pip install -r requirements.txt

# チャットで確定したキャラクター画像を以下に保存してから実行
# assets/original/koma_confirmed.png
python scripts/build_psd_v6.py

# PSD本体を再読み込みして初期画像と差分、部位の非表示時の穴を検査
python scripts/audit_psd.py assets/parts/v6/koma_structure_v6.psd

# 元画像がなくても動くPSDエクスポート回帰テスト
python tests/test_psd_writer.py
```

出力：`assets/parts/v6/koma_structure_v6.psd` と監査レポート、比較用画像。

性能の原因、改善策、検証の範囲は [PSD生成の性能レビュー](docs/psd_performance_review_20261018.md) を参照してください。

確定PNGとPSDバイナリは会話内の制作データに同梱しています。GitHubではスクリプト・設定・テストを管理します。
