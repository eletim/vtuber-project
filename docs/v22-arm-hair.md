# 羽月こま v22：頬へ手を添える動きと房別の髪

`b77f2fd6c6c4d1918615f0c6b14b59d2c38be6b4` から作った `codex/koma-v22-arm-hair` の実行版。画面左の腕を肘で曲げ、指先を頬へ添えて下ろす。前髪・横髪・後ろ髪を12房に分け、根元を固定して速度と位相の異なる揺れを追加した。旧チェックポイントは保存したまま。今回の実行用PSDは `koma_articulated_v22.psd`。

## 成果物と起動

- PSD：[`../assets/parts/v22/koma_articulated_v22.psd`](../assets/parts/v22/koma_articulated_v22.psd)。25描画グループ、8表情、元v19のネイティブ構造を非表示バックアップとして内包。保存姿勢は手を上げたバインド姿勢。実行時は下ろした姿勢から始まる。
- 実行モデル：`runtime/model/model.json`、`runtime/model/body_v22/`。コード：`runtime/web/articulated-arm.js`、`hair-rig.js`、`renderer.js` など。
- 動画：[`../assets/parts/v22/motion-review/koma-v22-arm-hair-motion.webm`](../assets/parts/v22/motion-review/koma-v22-arm-hair-motion.webm)。11秒、1304×910、白黒背景の実Chrome描画。旧environment-reviewの動画はv19基準記録であり、この動画とは別。
- 比較画像：`motion-review/arm-five-poses.png`、`all-eight-raised.png`、`video-transition-contact.png`、`isolated-arms-contact.png`。
- 数値記録：`psd-runtime-v22.json`、`hair-export-verification.json`、`motion-review/review.json`、`connection-and-matte-audit.json`、`final-asset-verification.json`。

このPCではリポジトリ内で `./Start-Koma.ps1` を実行し、ブラウザーで `http://127.0.0.1:8766/` を開く。スクリプトはブラウザーを自動操作しない。停止はCtrl+C。既存Pythonを指定する場合は `-Python <実行ファイル>`。依存 `aiohttp` は隣の `.local-python` にあり、新規インストールは起動時に行わない。

画面の「頬に手を添えて戻す」ボタンで一連の動き。「頬に手を添える」スライダーで途中姿勢を調整できる。ボタンは既存のAI制御モードへ切り替えてローカルの演技を実行する。会話AIへの要求ではなく、モデル導入や外部APIは不要。

## 画と構造

元PSD由来の肩の支持部と、画像編集ツールで描いた曲げ腕を組み合わせた。上腕・前腕・手首／手・袖口・袖の内側と折れを含む垂れ布は独立した編集面。前腕・手は長さを保った回転と平行移動で動き、布だけ別の変形面を使う。肩・肘・手首を階層化し、胴体服とスカートに腕の変形を適用しない。旧腕の下に隠れていた服の補完画も固定の胴体レイヤーに置いた。

手と前腕は顔・前髪より手前、肩と上腕はその奥に描画する。すべての表情ベースから選択した可動髪を除去し、目・口の差分画像にも描画後に所有領域マスクを適用する。固定の髪が差分画像経由で復活する経路も遮断した。房同士の境界には小さな動く重なりを設け、固定側には頭皮・肌の補完のみを置く。

新規作画の原本は `assets/parts/v22/sources/` に保持。`bent-arm-imagegen.png` は初期案、`bent-arm-clean-painted.png` は髪や服の混入を除いた腕素材、`hair-skin-reveal-painted.png` は前髪・頬横の髪の下の肌素材。生成画像全体で顔を置換していない。元の承認済み顔、衣装の見えていた領域、v19ファイルは保持した。

## 最終検証

