# v50 音声付き確認動画（実合成 + 実リップシンク）

v50の無音確認動画 `assets/parts/v50/review/v50-emotions-full-cfr.mp4` には音声がない。ここではv12/v20と同じ方式（VOICEVOXで新規合成 → Web Audioの実音量解析 → その値だけで口を動かす → 録画）を、v50の `runtime` 一式にそのまま当てて、音声入りの確認動画を1本作る。

絵・PSD・既存の動き計算は変更していない。追加したのは収録用 `scripts/capture_voice_lipsync_v50.mjs` と検証用 `scripts/verify_voice_lipsync_v50.mjs` の2本だけ。

## 成果物

- `assets/parts/v50/voice-review/koma-v50-voice-lipsync.mp4` — 音声入り本編（16.23秒・487フレーム・30fps CFR / 640x1040 / H.264 + AAC）
- `assets/parts/v50/voice-review/koma-v50-voice-timeline.wav` — 動画に入っている音声そのもの（今回新規合成）
- `assets/parts/v50/voice-review/clips/line-*.wav` — 1行ずつの合成結果
- `assets/parts/v50/voice-review/capture-report.json` — 解析値と全フレームのパラメータ
- `assets/parts/v50/voice-review/verification.json` — 検証結果
- `assets/parts/v50/voice-review/lipsync-contact.png` — 抜粋8フレームの一覧

## セリフ

将棋VTuber『羽月こま』の短い一言を、v50の発話感情ごとに1行ずつ。文面はサンプルであり台本確定ではない。

1. 喜ぶ（happy / soft_smile）「よし、いい手が見えました。ここは嬉しい一手ですね。」
2. 考える（thoughtful / thinking）「うーん、この局面はもう少し考えさせてください。」
3. 驚く（surprised / surprised）「えっ、そこに打つんですか。おどろきました。」

声は **VOICEVOX:雨晴はう / ノーマル**（公式Linux CPUエンジン 0.25.2）。配信・公開時もこのクレジットを掲載する。仮の声であり、こまの最終的な声の決定ではない。

## 口の動かし方

口の開き `ParamMouthOpenY` は、台本やキーフレームを一切持たない。値の出どころは次の一本道だけ。

1. `runtime/server.py` の `/api/speech` が実際にVOICEVOXへ合成を依頼し、WAVを返す。保存済み音声への差し替えはしない。エンジンが無ければ収録は失敗で止まる。
2. 3本のWAVを1本のタイムラインへ並べ、`koma-v50-voice-timeline.wav` として書き出す。発話区間以外は完全な無音。
3. Chromiumの中で、そのWAVを `decodeAudioData` で復号し、`AnalyserNode`（`fftSize` 1024）へ通す。`OfflineAudioContext.suspend()` で60Hzの制御刻みごとに描画を止め、本番の `app.js` と同じ `getFloatTimeDomainData` → `rmsMouth()` を呼ぶ。
4. その値を `target.ParamMouthOpenY` に入れ、以降は `PerformanceMotion.frame` → `ActingController.frame` → `smoothParameters` → `AvatarRenderer.render` という `app.js` のtickと同じ順序で進める。

実時間再生ではなくオフライン解析にしたのは、headless Chromiumの音声出力先が無く `AudioContext.currentTime` が実時間で進まないため（0.5秒の実時間で0.012秒しか進まないことを確認済み）。`OfflineAudioContext.suspend()` は同じ `AnalyserNode` の同じ時間領域窓を、取りこぼしなく読む。読み取り予定と実際の読み取り回数が一致しない場合は収録が失敗する。

## 動きと表情

発話中は本番と同じく `actingBlocked()` 相当の状態になり、v50の演技オーバーレイ（`ActingController`）は重み0のまま待機する。身体の感情表現は `PerformanceMotion` が担当し、サーバーの `/api/playback` が発話中に設定するのと同じ `performance` 状態（`emotion` と `started_at` / `until`）を時刻どおりに与える。表情は `/api/speech` が返した `expression` を発話中だけ `owner='speech'` 相当で適用する。

