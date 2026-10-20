#!/usr/bin/env python3
"""Integrate localized arm/cuff paintings and extract independently movable limbs."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from audit_psd import composite, parse_psd
from clean_neck_clothing_v8 import _moved_layers
from psd_writer import write_psd

ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / 'assets/parts/v8'
SOURCE = DIRECTORY / 'koma_neck_clothing_cleaned_v8.psd'
OUTPUT = DIRECTORY / 'koma_sleeves_arms_hands_cleaned_v8.psd'
CONFIG = ROOT / 'config/koma_sleeves_v8.json'
PAINTS = ('arms_painted_underlayer_v8.png', 'inner_cuffs_painted_underlayer_v8.png')


def ownership_masks():
    config = json.loads(CONFIG.read_text())
    masks = {}
    for name, points in config['regions'].items():
        canvas = Image.new('L', tuple(config['reference_size']))
        ImageDraw.Draw(canvas).polygon([tuple(p) for p in points], fill=255)
        masks[name] = np.asarray(canvas) > 0
    # Wrists/hands sit in front of the sleeve openings.
    for side in ('left', 'right'):
        masks[f'{side}_arm_sleeve'] &= ~masks[f'{side}_hand']
    return masks


def clean_layers(source):
    layers = copy.deepcopy(source)
    approved = composite(source)
    masks = ownership_masks()
    scope = np.logical_or.reduce(list(masks.values()))
    # Remove fixed duplicates, including fragments in body_remaining. Preserve
    # every pixel outside the explicitly authored limb ownership boundaries.
    for record in layers:
        if record['visible']:
            record['data'][scope] = 0
    paints = [np.asarray(Image.open(DIRECTORY / name).convert('RGBA')) for name in PAINTS]
    for paint in paints:
        if paint.shape != approved.shape:
            raise AssertionError('paint canvas does not match source')
    added = []
    def add(name, pixels, mask):
        data = np.zeros_like(approved)
        data[mask] = pixels[mask]
        data[data[:, :, 3] == 0] = 0
        added.append(dict(name=name, data=data, visible=True))
    yy, _ = np.indices(scope.shape)
    for side in ('left', 'right'):
        hand = masks[f'{side}_hand']
        sleeve = masks[f'{side}_arm_sleeve']
        add(f'{side}_hand', approved, hand)
        add(f'{side}_arm_sleeve', approved, sleeve)
        # Inner fabric travels with its sleeve. It is completely covered in
        # the rest pose; hand hiding exposes the small cuff overlap only.
        cuff = hand & (yy < (1224 if side == 'left' else 1252))
        add(f'{side}_inner_cuff', paints[1], cuff & (approved[:, :, 3] == 255))
        # Do not leave a second palm/fingers behind when a hand moves. A short
        # wrist overlap supports small rigging offsets under the sleeve hem.
        arm = (sleeve | (hand & (yy < (1234 if side == 'left' else 1262))))
        arm &= approved[:, :, 3] == 255
        # Keep torso repairs fixed when an arm is moved. These boundaries lie
        # in the transparent gap between the generated arm and the garment.
        boundary = Image.new('L', (approved.shape[1], approved.shape[0]))
        points = ([(0, 600), (367, 600), (353, 830), (305, 990),
                   (241, 1170), (220, 1270), (0, 1270)] if side == 'left' else
                  [(772, 600), (1085, 600), (1085, 1290), (895, 1290),
                   (856, 1100), (786, 880)])
        ImageDraw.Draw(boundary).polygon(points, fill=255)
        skin = np.asarray(boundary) > 0
        add(f'{side}_arm_wrist_join', paints[0], arm & skin)
        add(f'{side}_torso_join', paints[0], arm & ~skin)
    # Reuse the existing part names; the obsolete illustrated/base limb layers
    # must not retain fixed copies beyond the new masks either. Keep their
    # out-of-scope pixels as local residuals so the approved pose is unchanged.
    for record in layers:
        if record['name'] in masks:
            record['name'] += '.outside_ownership'
    layers = added + layers
    if not np.array_equal(composite(layers), approved):
        raise AssertionError('approved pose changed')
    return layers


def scenes(layers):
    groups = {
        'sleeves': tuple(f'{side}_{part}' for side in ('left', 'right')
                         for part in ('arm_sleeve', 'inner_cuff')),
        'hands': ('left_hand', 'right_hand'),
    }
    result = {}
    for label, names in groups.items():
        result[label + '_hidden'] = composite(layers, hide=names)
        result[label + '_moved'] = composite(_moved_layers(
            layers, {name: ((-8 if name.startswith('left') else 8), -4) for name in names}))
    result['sleeves_and_hands_hidden'] = composite(layers, hide=groups['sleeves'] + groups['hands'])
    return result


def write_preview(images, path):
    panel = Image.new('RGB', (1086, 3 * 510), '#e8e4e0')
    draw = ImageDraw.Draw(panel)
    for index, (name, data) in enumerate(images.items()):
        image = Image.fromarray(data).crop((0, 470, 1086, 1448))
        image.thumbnail((543, 489), Image.Resampling.LANCZOS)
        x, y = index % 2 * 543, index // 2 * 510
        panel.paste(image, (x, y + 21), image)
        draw.text((x + 8, y + 4), name.replace('_', ' '), fill='#302020')
    panel.save(path)


def build_candidate(destination=OUTPUT):
    destination = Path(destination)
    source, size = parse_psd(SOURCE)
    layers = clean_layers(source)
    approved = composite(source)
    write_psd(destination, approved, [(r['name'], r['data']) for r in layers],
              hidden_names=[r['name'] for r in layers if not r['visible']])
    reloaded, actual_size = parse_psd(destination)
    assert size == actual_size
    assert np.array_equal(composite(reloaded), approved)
    views = scenes(reloaded)
    report = {
        'source': str(SOURCE.relative_to(ROOT)),
        'layer_count': len(reloaded),
        'initial_rgba_changed_pixels': 0,
        'paint_sha256': {name: hashlib.sha256((DIRECTORY / name).read_bytes()).hexdigest() for name in PAINTS},
        'scenes': {name: {'changed_pixels': int(np.count_nonzero(np.any(view != approved, axis=2)))}
                   for name, view in views.items()},
        'movement_pixels': {'left': [-8, -4], 'right': [8, -4]},
        'note': 'Removed outer cloth/hand silhouettes may become transparent. This is not a zero-hole audit.',
        'cubism_ready': False,
    }
    write_preview({'approved_pose': approved, **views}, destination.with_suffix('.png'))
    destination.with_suffix('.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    print(json.dumps(build_candidate(), indent=2))
