# Fresh-speech offline preview

This preview uses a complete, newly synthesized utterance produced by the runtime text-speech integration. It is not a screen recording or browser end-to-end test.

Requirements: the already available Python NumPy/Pillow, Node, ffmpeg/ffprobe, Mesa EGL/OpenGL, and Noto CJK fonts. No model/art editing or further voice generation occurs during video rendering.

Copy these files to a new writable output directory:
- prepare_source.py
- generate_fresh_speech_frames.mjs
- layered_egl.py
- test_egl.py
- test_layer_alpha.py
- render_fresh_speech.py
- verify_fresh_preview.py

Run only after the model/motion source and runtime-generated WAV/provenance are frozen:

```sh
python prepare_source.py --source /path/to/vtuber-project --voice-evidence /path/to/vtuber-v20-evidence
node generate_fresh_speech_frames.mjs
LP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 python test_layer_alpha.py
LP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 python render_fresh_speech.py --frames-only
# Inspect the lossless preview frames before encoding.
LP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 python render_fresh_speech.py
OPENBLAS_NUM_THREADS=1 python verify_fresh_preview.py
```

The immutable source snapshot contains only the model/art and frozen motion/render modules, not the changing API/UI. Runtime integration evidence is preserved separately. The exact accepted v19 layered EGL helper is reused unchanged, including independent role meshes and the production 2× premultiplied coverage resolve. The actual JS PerformanceMotion, BodyRig, RMS mouth, expression transitions and mouth-pixel helper produce the frame data.

The video is 15 seconds: 1.5 seconds idle, one complete 10.4853-second freshly synthesized utterance, and a quiet return to idle. There is no reused historical audio or repeated sentence. The same RMS-derived mouth amplitude drives the speech motion. Independent arm/torso/skirt layers are retained, with the prior small skirt coverage limit and original hair/thigh boundary limitations.

Verification performs a full decode, validates 450 frames at 30 fps and 1080×1440, checks the MP4 is below 20 MB, confirms the exact complete WAV occupies the timeline once, compares decoded AAC with the PCM timeline, and extracts actual encoded body/face checks. This does not claim browser playback, speaker output, or live API/UI operation was recorded.
