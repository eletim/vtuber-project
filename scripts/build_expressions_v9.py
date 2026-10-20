#!/usr/bin/env python3
"""Keep v8 art; install a painted skin reveal beneath independent expressions."""
from pathlib import Path
import json
import sys
import hashlib
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_psd import parse_psd, composite
from psd_writer import write_psd

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'assets/parts/v9'
SOURCE = ROOT / 'assets/parts/v8/koma_neck_clothing_cleaned_v8.psd'
PARTS = ('eye_screen_left', 'eye_screen_right', 'mouth')


def build():
    layers, size = parse_psd(SOURCE)
    baseline = composite(layers)
    original_layers = {r['name']: r for r in layers}
    h, w = baseline.shape[:2]
    painting = np.zeros_like(baseline)
    # Crop transform is recorded with the source; never align by eyeballing.
    painting[130:480, 305:730, :3] = np.asarray(Image.open(
        DEST / 'face_skin_painted_source.png').convert('RGB').resize(
        (425, 350), Image.Resampling.LANCZOS))
    distances = np.stack([distance_transform_edt(
        original_layers[p+'.open']['data'][:, :, 3] == 0) for p in PARTS])
    nearest = distances.argmin(axis=0)
    distance = distances.min(axis=0)
    # Painted skin replaces the whole old polygon and blends only in the
    # surrounding original artwork. Open restoration sprites cover the support
    # exactly, so neutral expression stays byte-identical to the source PSD.
    alpha = np.rint(np.clip((16-distance)/8, 0, 1)*255).astype('uint8')
    painting[:, :, 3] = alpha
    support = alpha > 0
    assert not support[:130].any() and not support[480:].any()
    assert not support[:, :305].any() and not support[:, 730:].any()
    for i, p in enumerate(PARTS):
        record = original_layers[p+'.open']
        record['data'] = np.zeros_like(baseline)
        mask = support & (nearest == i)
        record['data'][mask] = baseline[mask]
    index = max(i for i, r in enumerate(layers) if r['name'] in
                [p+'.open' for p in PARTS]) + 1
    layers.insert(index, {'name': 'face_expression_painted_skin_v9',
                          'visible': True, 'data': painting})
    assert np.array_equal(composite(layers), baseline)
    path = DEST / 'koma_expressions_v9.psd'
    write_psd(path, baseline, [(r['name'], r['data']) for r in layers],
              hidden_names=[r['name'] for r in layers if not r['visible']],
              compression_level=9, merged_rle=True)
    check, checked_size = parse_psd(path)
    assert checked_size == size
    states = {'normal': (), 'eyes_closed': PARTS[:2],
              'mouth_closed': PARTS[2:], 'both_closed': PARTS}
    strip = Image.new('RGB', (425*4, 380), '#eeeae6')
    frames = []
    measurements = {}
    for i, (name, closed) in enumerate(states.items()):
        hide = [p+'.open' for p in closed]
        show = [p+'.closed' for p in closed]
        frame = composite(check, hide=hide, show=show)
        assert np.array_equal(frame, composite(layers, hide=hide, show=show))
        assert np.array_equal(frame[:, :, 3], baseline[:, :, 3])
        Image.fromarray(frame).save(DEST / f'{name}.png')
        crop = Image.fromarray(frame).crop((305, 130, 730, 480)).convert('RGB')
        strip.paste(crop, (425*i, 30))
        ImageDraw.Draw(strip).text((425*i+8, 8), name, fill='black')
        frames.append(crop)
        measurements[name] = {'alpha_changes': 0, 'psd_roundtrip_exact': True}
    strip.save(DEST / 'four_expressions.png')
    palette = strip.quantize(colors=244, method=Image.Quantize.MEDIANCUT)
    gif_frames = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    gif_frames[0].save(DEST / 'expression_cycle.gif', save_all=True,
                   append_images=gif_frames[1:], duration=[900, 650, 650, 900], loop=0)
    hidden = composite(check, hide=[p+'.open' for p in PARTS])
    Image.fromarray(hidden).save(DEST / 'features_hidden.png')
    Image.fromarray(hidden).crop((305, 130, 730, 480)).resize((850,700)).save(
        DEST / 'skin_reveal_detail.png')
    approved = np.asarray(Image.open(ROOT/'assets/original/koma_confirmed.png').convert('RGB'))
    inherited_difference = np.any(baseline[:,:,:3] != approved, axis=2) & (baseline[:,:,3] > 0)
    report = {'source_psd': str(SOURCE.relative_to(ROOT)),
              'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
              'layer_count': len(check), 'normal_changed_pixels_vs_source': 0,
              'inherited_foreground_rgb_differences_vs_original': int(inherited_difference.sum()),
              'states': measurements, 'visual_review': 'PENDING',
              'skin_source_crop': [305,130,730,480],
              'toggle': 'Hide corresponding .open and show .closed; normal shows all .open.',
              'scope': 'Expression skin only; inherited hair/clothing defects remain.'}
    (DEST/'review.json').write_text(json.dumps(report, indent=2)+'\n')
    print(path)


if __name__ == '__main__':
    build()
