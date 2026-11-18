# Portable v50 development snapshot

This branch contains the v50 runtime and development sources, based on main with a small snapshot-only commit series. It does not merge or update main. The original Dell v50 checkout remains untouched.

## What is preserved

- The entire runtime directory is byte-identical to v50 commit e34f3233fca7a6916a478caab255485057be87de.
- All source code, scripts, tests, config, original artwork, imported/reference artwork, and all 27 tracked PSD files are retained.
- The v48, v49 and v50 delivered/review MP4 pairs are retained for comparison.
- Historical reports and written diagnoses remain.
- Generated previews and mask/material/reference inputs consumed by older builders/exporters are retained; the manifest lists them explicitly.

## What is omitted

Only generated image/video files in identified review directories are omitted. No PSD or runtime file is omitted. The exact 6,580 paths, object hashes and sizes are listed in snapshot-v50-manifest.json. Some old review scripts or documentation links need those generated outputs to be regenerated. This is a filtered development snapshot, not a byte-identical copy of the full 4.48 GB v50 tree.

## Start without Dell

Use Python 3.10+ with aiohttp installed, then run from the repository root:

    python runtime/server.py --port 8766

Open http://127.0.0.1:8766/ in a WebGL-capable browser. This direct server command does not download optional models. Manual controls and the coordinated gestures do not require Dell, a camera, or an LLM.

Camera tracking requires the vendor files specified in runtime/vendor-manifest.json. VOICEVOX and a local conversation model are optional separate dependencies; they are not bundled or newly validated by this snapshot. Read scripts/run_runtime.py and the existing voice/conversation docs before setting those up.

## Audible lip-sync review

`assets/parts/v50/voice-review/koma-v50-voice-lipsync.mp4` adds the one thing the silent v50 review pair does not have: real VOICEVOX speech with the mouth driven only by the measured volume of that speech. Read [docs/v50-voice-lipsync.md](docs/v50-voice-lipsync.md) for the method, the sample lines and the verification numbers. It is regenerated with `scripts/capture_voice_lipsync_v50.mjs` and checked with `scripts/verify_voice_lipsync_v50.mjs`; VOICEVOX remains an optional separate dependency.

## Tests and comparison

    node --test runtime/tests/*.test.js
    python tests/test_runtime_server.py

The source runtime is v50, two commits after the previously viewed v48 video: v49 fixes the bright lower iris rim; v50 coordinates joy, thinking and surprise with interruption/stop handling. The original v48 video and the v50 previews remain distinct. See docs/v49-eye-edge-diagnosis.md and docs/v50-emotional-actions.md.

Independent cloud validation results are reported separately. Historical test reports do not claim a fresh test pass.
