// Independently check the audible v50 review video: the attached audio must be
// the freshly synthesized timeline, and the drawn mouth must follow that exact
// waveform. Nothing here reuses the browser's own numbers as evidence; the
// reference envelope is recomputed in Node and the pixels are read back out of
// the encoded MP4.
import {execFile} from 'node:child_process';
import {readFile, writeFile} from 'node:fs/promises';
import {promisify} from 'node:util';

const run = promisify(execFile);
const OUT = 'assets/parts/v50/voice-review';
const MP4 = `${OUT}/koma-v50-voice-lipsync.mp4`;
// Face band around the drawn mouth, in encoded-video pixels. The body shifts
// by tens of pixels over the clip and hair sways across the right of the band,
// so every comparison is re-aligned by an integer shift search and judged
// against a control pair taken from the same segment.
const BAND = {x: 256, y: 256, w: 128, h: 64, shift: 24, threshold: 40};
const FFT = 1024, ANALYSER_RATE = 44100;

function readWav(buffer) {
  let rate = 0, channels = 0, bits = 0, data = null;
  for (let p = 12; p + 8 <= buffer.length;) {
    const id = buffer.toString('ascii', p, p + 4), size = buffer.readUInt32LE(p + 4);
    if (id === 'fmt ') {channels = buffer.readUInt16LE(p + 10); rate = buffer.readUInt32LE(p + 12); bits = buffer.readUInt16LE(p + 22);}
    if (id === 'data') data = buffer.subarray(p + 8, p + 8 + size);
    p += 8 + size + (size % 2);
  }
  if (!data || bits !== 16 || channels !== 1) throw Error('expected mono 16-bit PCM');
  const pcm = new Float32Array(data.length / 2);
  for (let i = 0; i < pcm.length; i++) pcm[i] = data.readInt16LE(i * 2) / 32768;
  return {rate, pcm, bytes: data};
}

// Trailing-window RMS with the same window duration the runtime AnalyserNode
// reports (fftSize samples at the browser's audio rate).
function envelope(pcm, rate, times) {
  const span = Math.max(1, Math.round(FFT / ANALYSER_RATE * rate));
  return times.map(t => {
    const end = Math.min(pcm.length, Math.round(t * rate));
    let energy = 0, count = 0;
    for (let i = Math.max(0, end - span); i < end; i++) {energy += pcm[i] * pcm[i]; count++;}
    return count ? Math.sqrt(energy / span) : 0;
  });
}

function pearson(a, b) {
  const n = Math.min(a.length, b.length);
  let sa = 0, sb = 0;
  for (let i = 0; i < n; i++) {sa += a[i]; sb += b[i];}
  const ma = sa / n, mb = sb / n;
  let num = 0, da = 0, db = 0;
  for (let i = 0; i < n; i++) {const x = a[i] - ma, y = b[i] - mb; num += x * y; da += x * x; db += y * y;}
  return da && db ? num / Math.sqrt(da * db) : 0;
}

function bestLag(reference, observed, maxLag) {
  let best = {lag: 0, r: -2};
  for (let lag = 0; lag <= maxLag; lag++) {
    const r = pearson(reference.slice(0, reference.length - lag), observed.slice(lag));
    if (r > best.r) best = {lag, r};
  }
  return best;
}

const result = {checkedAt: new Date().toISOString(), checks: {}, failures: []};
const expect = (name, ok, detail) => {result.checks[name] = {ok, ...detail}; if (!ok) result.failures.push(name);};

