# 羽月こま — VTuber Project

人間とAIの両方で操作するVTuberの制作プロジェクトです。

## 現在の成果（新しい文章の音声合成 v20／部位別の PSD v19）

- 元の PSD を保持し、左右の腕・袖・手、胴体服、スカートを分離した PSD と実行用画像。8 表情と目・口の開閉差分を保持。
- 元の通常表情と左右個別を含む 8 通りの旧来の目・口の組み合わせは、v9 と RGBA 全画素で一致。
- WebGL操作画面。まばたき・口の開閉、顔と体の変形、呼吸に対応。
- 身体は腰を支点に動き、左右の腕とスカートは独立した描画面を使用。腕の入力で胴体服を引っ張らず、スカートは腰を固定して裾が遅れて追従します。
- 人間: カメラの顔追跡、マイクの音量、スライダー。
- AI: HTTP/WebSocketのパラメータ指示、テキスト読み上げ要求、音声ファイルのリップシンク。
- 透明・グリーン背景と配信用表示。
- AI待機時の揺れ、発話時のうなずき、楽しそう／考え中／びっくりの仕草。
- 口の局所変形を v16 で修正。顔が傾いていても唇の向きと閉じ口の曲線を保ち、縮小時の暗い角・横線や下地の矩形境界を抑えます。元の絵・PSD・頭と身体の動きは変更していません。
- v17 では、v16 で見落としていた「驚き」の閉じ口の薄い灰色の肌を補正。口の線とハイライトを保持し、新しい PSD と実行版の両方に反映しています。
- v18 では、話すときの小さな腕の仕草と肩・上半身の動きを追加。待機時は控えめにし、発話の開始・停止に合わせて自然に動き始め、静まります。v17 の顔と全素材は保持しています。

![以前の操作画面（v10）](assets/parts/v10/control_room.png)

## 文章から新しい音声を合成（v20）

[起動・停止・検証範囲](docs/text-speech-v20.md)。公式VOICEVOX 0.25.2で入力した新しい文章を実合成し、HTTP/WebSocket、操作画面のみへの再生指定、表情・口・仕草の同期を検証しました。停止は合成中にも使え、古い結果や切断後の音声が再開しないようにしています。エンジンの接続確認と、失敗理由の表示も追加しました。

[今回の新しい音声を使った15秒動画](assets/parts/v20/koma-v20-fresh-speech.mp4) と [新規合成の検証記録](assets/parts/v20/runtime-fresh-speech-verification.json)。動画は実行版と同じ計算のオフライン描画で、ブラウザ操作の録画ではありません。実ブラウザのGUI・スピーカー出力は未検証です。v19の画像・PSDとモーション計算は変更していません。

AIの文章生成機能はまだ接続していません。現在のAIクライアントは外部プログラムから文章・表情・停止を渡すためのAPIであり、会話モデルやAPIキーは設定していません。

## 腕・胴体服・スカートの構造を分離（v19）

v18 の腕の動きが胴体服へ伝わる問題を、変形量の調整ではなく PSD 素材と実行時の描画面の分離で修正しました。新しい PSD は `assets/parts/v19/koma_separated_body_v19.psd` です。
[起動と使い方](docs/separated-body-v19.md) と [部位別描画・境界処理の説明](docs/body-sampling-v19.md)。元の v17 PSD と v18 の動画・素材は履歴として保持します。

確認動画は、胴体を固定した腕の単独動作、腰を固定したスカートの単独動作、音声付きの自然な動きを順に示します。実行版と同じ計算を使うオフライン OpenGL 再描画で、ブラウザー操作の録画ではありません。裾は既存素材で覆える控えめな範囲に制限し、以前からの脚の切り抜きや髪の外周マットを直したものではありません。

## 腕と身体の仕草（v18）

[起動と使い方](docs/arm-body-motion-v18.md)。v18 時点では PSD を変更せず、`assets/parts/v17/koma_expression_skin_v17.psd` を使用していました。
修正したのは実行時の動かし方です。袖・手を切り離さない控えめな仕草であり、大きな腕上げや手指の個別操作ではありません。

