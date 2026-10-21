# v20 implementation QA

- Baseline: accepted v19 commit 83fb688e78b7f478cc8bed134e3f4f641ebf99b2.
- Official VOICEVOX 0.25.2 Linux CPU engine was installed from the pinned official release and verified by SHA256. Engine binaries and local install environment are not committed or bundled.
- Actual text -> runtime HTTP -> VOICEVOX -> fresh PCM -> WebSocket controller ownership -> playback state and cancellation passed twice. The immutable sample and second proof are retained here.
- New input is never replaced silently with an old WAV. Included WAV is explicitly a saved verification sample.
- Stop cancels the runtime provider task, retires the request ID and rejects late results. Native engine computation may continue briefly after a disconnected HTTP request; immediate engine CPU cancellation is not asserted.
- Cancellation-before-arrival, supersession, delayed broadcasts, controller disconnect, malformed WAV, missing speaker, unreachable engine, seek/rate/pause/stop and autoplay/decode error distinctions are covered.
- Browser access was not performed: no permitted GUI route was available. Node DOM/media mocks and real local HTTP/WebSocket are not browser E2E or proof of physical speaker output.
- Preview uses the new actual runtime waveform and unchanged v19 motion/renderer with explicit offline labels. No camera, microphone, external LLM service or credentials used.
- Model/art and PSD unchanged. No additional PSD is required; retain accepted v19 PSD.
- Runtime ZIP is divided losslessly into core/model. Engine setup is opt-in, not included. Each native attachment stays below 19.5 MB.
