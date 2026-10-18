# VTuber Project — 羽月こま

将棋をテーマにしたLive2D VTuber制作プロジェクトです。将来は人間操作とAI操作を切り替えられる構成を目指します。

## 現状（PSD v0）

確定済みのキャラクター画像（1086×1448）を、顔・髪・目・口・衣装などの **26レイヤー** に大まかに分割し、読み込み確認済みのPSD初稿を作成しました。画像の見た目を保ったままレイヤーごとに分けられています。

**注意:** 現在のPSDは大まかなポリゴン分割です。パーツ境界に周辺部位の画素が混ざる箇所があります。隠れた部位の描き足し、まぶた・口の差分、変形用メッシュは未作成のため、**Cubismで自然に動く完成モデルではありません**。

## 再生成

Python 3.10以降で、以下のコマンドを実行します。

```bash
python -m pip install -r requirements.txt
# 確定画像を assets/original/koma_confirmed.png に配置
python scripts/build_psd.py
```

出力先は `assets/parts/v0/` です。

- `koma_parts_draft.psd` — 名前付き編集可能レイヤー
- `flattened_transparent.png` — 背景透過した合成画像
- `part_manifest.csv` — 各パーツの画素数
- `build_info.json` — 生成条件と現在の制約

GitHubには分割座標 `config/koma_regions.json` と再生成プログラムを保存しています。PSD本体と確定画像は別途提供する制作成果物です。大容量バイナリをGitに保存する場合はGit LFSなどを使用します。

## 今後

1. 不正確な境界の修正と隠れた部位の描き足し
2. まばたき・口パクの表情差分とLive2D Cubismのメッシュ作成
3. 人間モード・AIモードの制御系を接続

方針：無料ツールとAI支援を優先。確定デザインについて追加の画像生成はしません。