- Node 164件、PythonのHTTPサーバー4件が成功。Pythonテストは制限環境では待機したため中断し、許可されたループバック通信環境で実行して成功した。
- 専用ヘッドレスChromeで8表情×3姿勢×白黒2背景＝48画像。ページエラー0。実アプリのボタンで挙上し、リセットで下がることを確認。
- 元モデルと比較し、全8表情の目2領域と口周辺領域でRGBA差0。髪の所有領域以外の表情ベースも差0。これは検査した領域についての保証であり、顔全域の全動的フレーム比較ではない。
- 腕の0〜1を0.05刻みで21姿勢。半解像度・alpha128以上・100画素以上の連結成分はすべて1。大きな部品の分離はない。テストで骨の長さ、肩固定、胴体・スカートへの非干渉、途中姿勢の連続性も確認。
- 動画を再読込し、0、1.2、1.4、1.6、2、3、5.2、5.4、5.6、6、10秒の11時点をデコード。上げ下げ途中の抜粋を目視した。動画自体にも房の継続した揺れを収録。
- PSDを書き出して独自PSD読込器で再読込し、合成RGBA差0。バインド姿勢のPSDと実WebGL画像を原寸比較：平均RGB差は255段階で約0.0102、差16を超える画素は1,572,528画素中11画素。整数alpha合成とWebGL補間の境界差があるため完全一致とはしていない。
- v19 PSDのSHA256は `0f1d28279d0256f2a7ba860422709041f701dade3becf361c2b54bf5342ba3f4` のまま。最新版PSDのSHA256は `psd-runtime-v22.json` と `final-asset-verification.json` に保存。

## 残る画の限界・未確認

挙上量0.5付近の前腕の輪郭は直線的で、袖口の折れがやや硬い。接続は成立しているが、肘・袖の途中専用作画を追加した完成原画と同じ自然さには達していない。肩と肘は衣装に隠れるため連結成分の検査だけで解剖学的な自然さまでは保証しない。

髪の白いマット・ギザつきと脚の切り抜きは元素材の問題として未修正。元の白画素から20px以上離れた新しい白画素は5時点すべて0だった。ただし細い透明境界は完全にはなくなっていない。元の不透明領域を20px縮小した内部で新たに透明になった画素は0〜4秒で11、26、78、134、215。輪郭移動も含む診断値であり、すべてが欠陥とは限らないが「新規の隙間ゼロ」とは主張しない。赤い診断画像と黒背景動画を保存した。裾の可動域も従来の小さい制限を維持。

カメラ、マイク、このPCでの新規音声合成、会話モデルは未検証。v20音声コードを保持し、v21会話AIのモデル導入は保留。Photoshop/Kritaでの対話的PSD表示は行っておらず、PSD検証は読み書き・合成とブラウザー比較による。ユーザーの表示中の画面や入力は操作していない。

## 環境と保存

Windows build26200、WSL Ubuntu-22.04、Git2.55、Node24.19、同梱Python/Pillow/NumPy/Playwright、既存Chromeを使用。組み込み画像編集ツールで作画。mainのv13から7個のLibrary bundleを順に検証・適用してb77f2fdまで復元済み。詳細は `dell16plus-handoff-v22-checkpoint.md` の履歴記録を参照。

既存HTTPS認証での `git push --dry-run` は対話禁止・パスワード取得不可で失敗。SSHは既存known_hostsに対象ホスト鍵がなく、厳格確認で停止した。認証情報作成・ホスト鍵登録・設定緩和はしていない。GitHub新規ブランチとDraft PRは未作成、mainへのマージなし。ローカルブランチとコミットを成果として保存する。

## 再生成

Pythonで `scripts/build_articulated_arm_v22.py` → `scripts/build_hair_v22.py` → `scripts/export_psd_v22.py` の順。腕スクリプトは保存済み元モデルから作り直すため順序を守る。原本は変更しない。

ブラウザー検証は `PYTHON`、`PYTHONPATH`、`PLAYWRIGHT_MODULE`、`CHROME_PATH` を既存実行環境へ設定し、`node scripts/review_v22_motion.mjs`。ポート18770の検証用サーバーを自身で起動・終了する。`JOINT_ONLY=1` は腕21姿勢と旧髪比較、`AUDIT_ONLY=1` は顔・実アプリ・バインド照合。動画デコードは `node scripts/verify_v22_video.mjs`、数値集計はPythonの `scripts/audit_v22_connections.py` と `scripts/summarize_v22_review.py`。