42 秒の動画 `koma-v18-arm-body-motion.mp4` は別添の納品ファイルです。動画と実行 ZIP は Git bundle に重複格納せず、再生成スクリプトと検証記録を保存します。動画は実行版と同じ計算のオフライン OpenGL 再描画です。

[同条件の動きの比較](assets/parts/v18/koma-v18-diagnostic-motion-sheet.png) と [再生成手順](scripts/video_v18/RERUN.txt)。

## 薄い灰色の口まわりを補正（v17）

v17 時点の PSD は `assets/parts/v17/koma_expression_skin_v17.psd`。
[v17 の使い方・修正範囲](docs/mouth-skin-v17.md) と [口元の肌の比較](assets/parts/v17/review/surprised-before-after.png) を参照してください。
元の v15 PSD と v16 動画・素材は残しています。差分は「驚き」の閉じ口の周囲の肌だけで、元の口の画素、他の 114 レイヤー、頭と身体の動きは保持しています。

42 秒の修正確認動画 `koma-v17-mouth-motion.mp4` は別添の納品ファイルです。[再生成手順](scripts/video_v17/RERUN.txt) と検証記録をソースに含め、復元 bundle が大きくならないよう MP4 の重複格納は避けています。動画は実行版と同じ計算のオフライン OpenGL 再描画であり、ブラウザー操作の録画ではありません。

## 口まわりの修正版（v16）

v15 の中間の口形状には、口だけ水平に近づく問題と、暗い口角が小さな破片のように残る問題がありました。唇の局所座標と表情ごとの閉じ口の曲線を使い、縮小時の画素サンプリングも変更しています。

[v16 の起動・使い方・検証範囲](docs/mouth-rendering-v16.md)。PSD は変更していないため、下記の v15 PSD をそのまま使用します。
[修正後の 42 秒動画](assets/parts/v16/koma-v16-mouth-motion.mp4) と [同時刻の修正前後比較](assets/parts/v16/koma-v16-mouth-before-after.png) を保存しています。頭・身体の動きと音声は旧動画と同一です。動画はオフライン OpenGL 再描画であり、ブラウザー操作の録画ではありません。

## 表情を動かす（v15）

8 表情を操作画面から選び、各表情に対応したまばたき・実音量に連動する口パクで動かせます。
切り替え時は目と口を短く閉じ、閉じ際に表情を切り替えます。顔全体の半透明クロスフェードはしません。
まばたきは描かれた開眼・閉眼の 2 状態を切り替え、口の中間形状は口まわりの狭い範囲だけの局所変形で作ります。にっこりの目は閉じたデザインを保持します。

v15 時点の PSD は `assets/parts/v15/koma_expression_motion_v15.psd`。
[起動・使い方・動画と検証の範囲](docs/expression-motion-v15.md) を参照してください。
v14 のファイルは前段階の静止表情として残しています。

![v15 表情と目・口の開閉](assets/parts/v15/expression_motion_contact_sheet.png)

[42 秒の音声付き動画サンプル](assets/parts/v15/koma-v15-expression-motion.mp4)。実行版と同じ計算を使ったオフライン OpenGL 再描画で、操作画面の録画ではありません。保存済み音声を再使用しています。
[動画の再生成手順](scripts/video_v15/RERUN.txt)。

## 表情コレクション（PSD v14）

元の通常表情を保持したまま、微笑み・にっこり・困り顔・驚き・照れ・不満・考え顔を追加しました。
`assets/parts/v14/koma_expression_collection_v14.psd` の EXP フォルダーを 1 個だけ表示して切り替えます。
元の 66 レイヤーは保持し、7 個の描き下ろし表情レイヤーを追加しています。
各表情は眉・目・口・頬をまとめた顔差分です。新表情ごとの独立した瞬き・口パクや実行画面への反映は含みません。

![表情一覧](assets/parts/v14/expression_contact_sheet.png)

