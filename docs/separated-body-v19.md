# 羽月こま v19: 腕・胴体服・スカートを独立させる

## 今回の変更

v18 は腕を動かすと隣の胴体服まで引かれる構造でした。v19 はその変形量を弱める修正ではなく、左右の腕・袖・手、胴体の服、スカートを別の画像と描画面に分離しています。PSD と実行版の両方で同じ部位の分離を使います。

- 左右の腕はそれぞれ肩を支点に動き、胴体服の形を引っ張りません。
- スカートは腰位置を固定し、裾だけが身体の動きに少し遅れて揺れます。腕の入力はスカートを変形させません。
- 顔、肌補正、表情、まばたき、口の処理は承認済みの v17 を保持します。
- 元の PSD と素材は残し、新しい PSD を別ファイルとして追加します。

隠れていた胴体・肩は補完画を用意します。元の見えている絵や顔を描き直す変更ではありません。裾の下は既存素材で覆える範囲に制限しています。裾の横移動は元画像で最大 ±3 px の小さな揺れで、大きく翻るスカートや大きな腕上げは対象外です。

## 起動

Python 3.10 以降、WebGL 対応の Chrome / Edge が必要です。

添付サイズの都合で ZIP が 2 つの場合は、`koma-v19-runtime-core.zip` と `koma-v19-runtime-model.zip` の両方を同じ場所へ展開してください。両方の中にある `koma-v19-runtime` フォルダーを統合します。後から展開するフォルダーで先のフォルダー全体を置き換えず、中のファイルを追加してください。最終的に `koma-v19-runtime/runtime/model/model.json` と `koma-v19-runtime/scripts/run_runtime.py` の両方があれば、正しい構造です。画質や素材は完全版 ZIP と同じです。

1. 実行用 ZIP を展開し、`koma-v19-runtime` フォルダーでターミナルを開きます。
2. `python -m pip install -r requirements-runtime.txt` を実行します。
3. `python scripts/run_runtime.py` を実行します。
4. ブラウザーで `http://127.0.0.1:8766/` を開きます。
5. 「音声ファイルでリップシンク」で `samples/koma-free-voice.wav` を選びます。

`python` が見つからない場合、macOS / Linux は `python3`、Windows は `py` を使ってください。初回に顔追跡のモデル / WASM を取得し、固定 SHA-256 で検証します。カメラ・マイクは対応するボタンを押したときだけ開始します。

「自然な動き」を無効にすると自動の仕草は静まります。左右の腕・肩・重心・スカートのスライダーは引き続き操作できます。

## 手動・外部操作

次のパラメーターは `-1` から `1`、通常は `0` です。HTTP / WebSocket からも同じ値を送れます。

- `ParamArmLOpen`: 画面左の腕。正の値で外側。
- `ParamArmROpen`: 画面右の腕。正の値で外側。
- `ParamShoulderY`: 正の値で肩を上げる。
- `ParamBodyShiftX`: 正の値で上半身の重心を画面右へ。
- `ParamSkirtSway`: スカートの裾の左右揺れ。腰は固定。

自然な身体の動きによる裾の遅れと手動入力は安全な範囲で重なります。単独操作を確認する場合は自動の仕草を無効にし、他の値を中立に戻してください。

## PSD と表情

新しい PSD は `assets/parts/v19/koma_separated_body_v19.psd` です。

構造用レイヤーと表情の切り替え方は、同梱の `artwork_controls/使い方.txt` を参照してください。旧素材を保存した非表示のバックアップと、使用する構造グループを同時表示しないでください。

8 表情を保持します。まばたきは描かれた開眼・閉眼の 2 状態で、まぶたの連続変形ではありません。口の向きと肌色は v16 / v17 の修正を引き継ぎます。

## 確認動画と限界

48 秒の確認動画には、胴体を止めた左右の腕の単独操作、腰を固定したスカートの単独操作、その後の音声付きの自然な動作を含みます。保存済み音声の再使用で、新しい台詞を合成していません。

音声クレジット: VOICEVOX:雨晴はう。配信・動画公開時もクレジットを表示してください。

動画は実行版と同じ JavaScript の部位別ジオメトリを使ったオフライン OpenGL 再描画です。ブラウザー操作の録画ではありません。この環境では実ブラウザー E2E、実機カメラ / マイク、OBS、Photoshop 本体の操作は未確認です。

正式な Live2D Cubism データではなく、PSD 素材を独自の WebGL 2D メッシュで動かす実行版です。手指の個別操作、大きな腕上げ、身体を大きく横に向ける動作は含みません。以前からの脚部切り抜き・髪の外周マットを直したものではありません。

## ソース側での再生成・検査

リポジトリのルートで実行します。実行 ZIP には通常運用に不要な PSD 作成依存関係を含めていません。

```bash
python -m pip install -r requirements.txt
python scripts/build_separated_parts_v19.py
python scripts/integrate_body_v19.py --sampling coverage-2x
python tests/test_separated_parts_v19.py
python scripts/verify_separated_v19_preservation.py
node --test runtime/tests/*.test.js
python -m unittest discover -s tests -v
python scripts/package_runtime_v19.py /任意の新しい出力フォルダー
python scripts/verify_runtime_bundle_v19.py /任意の新しい出力フォルダー/koma-v19-runtime.zip
python scripts/split_runtime_bundle_v19.py /任意の新しい出力フォルダー/koma-v19-runtime.zip
```

PSD 再生成は保存済みの元画像・補完画像から行い、新しい画像生成や外部送信はしません。出力は v19 専用フォルダーです。元の v17 PSD は変更しません。実行 ZIP の作成は同名の既存出力フォルダーを上書きしないため、別の出力先を選んでください。

部位の表示順と画像矩形は `runtime/model/model.json` の `bodyLayers` に保存しています。`role` ごとに独立した頂点配列を持ち、画像の透明度を腕の変形ウェイトに流用しません。顔用の処理は `runtime/web/expressions.js` と保存済みの表情 PNG をそのまま使用します。

分割画像の境界が半透明に抜けないよう、部位を高解像度の共通描画先へ独立して描いた後、合成済みの画像を一度だけ縮小します。これは描画時のサンプリング修正で、脚や顔の画素を塗り足す処理ではありません。
