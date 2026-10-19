# PSD v7/v8素材のGit登録

## 状態
このブランチは **素材をGitで共有するための準備** です。承認済みバイナリはまだリポジトリへプッシュされていません。

対象は `koma_v8_psd_expression_fix_bundle.zip` に含まれる9ファイルで、SHA-256値は [v8-approved-assets.sha256](v8-approved-assets.sha256) に記録しています。

- 2つのPSD：Git LFS
- 確定PNG、表情参考PNG、GIF、比較PNG、JSON、README：通常のGit
- ソースZIPそのものはコミットしない（重複回避）

## 導入

Git LFSが利用できるPCで、既存のリポジトリがクリーンな状態のとき実行します。

```bash
# Ubuntu: 未導入の場合のみ
sudo apt install git-lfs

bash scripts/import_v8_assets.sh /path/to/vtuber-project /path/to/koma_v8_psd_expression_fix_bundle.zip
```

スクリプトは承認済み9ファイルのSHA-256を確認し、異なる既存ファイルを上書きせず、専用の `assets/import-v8` ブランチにプッシュします。main や `dev/v0.3.0` を直接変更せず、強制pushもしません。

このリポジトリはPublicなので、LFSに登録したPSDを含む素材も公開されます。すでに了承された公開範囲を越える設定変更はしません。

## 導入後の確認

```bash
git lfs ls-files
git status --short
git log -1 --oneline
```

PRで9つの素材ファイルの追加を確認し、その後に `dev/v0.3.0` へ統合します。取り込み後のAWMでは、`assets/original/`、`assets/expression_references/`、`assets/parts/v7/`、`assets/parts/v8/` を参照できます。

素材の存在確認が済むまでは、AWMのblocked状態やPSD制作完了判定を変更しません。