[使い方・検証範囲](docs/expressions-v14.md)。Photoshop 用の選択スクリプトと日本語の説明書も同じフォルダーにあります。
v14 時点の実行版は v10 素材でしたが、v15 で表情用の描画素材と動作を統合しています。

## 起動

Python 3.10以降。Chrome/Edge等のWebGL対応ブラウザを使います。

```bash
python -m pip install -r requirements.txt
python scripts/run_runtime.py
```

ブラウザで **http://127.0.0.1:8766/** を開いてください。
初回だけ顔追跡のモデル/WASMを取得し、SHA-256で照合します。取得後の追跡はローカルで実行します。
カメラ・マイクはボタンを押したときに開始します。
コントロール画面を開いたまま、OBSのブラウザソース等で `http://127.0.0.1:8766/?overlay=1` を表示できます。

## AIから操作

起動したコントロール画面を開いてから実行します。

```bash
python runtime/ai_client.py --demo
python runtime/ai_client.py --say "こんにちは、羽月こまです。"
```

既存のAIプログラムから直接呼べます。

```python
from runtime.ai_client import KomaClient

koma = KomaClient()
koma.select("ai")
koma.pose(ParamAngleX=8, ParamEyeLOpen=0, ParamMouthOpenY=1)
koma.say("次の一手を考えています。")
```

会話AI/LLMそのものはまだ接続していません。
人間/AIの切り替えで前の入力を停止し、外部からの指示が途切れると2秒で通常姿勢へ戻ります。
読み上げはローカルのVOICEVOXを使います（仮音声：VOICEVOX:雨晴はう）。VOICEVOX未起動時は起動案内を表示し、別の声へ自動で置き換えません。音声ファイルとマイクではWeb Audioの音量に合わせて口を動かします。

## PSDと再生成

最新 PSD は `assets/parts/v17/koma_expression_skin_v17.psd` です。元の統合データは `assets/parts/v10/koma_integrated_v10.psd`、静止表情版は v14 に保持しています。承認済み原画と旧PSDは上書きしていません。

次のコマンドは旧版素材の再生成用です。現在の実行用モデルを旧版で上書きするため、v18 を起動するだけなら実行しないでください。v18 は既存の承認済み v17 素材をそのまま使用します。

```bash
python scripts/build_integrated_v10.py
python scripts/export_runtime_model.py
python scripts/build_expressions_v15.py
python tests/test_expressions_v15.py
python tests/test_integrated_v10.py
python tests/test_runtime_server.py
node --test runtime/tests/*.test.js
```

保存した描画素材から再ビルドでき、画像生成を再実行する必要はありません。

## 残っている工程

**正式なCubismモデル（cmo3/moc3/model3.json）は未作成です。** 現在の実行版はPSD由来素材を独自の2Dメッシュで動かしています。
目・口は描画された開閉 2 状態と局所変形を組み合わせて動かします。音素別の口形状、立体的な顔の向き、パーツごとの物理演算は今後の工程です。
元の髪の外周マットにも荒れが残るため、PSD全体を最終美術合格にはしていません。

[制作・検証記録](docs/v10-production-runtime.md) / [身体の動きの修正](docs/body-motion-v11.md) / [Cubism引き継ぎ設定](config/cubism_rig_v10.json)

## 無料音声で発話（v12）

VOICEVOXを起動して `python scripts/run_runtime.py` → 「読み上げ」。日本語音声に合わせて口が動きます。[起動・AI接続・検証](docs/free-voice-v12.md)。仮音声：VOICEVOX:雨晴はう。

## 待機・発話の仕草（v13）

再開時の手順と今回確認した範囲は [v13 起動・確認メモ](docs/v13-recovery-handoff.md) を参照してください。

AI操作時に首と身体が自然に揺れ、発話にうなずき・首かしげなどが付きます。操作画面の「自然な動き」「発話の雰囲気」から指定できます。[使い方とAI API](docs/lively-motion-v13.md)。
