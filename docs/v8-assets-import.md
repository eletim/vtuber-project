# PSD v7/v8素材のGit登録

## 状態
承認済みバイナリは `dev/v0.3.0` に取り込まれています。PSDを含む9ファイルは、Git LFSを必要としない通常のGit blobとして管理します。

対象は `koma_v8_psd_expression_fix_bundle.zip` に含まれる9ファイルで、SHA-256値は [v8-approved-assets.sha256](v8-approved-assets.sha256) に記録しています。

- 2つのPSD、確定PNG、表情参考PNG、GIF、比較PNG、JSON、README：通常のGit
- ソースZIPそのものはコミットしない（重複回避）

## 導入

既存のリポジトリがクリーンな状態のとき実行します。Git LFSの導入は不要です。

```bash
bash scripts/import_v8_assets.sh /path/to/vtuber-project /path/to/koma_v8_psd_expression_fix_bundle.zip
```

あらかじめ `dev/v0.3.0` から専用の作業ブランチを作成してください。スクリプトは承認済み9ファイルのSHA-256を確認し、異なる既存ファイルを上書きせず、現在のブランチへステージします。自動commit・pushは行いません。

このリポジトリはPublicなので、PSDを含む素材も公開されます。すでに了承された公開範囲を越える設定変更はしません。

## 導入後の確認

```bash
git check-attr filter -- assets/parts/v8/koma_expression_repaired_v8.psd
git cat-file -s HEAD:assets/parts/v8/koma_expression_repaired_v8.psd
git status --short
git log -1 --oneline
```

`filter: unspecified` と実ファイル相当のサイズが表示されれば、PSDはLFSポインタではなく通常のGit blobです。

PRで9つの素材ファイルの追加を確認し、その後に対象の開発ブランチへ統合します。取り込み後のAWMでは、`assets/original/`、`assets/expression_references/`、`assets/parts/v7/`、`assets/parts/v8/` を参照できます。

素材の存在確認が済むまでは、AWMのblocked状態やPSD制作完了判定を変更しません。
