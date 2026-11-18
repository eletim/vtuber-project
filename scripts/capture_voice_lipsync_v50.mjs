// Record one audible v50 review video: real VOICEVOX synthesis, real Web Audio
// analysis of that waveform, and the production mouth/motion code.
//
// The mouth parameter is never scripted. Every value comes from the runtime
// AnalyserNode (fftSize 1024) reading the decoded synthesized timeline inside
// Chromium, passed through the production rmsMouth() helper. No stored
// historical utterance is reused and no art, PSD or motion logic is edited.
import {createRequire} from 'node:module';
import {spawn, execFile} from 'node:child_process';
import {mkdir, writeFile} from 'node:fs/promises';
import {promisify} from 'node:util';
import {muxCfr} from './cfr_mp4.mjs';
import {samples} from './mp4_samples.mjs';

const run = promisify(execFile);
const require = createRequire(import.meta.url);
const {chromium} = require(process.env.PLAYWRIGHT_MODULE);
const PYTHON = process.env.PYTHON || 'python3';
const PORT = Number(process.env.KOMA_PORT || 18812);
const BASE = `http://127.0.0.1:${PORT}`;
const OUT = 'assets/parts/v50/voice-review';
const FPS = 30, SUB = 2, W = 640, H = 1040, STAGE = 0.5;
const SMOKE = process.env.KOMA_SMOKE === '1';
const LEAD_IN = SMOKE ? 0.3 : 0.8, GAP = SMOKE ? 0.3 : 0.9, TAIL = SMOKE ? 0.5 : 2.0;

// A short shogi-VTuber script: one line per v50 speech emotion.
const LINES = SMOKE ? [{emotion: 'happy', text: 'こんにちは。'}] : [
  {emotion: 'happy',     text: 'よし、いい手が見えました。ここは嬉しい一手ですね。'},
  {emotion: 'thoughtful', text: 'うーん、この局面はもう少し考えさせてください。'},
  {emotion: 'surprised', text: 'えっ、そこに打つんですか。おどろきました。'}
];

const report = {errors: [], generatedAt: new Date().toISOString(), lines: [], timeline: {}, analysis: {}, frames: []};
const sleep = ms => new Promise(r => setTimeout(r, ms));

function wavBytes(pcm, rate) {
  const header = Buffer.alloc(44);
  header.write('RIFF', 0); header.writeUInt32LE(36 + pcm.length, 4); header.write('WAVE', 8);
  header.write('fmt ', 12); header.writeUInt32LE(16, 16); header.writeUInt16LE(1, 20);
  header.writeUInt16LE(1, 22); header.writeUInt32LE(rate, 24); header.writeUInt32LE(rate * 2, 28);
  header.writeUInt16LE(2, 32); header.writeUInt16LE(16, 34);
  header.write('data', 36); header.writeUInt32LE(pcm.length, 40);
  return Buffer.concat([header, pcm]);
}

function readWav(buffer) {
  if (buffer.toString('ascii', 0, 4) !== 'RIFF' || buffer.toString('ascii', 8, 12) !== 'WAVE') throw Error('not a RIFF/WAVE clip');
  let rate = 0, channels = 0, bits = 0, data = null;
  for (let p = 12; p + 8 <= buffer.length;) {
    const id = buffer.toString('ascii', p, p + 4), size = buffer.readUInt32LE(p + 4);
    if (id === 'fmt ') {channels = buffer.readUInt16LE(p + 10); rate = buffer.readUInt32LE(p + 12); bits = buffer.readUInt16LE(p + 22);}
    if (id === 'data') data = buffer.subarray(p + 8, p + 8 + size);
    p += 8 + size + (size % 2);
  }
  if (!data || bits !== 16 || channels !== 1) throw Error(`expected mono 16-bit PCM, got ${channels}ch/${bits}bit`);
  return {rate, data};
}

async function json(path, body) {
  const response = await fetch(BASE + path, body === undefined ? {} : {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
  });
  if (!response.ok) throw Error(`${path} ${response.status}: ${(await response.text()).slice(0, 200)}`);
  return response.json();
}

