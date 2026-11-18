# dell16plus 引継ぎ・v22 作画チェックポイント

この保存は制作途中です。新しい腕・髪のモーション完成版ではありません。

## 復元と環境

- 作業領域: `C:\Users\rext7\Documents\Codex\2026-10-22\task\vtuber-project`
- Windows build 26200、WSL2 Linux 6.6.87.2、Ubuntu-22.04 を確認。
- Git 2.55.0.windows.5、Node v24.19.0、同梱 Python 3.12、Pillow、NumPy、Playwright を利用可能。
- Chrome と Edge の実行ファイルを確認。専用ヘッドレス Chrome の WebGL 起動に成功。ユーザーの画面・既存ブラウザーセッションは操作していない。
- Krita/GIMP は調査した標準インストール先に存在しない。全ディスク検索はしていない。
- `aiohttp` とその依存だけを作業領域直下の `.local-python` に追加。新しい AI モデル・有料 API・認証情報は導入していない。
- GitHub main は `faccb9cd68cd0942545fa46d143bd09c2e59518b`。
- Library の7 bundleを指定順に `git bundle verify` / `git fetch` し、`b77f2fd6c6c4d1918615f0c6b14b59d2c38be6b4` から `codex/koma-v22-arm-hair` を作成。`git fsck --connectivity-only` 成功。
- v19 PSD SHA256: `0f1d28279d0256f2a7ba860422709041f701dade3becf361c2b54bf5342ba3f4` と完全一致。
- Windows の Library 転送処理は `os.setxattr` 非対応で失敗したが、同じ公式処理を WSL Python で実行し、拡張属性付きで全 bundle を取得済み。bundle はリポジトリの隣の `bundles` に保持。
- GitHub の読み取りは成功。書き込み確認の `git push --dry-run` は `Cannot prompt because user interactivity has been disabled / unable to get password from user` で失敗。リモート更新なし。新規認証は作成していない。

復元順の tip: `d80adf5` → `78ede7b` → `e70184f` → `0fbe1ea` → `83fb688` → `c92ef24` → `b77f2fd`。

## 保存物

- `assets/parts/v22/koma_v22_authoring_checkpoint.psd`: 元 v19 を非表示のネイティブバックアップとして保持。表示合成は元 PSD と RGBA 完全一致。既存7表情フォルダー＋通常表情を保持。
- 両腕の上腕・前腕袖・手首／手の編集用分離、および髪の領域分割の試作。**切断境界はまだ関節用の重なりを持たず、そのまま動かしてはいけない。**
- `assets/parts/v22/sources/bent-arm-imagegen.png`: 組み込み imagegen の曲げ腕参考作画。全身を置き換えるための承認済み素材ではない。
- `assets/parts/v22/sources/bent-arm-extracted-study.png`: 上記から腕周辺を抽出した試作。肩付近に髪、袖下端に衣装の画素が残るため、その除去と隠れ部分の追加作画が必要。
- PSD 内の曲げ腕試作は非表示。手首／手・前腕と袖・上腕・袖内側／折れの別レイヤー。承認済みの顔や胴体服を新規画像で置き換えていない。
- `assets/parts/v22/authoring-checkpoint.json`: SHA256 と一致検証、未完項目。
- `assets/parts/v22/source-layer-review.png`: 既存髪レイヤーの構造確認。
- `assets/parts/v22/environment-review`: 復元版の実 Chrome 黒白背景と4秒動画。動画名に明示したとおり **v19 基準動画であり、新規 v22 モーションの動画ではない**。

## 検証

- PSD を保存後に再読込し、表示合成の変更 RGBA 値数 = 0。
- `node --test --test-reporter=dot runtime/tests/*.test.js` 成功。
- Windows checkout の CRLF に対応するため `control-flow.test.js` の import 除去正規表現を `\r?\n` 対応に修正。実行コードには変更なし。
- ヘッドレス Chrome で復元モデルの7描画レイヤー、WebGL描画、黒白スクリーンショットを確認。ページエラーなし。
- 声・カメラ・マイク・会話モデルはこの環境では検証していない。モデル導入は保留のまま。

## 未完の作業

1. 曲げ腕の肩付近の髪／袖下端の衣装混入を除去し、肩・肘・手首の接続、袖内側と折れ、隠れ部分を作画。
2. 上腕・前腕・手の長さと関節位置を画像上で確認し、独立した変換階層を実装。胴体服へ腕の変形を伝えない。
3. 髪の試作分割を房の輪郭へ合わせ、動いた下に見える肌・髪の作画を追加。現在の単なる領域分割は完成版ではない。
4. 8表情のベースを、顔・固定頭部と可動髪が重複しない構造で書き出す。今回 runtime の表情ベースは未変更。
5. `model.json`、`body-rig.js`、`render-plan.js`、`renderer.js` に独立関節と房ごとの遅れを実装。
6. 途中姿勢、根元固定、黒白背景、全表情との組合せを実ブラウザーで検証し、新規モーションのサンプル動画を作成。
7. 既存 Git 認証で push が可能になった場合のみ新規ブランチへ保存し Draft PR を作成。main はマージしない。

## 使用した画像生成プロンプト

組み込みツールを使用。Windows 絶対パスを渡す方法はパスの解析エラーで実行されず、表示済みの元画像を参照する方法で成功した。

> Edit target: most recent provided VTuber character illustration. Preserve exact identity, skin colors, brown hair, costume design and all non-arm regions. Change ONLY screen-left arm: bend elbow naturally and raise relaxed hand beside cheek. Upper arm angles down and slightly outward from original shoulder; forearm points up. Keep same white double bell ruffle sleeve, brown ribbon and orange tails; author believable inner sleeve and compressed elbow folds. Never stretch whole arm or pull torso. Keep image framing and original proportions, transparent background, no text. This painted pose is a source for native PSD articulation, not replacement face art.

## 再実行

PSD: 同梱 Python で `scripts/build_v22_authoring_checkpoint.py`。既存ファイルに触れず v22 のチェックポイントだけを再生成する。

ブラウザー: `scripts/verify_dell_headless.mjs`。環境変数 `PYTHON` に同梱 Python、`PYTHONPATH` に作業領域 `.local-python`、`PLAYWRIGHT_MODULE` に同梱 Playwright、`CHROME_PATH` に Chrome 実行ファイルを指定。ポート18769にこのプロセス専用サーバーを起動し、終了時に閉じる。
