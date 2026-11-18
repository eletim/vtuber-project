#!/usr/bin/env python3
"""Reproduce the reviewed surprised-mouth skin candidate in an explicit folder.

Only image-tool-painted skin is composited with the existing original lip and
highlight pixels. No hue correction, procedural painting, or geometry edits are
performed. The frozen v15 manifest supplies the unmodified source endpoint even
after the active runtime manifest points to the versioned correction.

Usage: python scripts/build_skin_candidate_v17.py --output /tmp/koma-candidate
This script does not modify the runtime, PSD, source images, or manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_fill_holes, distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'runtime/model'
MANIFEST = ROOT / 'tests/fixtures/model_v15.json'
SOURCE = ROOT / 'assets/parts/v17/sources/surprised_skin_corrected.png'
SOURCE_SHA256 = '0dc3b86ea7056a7794bd5e6f73e4642a5b4dd10dfa108ed1d8ddd674e4c4c99a'
ORIGINAL_SHA256 = '2ae283bd6577af767f61b9d63dd921082ffd98debdec95a8d06cdcefa0ff8427'
CROP = (340, 165, 740, 465)
RECT = (510, 321, 601, 390)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bounds(mask, offset=(0, 0)):
    y, x = np.nonzero(mask)
    if not len(x):
        return None
    return [int(x.min()+offset[0]), int(y.min()+offset[1]),
            int(x.max()+offset[0]+1), int(y.max()+offset[1]+1)]


def create_candidate(original, clean):
    """Return RGBA, protected original-art mask, and skin compositing weight."""
    if original.shape != (69, 91, 4) or clean.shape != original.shape:
        raise ValueError('Expected unchanged 91 x 69 RGBA mouth rectangles')
    yy, xx = np.indices(original.shape[:2])
    xx += RECT[0]
    yy += RECT[1]
    lip_gate = (xx >= 535) & (xx <= 568) & (yy >= 346) & (yy <= 369)

    def ink(image):
        rgb = image.astype(np.int16)
        return (rgb[:, :, 0]-rgb[:, :, 1] > 20) & (rgb[:, :, 1] < 230)

    old_ink = ink(original) & lip_gate
    new_ink = ink(clean) & lip_gate
    # Include the new painting's ink footprint so its changed lip cannot leak
    # through. Pale old lip highlights are protected explicitly, not recolored.
    highlights = (xx >= 543) & (xx <= 556) & (yy >= 358) & (yy <= 362)
    lip_seed = binary_fill_holes(old_ink | new_ink | highlights)
    lip_protected = distance_transform_edt(~lip_seed) <= 2
    # The broad historical support grazes a small fragment of the nose.
    other_ink = (ink(original) | ink(clean)) & ~lip_gate & (original[:, :, 3] > 0)
    other_protected = (distance_transform_edt(~other_ink) <= 2
                       if other_ink.any() else other_ink)
    protected = lip_protected | other_protected
    replace = np.clip(distance_transform_edt(~protected)/2, 0, 1)
    replace[original[:, :, 3] == 0] = 0
    candidate = original.copy()
    candidate[:, :, :3] = np.rint(
        original[:, :, :3]*(1-replace[:, :, None]) +
        clean[:, :, :3]*replace[:, :, None]).clip(0, 255).astype(np.uint8)
    assert np.array_equal(candidate[:, :, 3], original[:, :, 3])
    assert np.array_equal(candidate[protected], original[protected])
    assert np.array_equal(candidate[original[:, :, 3] == 0],
                          original[original[:, :, 3] == 0])
    assert np.all(protected[new_ink]), 'Replacement lip ink leaked into the result'
    assert np.array_equal(candidate[replace == 1, :3], clean[replace == 1, :3])
    details = {
        'original_ink_bbox': bounds(old_ink, RECT[:2]),
        'generated_ink_bbox': bounds(new_ink, RECT[:2]),
        'protected_lip_bbox': bounds(lip_protected, RECT[:2]),
        'original_lip_ink_pixels': int(old_ink.sum()),
        'generated_lip_ink_pixels': int(new_ink.sum()),
        'protected_lip_pixels': int(lip_protected.sum()),
        'other_ink_protected_pixels': int(other_protected.sum()),
    }
    return candidate, protected, replace, details


def build(output):
    output = Path(output).expanduser().resolve()
    manifest = json.loads(MANIFEST.read_text())
    expression = next(e for e in manifest['expressions'] if e['id'] == 'surprised')
    parts = {p['state']: p for p in expression['parts']
             if p['parameter'] == 'ParamMouthOpenY'}
    original_path = MODEL / parts['closed']['file']
    if tuple(parts['closed']['rect']) != RECT or tuple(parts['open']['rect']) != RECT:
        raise ValueError('Frozen mouth rectangles differ from the reviewed candidate')
    if sha256(original_path) != ORIGINAL_SHA256 or sha256(SOURCE) != SOURCE_SHA256:
        raise ValueError('Original endpoint or image-tool source hash changed')
    if output == original_path.parent or output == SOURCE.parent:
        raise ValueError('Output must not overwrite the runtime or source folder')
    original = np.asarray(Image.open(original_path).convert('RGBA')).copy()
    approved = np.asarray(Image.open(MODEL / parts['open']['file']).convert('RGBA')).copy()
    source = Image.open(SOURCE).convert('RGBA')
    if source.size != (1448, 1086):
        raise ValueError('Unexpected image-tool source dimensions')
    mapped = source.resize((400, 300), Image.Resampling.LANCZOS)
    x0, y0, x1, y1 = RECT
    clean = np.asarray(mapped.crop((x0-CROP[0], y0-CROP[1],
                                    x1-CROP[0], y1-CROP[1]))).copy()
    candidate, protected, replace, details = create_candidate(original, clean)
    base = Image.open(MODEL / expression['base']).convert('RGBA')
    base_crop = np.asarray(base)[y0:y1, x0:x1]
    # Fixed before-defined skin selection, excluding preserved original artwork.
    skin = ((original[:, :, 3] == 255) & (approved[:, :, 3] == 255) & ~protected &
            (approved[:, :, 0] > 235) & (approved[:, :, 1] > 205) &
            (approved[:, :, 2] > 195) & (original[:, :, 0] > 235) &
            (original[:, :, 1] > 205) & (original[:, :, 2] > 195))

    def compare(a, b):
        delta = a[:, :, :3].astype(float)-b[:, :, :3].astype(float)
        luminance = delta @ np.array([.2126, .7152, .0722])
        return {'mean_RGB': np.round(delta[skin].mean(0), 4).tolist(),
                'median_luminance': round(float(np.median(luminance[skin])), 4),
                'p05_p95_luminance': np.round(np.quantile(luminance[skin], [.05, .95]), 4).tolist(),
                'skin_pixels_luminance_below_minus3': int(np.sum(luminance[skin] < -3))}

    def render(art):
        canvas = base.copy()
        for part in expression['parts']:
            if part['parameter'] == 'ParamMouthOpenY':
                if part['state'] == 'closed':
                    canvas.alpha_composite(Image.fromarray(art), tuple(part['rect'][:2]))
            elif part['state'] == 'open':
                canvas.alpha_composite(Image.open(MODEL / part['file']).convert('RGBA'),
                                       tuple(part['rect'][:2]))
        return canvas

    output.mkdir(parents=True, exist_ok=True)
    Image.fromarray(candidate).save(output / 'mouth_closed.png')
    Image.fromarray((protected*255).astype(np.uint8)).save(output / 'protected_original_art.png')
    Image.fromarray(np.rint(replace*255).astype(np.uint8)).save(output / 'image_tool_skin_weight.png')
    mapped.save(output / 'image_tool_corrected_mapped.png')
    before, after = render(original), render(candidate)
    before.crop(CROP).save(output / 'before_face.png')
    after.crop(CROP).save(output / 'candidate_face.png')
    after.save(output / 'candidate_full.png')
    changed = np.any(candidate != original, axis=2)
    metrics = {
        'original': str(original_path.relative_to(ROOT)), 'original_sha256': ORIGINAL_SHA256,
        'frozen_manifest': str(MANIFEST.relative_to(ROOT)),
        'image_tool_source': str(SOURCE.relative_to(ROOT)), 'image_tool_source_sha256': SOURCE_SHA256,
        'candidate_sha256': sha256(output / 'mouth_closed.png'),
        'source_mapping': {'original_size': list(source.size), 'resize_to': [400, 300],
                           'full_crop': list(CROP), 'translation': [0, 0]},
        'rect': list(RECT), 'alpha_exact': True, 'original_protected_pixels_exact': True,
        'new_lip_ink_included_in_protected_mask': True, **details,
        'changed_rgb_pixels': int(changed.sum()), 'changed_bbox': bounds(changed, RECT[:2]),
        'fixed_skin_count': int(skin.sum()),
        'original_vs_approved_open_skin': compare(original, approved),
        'candidate_vs_approved_open_skin': compare(candidate, approved),
        'mapped_source_vs_approved_open_skin': compare(clean, approved),
        'candidate_vs_base_skin': compare(candidate, base_crop),
    }
    (output / 'metrics.json').write_text(json.dumps(metrics, ensure_ascii=False, indent=2)+'\n')
    sheet = Image.new('RGB', (1200, 338), '#fff9f4')
    draw = ImageDraw.Draw(sheet)
    poses = [('Before: original gray skin', before.crop(CROP)),
             ('Candidate: original lip + painted skin', after.crop(CROP)),
             ('Approved V14 open pose', Image.open(ROOT / 'assets/parts/v14/previews/surprised_full.png').crop(CROP))]
    for i, (title, pose) in enumerate(poses):
        sheet.paste(pose, (i*400, 28))
        draw.text((i*400+8, 8), title, fill='black')
    sheet.save(output / 'comparison.png')
    return metrics


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='Explicit candidate output directory; never defaults to production')
    args = parser.parse_args()
    print(json.dumps(build(args.output), ensure_ascii=False, indent=2))
