# v10 — PSD統合と人間・AI操作（2026-10-20）

## 到達点

1. v9の表情、PR #22の袖・腕・手を統合し、66レイヤーのPSDを作成。
2. 髪の隠し状態の固定残像と、ベスト下の白/灰色パッチを描画素材で修正。
3. PSD由来素材を動かす30×40格子のWebGLメッシュと操作画面を実装。
4. 同じパラメータに人間入力（顔追跡・マイク・スライダー）とAI入力（HTTP/WS・発話要求・音声ファイル）を接続。

Cubism Editorでのアートメッシュ/デフォーマ作成とmoc3出力は未完了。
この環境はLinuxで、Cubism EditorのWindows/macOSアプリを操作できない。
公式の[動作環境](https://www.live2d.com/en/cubism/download/spec/)と[ファイル形式](https://docs.live2d.com/en/cubism-editor-manual/file-type-and-extension/)を確認した。
現在のモデル形式は `koma-part-mesh-1`。本物のCubism model3.jsonに見せかけたファイルは作っていない。

## PSDと描画

`assets/parts/v10/koma_integrated_v10.psd`。入力はv9の54レイヤーPSD。
PR #22の描画PNG、設定、コード、旧63レイヤー候補、テストを取得して保持した。
腕・袖の10レイヤーと、髪/ベストの描画下地2レイヤーを追加した。

既存候補の髪・ベスト非表示状態に対し、画像編集で下に見える衣装・肩・肌を描いた。
採用するのは対象パーツの下に隠れている範囲。通常の全身・顔・衣装を生成素材に置き換えていない。
旧マスク外に固定されていた髪の半透明断片は、描画素材で背景になっている範囲を確認して可動髪に再割り当てした。
通常RGBA差分は0。左右個別を含む8表情もv9と全画素一致。

`hair_review.png`、`vest_review.png`、`sleeves_review.png`、`hands_review.png` は通常・非表示・6px移動の比較。
髪を隠した短い髪と肩は、隠れ部分の表示確認であり、通常の髪型の変更ではない。

### 未完了の品質

- 通常姿勢の髪外周には、旧抽出由来の明るい縁・不規則な抜けが残る。
- 頭頂、髪飾り、前髪の個別変形はCubismでの最終確認が必要。
- 大きな腕/袖の回転、髪物理、顔の立体的な角度は未作成。
- `visual_review.json` はPSD全体を `NOT_READY` と記録している。

## 実行版

`scripts/run_runtime.py` で初回の追跡依存を照合/取得し、127.0.0.1:8766で起動。
MediaPipe Tasks Visionは `0.10.22-rc.20250304`、Face Landmarkerは公式float16モデル。
依存URLとSHA-256は `runtime/vendor-manifest.json` に固定。バイナリはGitに重複保存しない。
[Google公式ガイド](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/web_js)のAPIを使用した。

PSDの目口を隠した肌と6つの差分を、元座標・元画素でランタイムへ出力する。
ベースと表情は同じメッシュで変形するため、顔を動かしても表情パーツが置き去りにならない。
既存イラストは開閉2状態なので、途中を半透明合成せず、線を不透明なまま切り替える。
顔の向きは小さな2D変形で、横顔を新たに描いたものではない。

### 操作API

| 操作 | 経路 | データ例 |
|---|---|---|
| 状態取得 | GET `/api/state` | モード・パラメータ |
| モード切替 | POST `/api/mode` | `{"mode":"ai"}` |
| パラメータ指示 | POST `/api/control` | `{"source":"ai","parameters":{"ParamAngleX":8},"ttl_ms":2000}` |
| 発話要求 | POST `/api/speech` | `{"text":"こんにちは"}` |
| 状態購読・入力 | WS `/ws` | controlと同じ入力、stateイベント |

`ParamEyeLOpen` はキャラクター左目（画面右）、`ParamEyeROpen` は画面左。
入力所有者を切り替え、非アクティブなHTTP入力は409で拒否する。
切替時に送信中だった旧WSフレームは無視し、カメラ・マイク・音声再生を停止して姿勢を初期化する。
外部指示の有効期間は標準2秒。途切れると通常状態に戻す。

文字列読み上げは端末のSpeechSynthesisを利用し、口は発話中の推定タイミングで切り替える。
音声ファイルとマイクではWeb Audioの実際のRMSを使う。これらを同じ精度のリップシンクとは説明しない。
AIが操作できる接続口を提供するが、会話生成、LLM接続、自律配信スケジューラは未実装。

## 検証

- `tests/test_integrated_v10.py`: 66レイヤー、通常RGBA、Pillow統合画像、8表情、ランタイム画像と座標。
- 既存の袖/腕/手テスト: 旧成果の形状・連続性・所有範囲・再生成。
- `tests/test_runtime_server.py`: 入力所有権、数値範囲、異常入力、期限切れ、WS配信。
- `runtime/tests/controls.test.js`: 左右独立の顔表情、口の音量、補間。
- `runtime/tests/e2e.mjs`: 実Chrome HeadlessのWebGL、4表情、外部AI指示、音声、顔追跡、マイク、モード切替、字幕、390px表示。

E2Eでは、Google MediaPipeの公開portrait画像をY4Mにしたテスト映像とサイン波WAVを、ブラウザのfake-deviceへ入力した。
MediaPipe WASMの実推論とgetUserMedia/Web Audio/HTTP/WS/WebGLを通している。追跡器の返値はモックしていない。
ユーザーの物理カメラ/マイクと、日本語TTSの実際の音声出力は未検証。
公開portraitや、その人物が写る検証スクリーンショットはプロジェクトに同梱しない。

`runtime_e2e.json` に結果、`runtime_motion.gif` にAI API操作中の実際のWebGLフレーム、`control_room.png` に操作画面を保存した。
いずれも `assets/parts/v10/` にある。

## Cubismへの引き継ぎ

`config/cubism_rig_v10.json` はPSDのパス、パラメータID/範囲、回転中心、表情レイヤー対応を保存する設定資料。Cubismプロジェクトそのものではない。

1. 外周マットと個別パーツの描画を仕上げる。
2. EditorでPSDを読み込み、頭/体のデフォーマとパーツごとのアートメッシュを作成。
3. 目口の中間形状、角度キー、髪/袖物理を作成。
4. moc3、model3.json、テクスチャを正式出力し、Viewerで確認。
5. 同じ入力パラメータをCubismランタイムへ接続する。

## 描画素材の来歴

組み込み画像編集を使用。保存PNGからの再ビルドに画像生成は不要。

ベスト: `vest_hidden_painted_source.png`。既存PSDのベスト非表示状態 `(130,450,990,1400)` を編集。
残存ラペル・チェック襟・コート裾・白灰色ポリゴンを除き、同じ白ブラウスとチェックのコルセット/スカートを続けて描く指示。
肩・袖・腕・リボン・ペンダント・ベルト・裾・髪・ポーズ・クロップを維持し、新衣装や新キャラを作らないと指定。

髪: `hair_hidden_painted_source.png`。横髪/後ろ髪非表示状態 `(0,0,1086,950)` を編集。
頬・首・肩に残る長い横髪/後ろ髪と灰/緑の切り抜き断片だけを除き、その下の顔輪郭・耳・首・肩・襟・ベストを描く指示。
頭頂・前髪・編み込み・髪飾り・表情・顔形状・ポーズ・衣装・背景を維持し、新キャラを作らないと指定。

正確なプロンプト全文と描画素材のSHA-256は `assets/parts/v10/painting_provenance.json` に保存。
袖の旧候補の手首境界1画素 `(221,1213)` は、Pillowのポリゴン描画差に依存しないよう明示し、旧PSDの各レイヤーとの画素一致を確認した。圧縮方式のバイト列ではなくデコード後のレイヤーを照合する。