つまりこの動画は「口＝音声の実音量」「体・顔＝発話感情のモーション」という本番の役割分担をそのまま写したもので、演技オーバーレイと音声が同時に動く新しい経路を作ってはいない。演技オーバーレイ単体の確認は従来どおり無音の `review/v50-emotions-*-cfr.mp4` が担当する。

画面下には、合成音声の実波形と、解析から出た口の開きを上下に並べ、再生位置の縦線を重ねている。目視でも波形と口が同じ位置で立ち上がることを確認できる。

## 再実行

```sh
python -m pip install -r requirements.txt
python -m pip install py7zr && python scripts/setup_voicevox.py   # Linux x64 CPUエンジンを導入する場合のみ
runtime/vendor/voicevox/linux-cpu-x64/run --host 127.0.0.1 --port 50021 &

PYTHON=python PLAYWRIGHT_MODULE=/path/to/playwright CHROME_PATH=/path/to/chrome \
  node scripts/capture_voice_lipsync_v50.mjs
node scripts/verify_voice_lipsync_v50.mjs
```

`scripts/setup_voicevox.py` は `hashlib.file_digest` を使うためPython 3.11以降が必要。3.10で導入する場合は、同じURLとSHA-256（`bab016a966131b89bad398e7b898f8c742617dc80a7da49bf494cd07133dbc7a`）を手元で照合してから `py7zr` で展開する。WindowsとmacOSは公式VOICEVOXアプリを起動する。

## 検証

`scripts/verify_voice_lipsync_v50.mjs` は、収録側の数値をそのまま信用せず、Nodeで同じWAVから参照包絡を計算し直し、MP4からは画素を読み戻して判定する。11項目すべて合格。

| 検査 | 結果 |
| --- | --- |
| タイムラインが今回の合成クリップそのもの（バイト一致）、発話区間外は完全無音 | 一致・無音 |
| ブラウザのAnalyserNodeの値 vs Nodeで再計算した同じ窓長のRMS | r = 0.9995（974制御点） |
| 描画された口パラメータ vs 音声包絡（フレーム単位） | r = 0.9628、遅れ 0フレーム |
| 無音102フレームの口の開き | 最大 0.000 |
| 各行の口の開き | 最大 0.915 / 0.875 / 0.839 |
| 発話中の演技オーバーレイの重み | 常に 0 |
| 発話感情の身体モーション | 喜ぶ: 弾み最大 0.91 / 考える: 頬添え 1.00 |
| 動画が厳密な30fps CFR | 487フレーム・30/1・640x1040 |
| 音声トラック | AAC 24kHz・16.227秒 |
| MP4内の音声 vs 解析したタイムライン | r = 1.00000 |
| 口周りの画素変化 vs 口パラメータ | 開/閉の変化画素比 9.5 / 2.0 / 2.1 倍、相関 0.59 / 0.82 / 0.82 |

画素の検査だけは精度に限界がある。全身が16秒の間に数十px移動し、揺れる髪が口の帯へ入り込むため、比較のたびに±24pxの整数ずらしで位置を合わせ直し、同じ区間の「口を閉じたフレーム同士」を対照群として比を見ている。絶対的な画素相関ではなく、対照群との比で判定している。

数値は `assets/parts/v50/voice-review/verification.json`、抜粋フレームは `lipsync-contact.png` を参照。

## 限界

スピーカーからの音響測定、実UI操作の実時間録画、OBS等での配信確認はしていない。動画はv50の既存素材・既存モーションのオフライン再描画であり、操作画面のスクリーン録画ではない。髪・太ももの境界など従来からの既知の課題は修正していない。音素別の口形（あいうえお）はまだ無く、v12からの音量ベースのままである。
