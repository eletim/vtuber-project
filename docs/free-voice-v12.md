# 無料音声で動く羽月こま（v12）

仮の声は **VOICEVOX:雨晴はう / ノーマル**。既存モデルのデザイン・PSDを変えず、文章 → 日本語WAV生成 → ブラウザ再生 → 実音量による口パクを接続した。音声API料金は不要。後から別の声・合成サービスに交換できる。

## 起動

### Windows / macOS / VOICEVOX導入済みLinux

1. [公式VOICEVOX](https://voicevox.hiroshiba.jp/)をインストールして起動する（通常 `127.0.0.1:50021`）。
2. このリポジトリの依存を `python -m pip install -r requirements.txt` で導入。
3. `python scripts/run_runtime.py` を起動し、`http://127.0.0.1:8766` を開く。
4. 「読み上げ」を押す。初回の合成にはモデルの読み込み時間がかかる。音声が自動再生できない環境では音声プレーヤーの再生を押す。

### Linux x64 CPU：専用エンジンを導入

```bash
python -m pip install -r requirements.txt py7zr
python scripts/setup_voicevox.py
python scripts/run_runtime.py --voicevox
```

公式engine 0.25.2を約1.8GBダウンロードしてSHA-256を照合。展開先はgit管理外の `runtime/vendor/voicevox`。専用エンジンはランナー終了時に停止する。デスクトップ版を既に起動している場合は `--voicevox` を付けない。既存実行ファイルは `--voicevox-engine /path/to/run` でも指定可能。

## AIから発話

操作画面を一つ開いておく。既存クライアントから実際の音声合成を呼べる。

```bash
python runtime/ai_client.py --say 'こんにちは、羽月こまです。今日は何をして遊びましょう？'
```

`POST /api/mode {"mode":"ai"}` 後に `POST /api/speech {"text":"..."}`。返却される `url` は生成済みWAV、`credit` は音声クレジット。WebSocketで最新の操作画面一つへ再生を依頼し、配信用画面は字幕と口の状態を受け取る。複数画面で声を重ねない。画面未接続なら `playback_clients:0` となり、WAV自体は返る。

会話文を考えるLLMそのものはこの変更には含まない。外部AIが決めた文章を既存APIに渡すと発話する。

## 設定・挙動

- `VOICEVOX_URL`：エンジンURL（既定 `http://127.0.0.1:50021`）。
- `VOICEVOX_SPEAKER` / `VOICEVOX_STYLE`：話者名・スタイル名。既定 `雨晴はう` / `ノーマル`。変更先の利用条件はその話者の公式条件を確認。
- `runtime/voice.py` が音声生成の交換箇所。ブラウザ標準音声への暗黙の代替は行わず、未起動時は503と起動案内を返す。
- 人間操作への切替と次の発話は再生を停止。合成中の古い発話も世代番号で無効化し、後から再生されない。
- WAVはメモリに最新8件を保持。再起動またはキャッシュ追い出し後のURLは無効。
- 口パクはWeb AudioのRMS。音素別の「あいうえお」形状は次の段階。

## 検証とサンプル

`assets/parts/v12/koma-free-voice.wav` は公式CPUエンジンによる実音声（8.17秒）。`free-voice-control.png` は実再生中の操作画面。`voice-verification.json` はブラウザでの再生・RMS・配信画面反映・停止の検証結果。

`koma-free-voice.mp4` は同じ音声の音量から15fpsで実WebGLモデルを描画して音声を合成した確認用動画。ブラウザの実時間再生テストとは別に、再現可能な確認用として生成している。

```bash
python tests/test_voice_runtime.py
python tests/test_runtime_server.py
node --test runtime/tests/*.test.js
VOICEVOX_ENGINE=/path/to/run node runtime/tests/voice.e2e.mjs
```

ブラウザ検証はPlaywrightとChromeが必要。`PLAYWRIGHT_MODULE` と `CHROME_PATH` で既存環境を指定可。実エンジンテストはモック音声を使用していない。物理スピーカーからの音響測定はしていない。

## クレジット

**VOICEVOX:雨晴はう**

- [VOICEVOX](https://voicevox.hiroshiba.jp/)
- [雨晴はうの公式音声利用規約](https://amehau.com/rules/amehare-hau-rule)
- [公式エンジンAPI](https://github.com/VOICEVOX/voicevox_engine/blob/master/README.md)

雨晴はう音声を別のオリジナルキャラクターへ利用することは公式規約で許可されている。配信・動画公開時にも上記クレジットを掲載する。これは仮の音声であり、こまの最終的な声の採用決定ではない。