const server = spawn(PYTHON, ['runtime/server.py', '--port', String(PORT)], {windowsHide: true, stdio: 'inherit'});
let browser;
try {
  await mkdir(OUT + '/frames', {recursive: true});
  await mkdir(OUT + '/clips', {recursive: true});
  for (let n = 0; n < 200; n++) {
    try {if ((await fetch(BASE + '/api/state')).ok) break;} catch {}
    await sleep(100);
  }

  // 1. Require a live engine. A stored WAV is never an acceptable substitute.
  const voice = await json('/api/voice');
  report.voice = voice;
  if (!voice.available) throw Error(`VOICEVOX unavailable (${voice.error}): ${voice.message}`);
  await json('/api/mode', {mode: 'ai'});

  // 2. Synthesize every line for real, through the production speech API.
  const stamp = Date.now().toString(36);
  for (const [index, line] of LINES.entries()) {
    const event = await json('/api/speech', {text: line.text, emotion: line.emotion, request_id: `voice-lipsync-${stamp}-${index}`});
    const wav = Buffer.from(await (await fetch(BASE + event.url)).arrayBuffer());
    const clip = readWav(wav);
    await writeFile(`${OUT}/clips/line-${index + 1}.wav`, wav);
    report.lines.push({...line, clip_id: event.clip_id, expression: event.expression, credit: event.credit,
                       duration: event.duration, bytes: wav.length, rate: clip.rate});
    LINES[index] = {...line, expression: event.expression, duration: event.duration, pcm: clip.data, rate: clip.rate};
  }

  // 3. Lay the fresh clips onto one timeline; this exact PCM is analysed and encoded.
  const rate = LINES[0].rate;
  if (LINES.some(l => l.rate !== rate)) throw Error('engine returned mixed sample rates');
  let cursor = LEAD_IN;
  for (const line of LINES) {line.start = cursor; cursor += line.duration + GAP;}
  const total = cursor - GAP + TAIL;
  const pcm = Buffer.alloc(Math.ceil(total * rate) * 2);
  for (const line of LINES) {
    const offset = Math.round(line.start * rate) * 2;
    line.pcm.copy(pcm, offset);
    line.samples = line.pcm.length / 2;
  }
  const timelineWav = wavBytes(pcm, rate);
  await writeFile(`${OUT}/koma-v50-voice-timeline.wav`, timelineWav);
  const totalFrames = Math.round(total * FPS);
  report.timeline = {rate, duration: total, frames: totalFrames, fps: FPS, leadIn: LEAD_IN, gap: GAP, tail: TAIL,
                     segments: LINES.map(l => ({emotion: l.emotion, expression: l.expression, text: l.text, start: l.start, duration: l.duration}))};

  // 4. Browser: production renderer + production analyser.
  browser = await chromium.launch({headless: true, executablePath: process.env.CHROME_PATH});
  const page = await browser.newPage();
  page.on('pageerror', e => report.errors.push(String(e.message)));
  page.on('console', m => {if (m.type() === 'error') report.errors.push('console: ' + m.text());});
  await page.route('**/capture', r => r.fulfill({contentType: 'text/html', body: '<!doctype html><meta charset="utf-8"><canvas/>'}));
  await page.route('**/timeline-audio.wav', r => r.fulfill({contentType: 'audio/wav', body: timelineWav}));
  await page.goto(`${BASE}/capture`);

  const plan = {segments: report.timeline.segments, total, totalFrames, fps: FPS, sub: SUB, width: W, height: H, stage: STAGE, credit: report.lines[0].credit};
  report.analysis = await page.evaluate(async plan => {
    const {AvatarRenderer} = await import('/web/renderer.js');
    const {ActingController} = await import('/web/acting-controller.js');
    const {PerformanceMotion} = await import('/web/performance.js');
    const {neutral, rmsMouth, smoothParameters} = await import('/web/controls.js');
    window.koma = {neutral, rmsMouth, smoothParameters, plan};

    const avatar = document.createElement('canvas');
    avatar.width = 1086; avatar.height = 1448;
    const renderer = new AvatarRenderer();
    await renderer.load(avatar);
    koma.renderer = renderer;
    koma.naturalMotion = new PerformanceMotion();
    koma.acting = new ActingController();

    // Real Web Audio: decode the freshly synthesized timeline, then read the
    // production AnalyserNode at every 60 Hz control step while the graph
    // renders. OfflineAudioContext.suspend() exposes the same time-domain
    // window that app.js polls with getFloatTimeDomainData during playback.
    const probe = new AudioContext();
    const sampleRate = probe.sampleRate;
    await probe.close();
    const encoded = await (await fetch('/timeline-audio.wav')).arrayBuffer();
    const length = Math.ceil(plan.total * sampleRate);
    const context = new OfflineAudioContext(1, length, sampleRate);
    const buffer = await context.decodeAudioData(encoded);
    const source = context.createBufferSource();
    source.buffer = buffer;
    const analyser = context.createAnalyser();
    analyser.fftSize = 1024;
    source.connect(analyser); analyser.connect(context.destination); source.start(0);

    const steps = Math.round(plan.total * plan.fps * plan.sub);
    const window1024 = new Float32Array(1024);
    const mouth = new Array(steps).fill(0);
    const rms = new Array(steps).fill(0);
    const quantum = 128 / sampleRate;
    let scheduled = 0, fired = 0;
    for (let j = 1; j < steps; j++) {
      const at = Math.round(j / (plan.fps * plan.sub) / quantum) * quantum;
      if (at <= 0 || at >= plan.total) continue;
      scheduled++;
      context.suspend(at).then(() => {
        fired++;
        analyser.getFloatTimeDomainData(window1024);
        let energy = 0;
        for (const value of window1024) energy += value * value;
        rms[j] = Math.sqrt(energy / window1024.length);
        mouth[j] = rmsMouth(window1024);
        context.resume();
      });
    }
    await context.startRendering();
    koma.mouth = mouth;

    // Peak envelope of the same decoded waveform, only for the on-screen strip.
    const channel = buffer.getChannelData(0), bins = 560, envelope = new Array(bins).fill(0);
    for (let b = 0; b < bins; b++) {
      const from = Math.floor(b * channel.length / bins), to = Math.floor((b + 1) * channel.length / bins);
      let peak = 0;
      for (let i = from; i < to; i++) peak = Math.max(peak, Math.abs(channel[i]));
      envelope[b] = peak;
    }
    koma.envelope = envelope;

    return {sampleRate, decodedSamples: channel.length, decodedDuration: channel.length / sampleRate,
            fftSize: analyser.fftSize, steps, scheduledSuspends: scheduled, firedSuspends: fired,
            analysedSteps: mouth.filter(v => v > 0).length, peakMouth: Math.max(...mouth),
            peakRms: Math.max(...rms), mouth, rms};
  }, plan);
  if (report.analysis.firedSuspends !== report.analysis.scheduledSuspends) throw Error(`analyser read ${report.analysis.firedSuspends}/${report.analysis.scheduledSuspends} scheduled control steps`);
  if (!(report.analysis.peakMouth > 0.3)) throw Error('analysed mouth amplitude never opened; check the engine output');

  // 5. Encode. One deterministic 30 fps pass over the analysed mouth timeline.
  await page.evaluate(plan => {
    const canvas = document.createElement('canvas');
    canvas.width = plan.width; canvas.height = plan.height;
    koma.stage = canvas;
    koma.ctx = canvas.getContext('2d');
    koma.chunks = []; koma.description = null;
    koma.current = koma.neutral();
    koma.encoder = new VideoEncoder({
      error: e => {throw e;},
      output: (chunk, meta) => {
        const bytes = new Uint8Array(chunk.byteLength);
        chunk.copyTo(bytes);
        koma.chunks.push({timestamp: chunk.timestamp, type: chunk.type, data: Array.from(bytes)});
        if (meta.decoderConfig?.description) koma.description = Array.from(new Uint8Array(meta.decoderConfig.description));
      }
    });
    koma.encoder.configure({codec: 'avc1.420028', width: plan.width, height: plan.height, framerate: plan.fps,
                            bitrate: 2400000, avc: {format: 'avc'}, latencyMode: 'realtime'});
  }, plan);

  const picks = new Set([0, ...LINES.map(l => Math.round((l.start + l.duration / 2) * FPS)),
                         ...LINES.map(l => Math.round((l.start + 0.45) * FPS)), totalFrames - 1]);
  for (let i = 0; i < totalFrames; i++) {
    const frame = await page.evaluate(async ([i, wantPng]) => {
      const {plan, neutral, rmsMouth, smoothParameters, renderer, naturalMotion, acting} = koma;
      let pose, expressionId, segment = null, mouthTarget = 0;
      for (let step = 0; step < plan.sub; step++) {
        const index = i * plan.sub + step, t = index / (plan.fps * plan.sub), dt = index === 0 ? 1 / 60 : 1 / (plan.fps * plan.sub);
        segment = plan.segments.find(s => t >= s.start && t < s.start + s.duration) || null;
        mouthTarget = koma.mouth[index] || 0;
        // Exactly the app.js tick order: audio RMS mouth, then speech
        // performance motion, then the (speech-blocked) acting overlay.
        const target = neutral();
        target.ParamMouthOpenY = mouthTarget;
        const performance = segment
          ? {enabled: true, emotion: segment.emotion, started_at: segment.start, until: segment.start + segment.duration}
          : {enabled: true, emotion: 'neutral', started_at: 0, until: 0};
        let next = naturalMotion.frame(target, t, performance, target.ParamMouthOpenY);
        expressionId = segment ? segment.expression : 'neutral';
        const result = acting.frame(next, t, {blocked: true, expression: expressionId, expressionOwned: true});
        next = result.pose;
        if (t % 4.7 > 4.48) next.ParamEyeLOpen = next.ParamEyeROpen = 0;
        next.ParamBreath = 0.5 + 0.5 * Math.sin(t * 1000 / 1700);
        koma.current = smoothParameters(koma.current, next, dt);
        renderer.render(koma.current, t, result.expression);
        pose = koma.current;
      }

      const t = i / plan.fps, ctx = koma.ctx, tint = {happy: '#2f6b4f', thoughtful: '#355b7a', surprised: '#8a4a2f'}[segment?.emotion] || '#5c5048';
      const jp = (size, bold) => `${bold ? 'bold ' : ''}${size}px "Noto Sans CJK JP", sans-serif`;
      ctx.fillStyle = '#f8f4ee'; ctx.fillRect(0, 0, plan.width, plan.height);
      ctx.fillStyle = tint; ctx.fillRect(0, 0, plan.width, 96);
      ctx.fillStyle = 'white';
      ctx.font = jp(30, true); ctx.fillText('羽月こま v50', 24, 44);
      ctx.font = jp(14); ctx.fillText('実合成音声 × 実波形リップシンク', 24, 74);
      ctx.textAlign = 'right';
      ctx.font = jp(20, true);
      ctx.fillText({happy: 'よろこぶ', thoughtful: 'かんがえる', surprised: 'おどろく'}[segment?.emotion] || '停止', plan.width - 24, 44);
      ctx.font = jp(14); ctx.fillText(`${t.toFixed(2)} / ${plan.total.toFixed(2)}秒`, plan.width - 24, 74);
      ctx.textAlign = 'left';
      ctx.drawImage(renderer.canvas, 0, 0, 1086, 1448, 48, 100, 1086 * plan.stage, 1448 * plan.stage);

      ctx.fillStyle = '#3a2f26'; ctx.font = jp(19);
      const line = segment ? '「' + segment.text + '」' : '発話していません（口は閉じたまま）';
      let row = line;
      while (ctx.measureText(row).width > plan.width - 48 && row.length > 1) row = row.slice(0, -1);
      ctx.fillText(row, 24, 856);
      if (row.length < line.length) ctx.fillText(line.slice(row.length), 24, 882);

      // Two stacked plots: the decoded waveform, and the mouth value the
      // AnalyserNode produced for it. The playhead crosses both together.
      const X0 = 40, PW = koma.envelope.length;
      ctx.fillStyle = '#857361'; ctx.font = jp(13);
      ctx.fillText('合成音声の実波形', X0, 916);
      ctx.fillText('口の開き ParamMouthOpenY（AnalyserNode + rmsMouth）', X0, 982);
      ctx.strokeStyle = '#ded1be'; ctx.beginPath();
      ctx.moveTo(X0, 944); ctx.lineTo(X0 + PW, 944); ctx.moveTo(X0, 1018); ctx.lineTo(X0 + PW, 1018); ctx.stroke();
      ctx.fillStyle = '#a8977f';
      for (let b = 0; b < PW; b++) {
        const h = Math.max(0.6, koma.envelope[b] * 22);
        ctx.fillRect(X0 + b, 944 - h, 1, h * 2);
      }
      ctx.strokeStyle = tint; ctx.lineWidth = 2; ctx.beginPath();
      for (let b = 0; b < PW; b++) {
        const index = Math.min(koma.mouth.length - 1, Math.round(b / PW * koma.mouth.length));
        const v = 1018 - (koma.mouth[index] || 0) * 36;
        b ? ctx.lineTo(X0 + b, v) : ctx.moveTo(X0 + b, v);
      }
      ctx.stroke(); ctx.lineWidth = 1;
      const playhead = X0 + PW * Math.min(1, t / plan.total);
      ctx.strokeStyle = '#c2453a'; ctx.beginPath();
      ctx.moveTo(playhead, 922); ctx.lineTo(playhead, 966); ctx.moveTo(playhead, 988); ctx.lineTo(playhead, 1022); ctx.stroke();
      ctx.fillStyle = '#6b5a48'; ctx.font = jp(13);
      ctx.fillText(`口 ${pose.ParamMouthOpenY.toFixed(3)} / 解析値 ${mouthTarget.toFixed(3)} · ${plan.credit}`, X0, 1034);

      const videoFrame = new VideoFrame(koma.stage, {timestamp: Math.round(i * 1e6 / plan.fps), duration: Math.round(1e6 / plan.fps)});
      koma.encoder.encode(videoFrame, {keyFrame: i % 30 === 0});
      videoFrame.close();
      while (koma.encoder.encodeQueueSize > 3) await new Promise(r => setTimeout(r, 2));
      return {frame: i, t, emotion: segment?.emotion || null, expression: renderer.expressionFrame.id,
              mouthTarget, mouth: pose.ParamMouthOpenY, armL: pose.ParamArmLOpen, armR: pose.ParamArmROpen,
              handToCheek: pose.ParamHandToCheek, bodyBounce: pose.ParamBodyBounce, angleY: pose.ParamAngleY,
              actingWeight: acting.weight,
              png: wantPng ? koma.stage.toDataURL().split(',')[1] : null};
    }, [i, picks.has(i)]);
    if (frame.png) await writeFile(`${OUT}/frames/frame-${String(i).padStart(4, '0')}.png`, Buffer.from(frame.png, 'base64'));
    delete frame.png;
    report.frames.push(frame);
    if (i % 60 === 0) console.log(`frame ${i}/${totalFrames}`);
  }

  const encoded = await page.evaluate(async () => {
    await koma.encoder.flush(); koma.encoder.close();
    return {width: koma.stage.width, height: koma.stage.height, chunks: koma.chunks, description: koma.description};
  });
  const silent = muxCfr({width: encoded.width, height: encoded.height, description: Buffer.from(encoded.description),
                         chunks: encoded.chunks.map(c => ({...c, data: Buffer.from(c.data)}))});
  const table = samples(silent);
  if (table.samples.length !== totalFrames || table.samples.some((s, i) => s.timestamp !== Math.round(i * 1e6 / FPS)))
    throw Error('encoded video is not exact 30 fps CFR');
  await writeFile(`${OUT}/koma-v50-voice-video-only.mp4`, silent);

  // 6. Attach the same analysed PCM as the audio track.
  await run('ffmpeg', ['-v', 'error', '-y', '-i', `${OUT}/koma-v50-voice-video-only.mp4`, '-i', `${OUT}/koma-v50-voice-timeline.wav`,
                       '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
                       '-movflags', '+faststart', `${OUT}/koma-v50-voice-lipsync.mp4`]);
  report.video = {name: 'koma-v50-voice-lipsync.mp4', frames: totalFrames, fps: FPS, width: W, height: H,
                  videoOnlyBytes: silent.length, codec: table.codec};
  console.log('CAPTURE COMPLETE');
} catch (error) {
  report.errors.push(error.stack || String(error));
  process.exitCode = 1;
} finally {
  await browser?.close();
  server.kill();
  await mkdir(OUT, {recursive: true});
  await writeFile(`${OUT}/capture-report.json`, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({errors: report.errors.slice(0, 3), video: report.video,
                              analysis: report.analysis && {sampleRate: report.analysis.sampleRate, steps: report.analysis.steps,
                              analysedSteps: report.analysis.analysedSteps, peakMouth: report.analysis.peakMouth}}, null, 2));
}