try {
  const report = JSON.parse(await readFile(`${OUT}/capture-report.json`, 'utf8'));
  if (report.errors.length) throw Error('capture reported errors: ' + report.errors[0]);
  const timeline = readWav(await readFile(`${OUT}/koma-v50-voice-timeline.wav`));
  const {segments, duration, fps, rate} = report.timeline;
  const frames = report.frames;

  // 1. The timeline carries exactly the clips synthesized in this run, and
  //    nothing else: every sample outside a segment is digital silence.
  let placed = true, silentOutside = true;
  for (const [index, segment] of segments.entries()) {
    const clip = readWav(await readFile(`${OUT}/clips/line-${index + 1}.wav`));
    const offset = Math.round(segment.start * rate) * 2;
    if (!clip.bytes.equals(timeline.bytes.subarray(offset, offset + clip.bytes.length))) placed = false;
  }
  for (let i = 0; i < timeline.pcm.length; i++) {
    const t = i / rate;
    if (segments.some(s => t >= s.start - 1e-9 && t < s.start + s.duration)) continue;
    if (timeline.pcm[i] !== 0) {silentOutside = false; break;}
  }
  expect('timeline_is_only_fresh_clips', placed && silentOutside, {placed, silentOutside, clips: segments.length});

  // 2. The browser analyser matches an independent Node RMS of the same PCM.
  const steps = report.analysis.rms.length;
  const stepTimes = Array.from({length: steps}, (_, j) => j / (fps * 2));
  const reference = envelope(timeline.pcm, rate, stepTimes);
  const analyserR = pearson(reference.slice(1), report.analysis.rms.slice(1));
  expect('analyser_matches_source_waveform', analyserR > 0.97, {correlation: +analyserR.toFixed(4), steps});

  // 3. The rendered mouth parameter follows that waveform.
  const frameTimes = frames.map(f => f.t);
  const frameReference = envelope(timeline.pcm, rate, frameTimes);
  const rendered = frames.map(f => f.mouth);
  const lagged = bestLag(frameReference, rendered, 8);
  expect('rendered_mouth_follows_audio', lagged.r > 0.8,
         {correlation: +lagged.r.toFixed(4), lagFrames: lagged.lag, zeroLag: +pearson(frameReference, rendered).toFixed(4)});

  // 4. Mouth closed when there is no audio, open while each line plays.
  const quiet = frames.filter(f => !segments.some(s => f.t >= s.start - 0.05 && f.t <= s.start + s.duration + 0.35));
  const quietMax = Math.max(...quiet.map(f => f.mouth));
  expect('mouth_closed_in_silence', quietMax < 0.05, {quietFrames: quiet.length, maxMouth: +quietMax.toFixed(4)});
  const perLine = segments.map(s => {
    const inside = frames.filter(f => f.t >= s.start && f.t < s.start + s.duration);
    return {emotion: s.emotion, expression: s.expression, frames: inside.length,
            maxMouth: +Math.max(...inside.map(f => f.mouth)).toFixed(3),
            meanMouth: +(inside.reduce((a, f) => a + f.mouth, 0) / inside.length).toFixed(3),
            expressionsSeen: [...new Set(inside.map(f => f.expression))]};
  });
  expect('mouth_opens_while_speaking', perLine.every(l => l.maxMouth > 0.5), {perLine});

  // 5. The acting overlay yields to audio during speech, exactly as app.js does.
  expect('acting_overlay_blocked_during_speech', frames.every(f => f.actingWeight === 0),
         {maxWeight: Math.max(...frames.map(f => f.actingWeight))});

  // 5b. The speech emotions really drive the body, not just the expression.
  const motion = segments.map(segment => {
    const inside = frames.filter(f => f.t >= segment.start && f.t < segment.start + segment.duration);
    const span = key => ({min: +Math.min(...inside.map(f => f[key])).toFixed(3), max: +Math.max(...inside.map(f => f[key])).toFixed(3)});
    return {emotion: segment.emotion, bodyBounce: span('bodyBounce'), handToCheek: span('handToCheek'),
            armL: span('armL'), armR: span('armR'), angleY: span('angleY')};
  });
  const happy = motion.find(m => m.emotion === 'happy'), thoughtful = motion.find(m => m.emotion === 'thoughtful');
  expect('speech_emotion_motion_runs', happy?.bodyBounce.max > 0.3 && thoughtful?.handToCheek.max > 0.8, {perLine: motion});

  // 6. The encoded file: exact CFR video plus a real audio track.
  const probe = JSON.parse((await run('ffprobe', ['-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', MP4])).stdout);
  const video = probe.streams.find(s => s.codec_type === 'video');
  const audio = probe.streams.find(s => s.codec_type === 'audio');
  expect('encoded_video_is_cfr', video && video.r_frame_rate === `${fps}/1` && Number(video.nb_read_frames) === frames.length,
         {frames: video?.nb_read_frames, rate: video?.r_frame_rate, size: `${video?.width}x${video?.height}`});
  expect('encoded_file_has_audio', !!audio && Math.abs(Number(audio.duration) - duration) < 0.2,
         {codec: audio?.codec_name, sampleRate: audio?.sample_rate, duration: Number(audio?.duration)});
  result.playback = {durationSeconds: +Number(probe.format.duration).toFixed(3), bytes: Number(probe.format.size)};

  // 7. The audio actually inside the MP4 is the analysed timeline.
  const decoded = (await run('ffmpeg', ['-v', 'error', '-i', MP4, '-vn', '-ac', '1', '-ar', String(rate), '-f', 's16le', '-'],
                             {encoding: 'buffer', maxBuffer: 1 << 28})).stdout;
  const decodedPcm = new Float32Array(decoded.length / 2);
  for (let i = 0; i < decodedPcm.length; i++) decodedPcm[i] = decoded.readInt16LE(i * 2) / 32768;
  const decodedReference = envelope(decodedPcm, rate, frameTimes);
  const audioR = pearson(frameReference, decodedReference);
  expect('mp4_audio_is_the_analysed_timeline', audioR > 0.99, {correlation: +audioR.toFixed(5)});

  // 8. The drawn mouth moves, measured on pixels read back out of the MP4.
  const raw = (await run('ffmpeg', ['-v', 'error', '-i', MP4,
                                    '-vf', `crop=${BAND.w}:${BAND.h}:${BAND.x}:${BAND.y},format=gray`,
                                    '-f', 'rawvideo', '-'], {encoding: 'buffer', maxBuffer: 1 << 28})).stdout;
  const area = BAND.w * BAND.h, decodedFrames = Math.floor(raw.length / area);
  const S = BAND.shift, innerW = BAND.w - 2 * S, innerH = BAND.h - 2 * S;
  const changedPixels = (f, ref) => {
    let best = Infinity;
    for (let dy = -S; dy <= S; dy++) for (let dx = -S; dx <= S; dx++) {
      let count = 0;
      for (let y = 0; y < innerH; y++) {
        const a = f * area + (S + y) * BAND.w + S, b = ref * area + (S + y + dy) * BAND.w + S + dx;
        for (let x = 0; x < innerW; x++) if (Math.abs(raw[a + x] - raw[b + x]) > BAND.threshold) count++;
      }
      if (count < best) best = count;
    }
    return best;
  };
  const median = values => {const sorted = [...values].sort((x, y) => x - y); return sorted[Math.floor(sorted.length / 2)];};
  const pixelLines = [];
  for (const segment of segments) {
    const indices = frames.map((f, i) => i).filter(i => i < decodedFrames && frames[i].t >= segment.start && frames[i].t < segment.start + segment.duration);
    const closed = indices.reduce((a, b) => rendered[b] < rendered[a] ? b : a, indices[0]);
    const distance = indices.map(i => changedPixels(i, closed));
    const open = indices.filter(i => rendered[i] > 0.5).map(i => distance[indices.indexOf(i)]);
    const control = indices.filter(i => i !== closed && rendered[i] < 0.05).map(i => distance[indices.indexOf(i)]);
    pixelLines.push({emotion: segment.emotion, closedReferenceFrame: closed,
                     openFrames: open.length, controlFrames: control.length,
                     openMedianChangedPixels: median(open), controlMedianChangedPixels: median(control),
                     ratio: +(median(open) / Math.max(1, median(control))).toFixed(2),
                     correlation: +pearson(indices.map(i => rendered[i]), distance).toFixed(4)});
  }
  expect('mouth_pixels_change_with_the_parameter',
         pixelLines.every(l => l.openFrames >= 5 && l.controlFrames >= 5 && l.ratio >= 1.8 && l.correlation > 0.4),
         {band: BAND, perLine: pixelLines});

  result.summary = {video: MP4, durationSeconds: result.playback.durationSeconds, frames: frames.length, fps,
                    lines: segments.map(s => ({emotion: s.emotion, text: s.text, start: +s.start.toFixed(3), duration: +s.duration.toFixed(3)})),
                    credit: report.lines[0].credit, engine: report.voice.version};
} catch (error) {
  result.failures.push(error.stack || String(error));
}

await writeFile(`${OUT}/verification.json`, JSON.stringify(result, null, 2));
console.log(JSON.stringify(result, null, 2));
if (result.failures.length) process.exitCode = 1;
