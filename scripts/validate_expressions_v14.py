#!/usr/bin/env python3
"""Independent psd-tools audit of the shipped expression collection.

Run after building, with psd-tools installed:
    python scripts/validate_expressions_v14.py

The writer's parser/compositor is deliberately not used. All rendered audit
images come from reopened PSD layers, never from the embedded PSD preview.
The legacy source's intended order is reversed in memory for rendering because
that older writer serialized its top-first API directly into bottom-first PSD
storage. No source file is changed. Floating-point quantization up to one byte
is reported as tolerance, never described as pixel-exact.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage, __version__ as PSD_TOOLS_VERSION


ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'assets/parts/v14/koma_expression_collection_v14.psd'
CROP = (340, 165, 740, 465)
STATES = ('neutral', 'soft_smile', 'big_smile', 'worried', 'surprised',
          'bashful', 'displeased', 'thinking')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rgba(path):
    with Image.open(path) as image:
        return np.array(image.convert('RGBA'))


def stats(actual, expected):
    support = (actual[:, :, 3] > 0) | (expected[:, :, 3] > 0)
    delta = np.abs(actual.astype(np.int16) - expected.astype(np.int16))
    visible_max = int(delta[support].max()) if support.any() else 0
    return {
        'visible_rgba_exact': bool(not np.any(delta[support])),
        'visible_rgb_different_pixels': int(np.count_nonzero(np.any(delta[:, :, :3], axis=2) & support)),
        'alpha_different_pixels': int(np.count_nonzero(delta[:, :, 3])),
        'max_visible_rgba_error': visible_max,
        'max_alpha_error': int(delta[:, :, 3].max()),
        'alpha_support_exact': bool(np.array_equal(actual[:, :, 3] > 0, expected[:, :, 3] > 0)),
        'pass_with_one_byte_tolerance': bool(visible_max <= 1 and np.array_equal(actual[:, :, 3] > 0, expected[:, :, 3] > 0)),
        'fully_transparent_rgb_ignored': True,
    }


def render(psd, viewport=None):
    return np.array(psd.composite(viewport=viewport, ignore_preview=True,
                                  apply_icc=False).convert('RGBA'))


def select(groups, enabled=()):
    enabled = set(enabled)
    for group in groups:
        group.visible = group.name in enabled


def make_sheet(frames, path):
    sheet = Image.new('RGB', (1600, 720), '#eee6de')
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 19)
    for i, (key, frame) in enumerate(frames.items()):
        x, y = i % 4 * 400, i // 4 * 360
        image = Image.fromarray(frame)
        background = Image.new('RGBA', image.size, '#eee6de')
        background.alpha_composite(image)
        sheet.paste(background.convert('RGB'), (x, y))
        draw.text((x + 12, y + 316), key.replace('_', ' ').title(), fill='#49372d', font=font)
    sheet.save(path)


def audit(path, report_path, render_dir):
    source_path = ROOT / 'assets/parts/v10/koma_integrated_v10.psd'
    initial_sha = digest(path)
    psd = PSDImage.open(path)
    source = PSDImage.open(source_path)
    groups = [layer for layer in reversed(list(psd)) if layer.is_group()]
    actual_original = [layer for layer in reversed(list(psd)) if not layer.is_group()]
    original = list(source)  # Historical file's intended top-first order.
    assert len(groups) == 7, 'Expected seven expression folders'
    assert len(actual_original) == len(original) == 66, 'Expected 66 original layers'
    assert [layer.name for layer in actual_original] == [layer.name for layer in original], 'Original relative layer order changed'
    assert all(not group.visible for group in groups), 'Default expression folders must be hidden'
    assert all(len(group) == 1 and group[0].visible for group in groups), 'Each folder needs one visible child'
    for actual, expected in zip(actual_original, original):
        assert actual.bbox == expected.bbox, f'Layer position changed: {actual.name}'
        assert actual.visible == expected.visible, f'Layer visibility changed: {actual.name}'
        assert actual.opacity == expected.opacity, f'Layer opacity changed: {actual.name}'
        np.testing.assert_array_equal(np.array(actual.topil()), np.array(expected.topil()), err_msg=f'Layer artwork changed: {actual.name}')
    render_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(path.parent / 'sources/expression_support_mask.png') as support_image:
        support_face = np.array(support_image) > 0
    support = np.zeros((psd.height, psd.width), bool)
    support[CROP[1]:CROP[3], CROP[0]:CROP[2]] = support_face
    opaque_masks = {}
    for group in groups:
        layer = group[0]
        pixels = np.array(layer.topil().convert('RGBA'))
        local = np.zeros((psd.height, psd.width), np.uint8)
        left, top, right, bottom = layer.bbox
        local[top:bottom, left:right] = pixels[:, :, 3]
        opaque_masks[group.name] = local[CROP[1]:CROP[3], CROP[0]:CROP[2]] == 255

    neutral = render(psd)
    original_preview = load_rgba(source_path)
    embedded = load_rgba(path)
    assert np.array_equal(embedded, original_preview), 'Saved merged neutral is not byte-exact'
    frames = {}
    state_stats = {}
    for index, key in enumerate(STATES):
        select(groups, [] if index == 0 else [groups[index - 1].name])
        actual = neutral if index == 0 else render(psd)
        expected = load_rgba(path.parent / 'previews' / f'{key}_full.png')
        result = stats(actual, expected)
        result['outside_face_mask_changed_pixels_vs_independent_neutral'] = int(
            np.count_nonzero(np.any(actual != neutral, axis=2) & ~support))
        result['folder'] = groups[index - 1].name if index else None
        assert result['pass_with_one_byte_tolerance'], (key, result)
        assert result['outside_face_mask_changed_pixels_vs_independent_neutral'] == 0, (key, result)
        state_stats[key] = result
        face = actual[CROP[1]:CROP[3], CROP[0]:CROP[2]]
        frames[key] = face
        Image.fromarray(face).save(render_dir / f'{key}_independent_face.png')
        print(f'{key}: exact={result["visible_rgba_exact"]}, max RGBA error={result["max_visible_rgba_error"]}', flush=True)
    make_sheet(frames, render_dir / 'independent_contact_sheet.png')

    # Every pair is intentionally an unsupported artistic mix. Confirm folder
    # visibility works and the higher folder wins wherever its alpha is 255.
    pair_checks = []
    neutral_face = frames['neutral']
    for high, low in itertools.combinations(range(len(groups)), 2):
        selected = [groups[high].name, groups[low].name]
        select(groups, selected)
        frame = render(psd, CROP)
        reference = frames[STATES[high + 1]]
        opaque = opaque_masks[selected[0]]
        max_error = int(np.abs(frame[opaque].astype(int) - reference[opaque].astype(int)).max())
        outside = int(np.count_nonzero(np.any(frame != neutral_face, axis=2) & ~support_face))
        assert max_error <= 1 and outside == 0, (selected, max_error, outside)
        pair_checks.append({'folders': selected, 'top_folder_opaque_region_max_error': max_error,
                            'outside_face_mask_changed_pixels': outside})
    select(groups, [group.name for group in groups])
    all_on = render(psd, CROP)
    assert not np.any(np.any(all_on != neutral_face, axis=2) & ~support_face)
    Image.fromarray(all_on).save(render_dir / 'unsupported_all_folders_on.png')
    select(groups)
    reset = render(psd, CROP)
    assert np.array_equal(reset, neutral_face), 'All-folders-off reset changed neutral'

    # Compare all original eye/mouth swaps with the independent renderer.
    # This local in-memory reorder corrects the historical writer's file order
    # to its intended public order, without rewriting its source PSD.
    source._layers.reverse()
    source_names = {layer.name: layer for layer in source}
    actual_names = {layer.name: layer for layer in actual_original}
    blink_states = {
        'blink_left': ('eye_screen_left',),
        'blink_right': ('eye_screen_right',),
        'blink_both': ('eye_screen_left', 'eye_screen_right'),
        'closed_mouth': ('mouth',),
        'all_closed': ('eye_screen_left', 'eye_screen_right', 'mouth'),
    }
    blink_stats = {}
    for key, parts in blink_states.items():
        for mapping in (source_names, actual_names):
            for part in ('eye_screen_left', 'eye_screen_right', 'mouth'):
                mapping[part + '.open'].visible = part not in parts
                mapping[part + '.closed'].visible = part in parts
        actual, expected = render(psd, CROP), render(source, CROP)
        result = stats(actual, expected)
        assert result['visible_rgba_exact'], (key, result)
        blink_stats[key] = result
        Image.fromarray(actual).save(render_dir / f'neutral_{key}_independent.png')
    for part in ('eye_screen_left', 'eye_screen_right', 'mouth'):
        actual_names[part + '.open'].visible = True
        actual_names[part + '.closed'].visible = False
    assert np.array_equal(render(psd, CROP), neutral_face), 'Blink reset changed neutral'
    assert digest(path) == initial_sha, 'PSD changed during validation; rerun against final build'

    report = {
        'psd': str(path.relative_to(ROOT)), 'psd_sha256': initial_sha,
        'source_psd_sha256': digest(source_path), 'psd_tools_version': PSD_TOOLS_VERSION,
        'render_method': 'psd-tools composite(ignore_preview=True, apply_icc=False) from reopened PSD layers',
        'original_layers_exact_pixels_names_positions_visibility_relative_order': 66,
        'expression_folders': 7, 'pixel_layers': 73,
        'merged_neutral_byte_exact': True,
        'states': state_stats,
        'mixed_folder_checks': pair_checks,
        'all_folders_on_confined_to_face_support': True,
        'all_folders_off_reset_exact': True,
        'original_neutral_blink_states': blink_stats,
        'legacy_render_reference_stack_corrected_in_memory': True,
        'visual_review': {'status': 'Not performed by this automated script; inspect the independently rendered contact sheet.'},
        'limitations': [
            'True psd-tools renders have up to one byte of RGB/alpha quantization relative to the exact stored PNG previews.',
            'Only one expression folder should be enabled. PSD folders do not automatically enforce mutual exclusion.',
            'Original independent blink/mouth controls are supported in neutral only, not combined with painted expression folders.',
            'This is not a Live2D/Cubism rig or a Photoshop-application interaction test.'
        ],
        'pass': True,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f'PASS: report saved to {report_path}', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--psd', type=Path, default=DEFAULT)
    parser.add_argument('--report', type=Path, default=DEFAULT.parent / 'independent_validation.json')
    parser.add_argument('--renders', type=Path, default=Path('/tmp/v14_independent_psd_tools'))
    args = parser.parse_args()
    audit(args.psd, args.report, args.renders)
