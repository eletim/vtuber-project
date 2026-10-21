"""Exact, independently reloaded PSD/runtime invariants for the v17 skin fix."""
from copy import deepcopy
from io import BytesIO
import hashlib
import itertools
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build_skin_v17 import (
    BASELINE, SOURCE, SOURCE_SHA256, PSD, MODEL, MANIFEST, ORIGINAL_SPRITE,
    SPRITE, CANDIDATE, PROTECTED_MASK, TARGET, TARGET_RECT,
    inspect_psd, decode_record, tree_signature, patch_psd, verify_patch,
    validate_candidate, sha256,
)
from psd_groups_v14 import (
    PixelLayer, LayerGroup, write_psd_groups, parse_psd_groups, composite_psd_groups,
)
from build_expressions_v15 import alpha_over, PARTS


def rgba(path):
    with Image.open(path) as image:
        return np.asarray(image.convert('RGBA')).copy()


def flatten(nodes):
    for node in nodes:
        if isinstance(node, LayerGroup):
            yield from flatten(node.children)
        else:
            yield node


def git_blob(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', f'{BASELINE}:{path}'])


class SurgicalSkinPatchUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'fixture.psd'
        baseline = np.full((12, 14, 4), (230, 200, 190, 255), dtype=np.uint8)
        feature = np.zeros_like(baseline)
        feature[3:8, 4:10] = (180, 150, 140, 255)
        feature[3, 4] = (170, 150, 140, 60)
        feature[5, 6] = (90, 45, 35, 255)  # Protected authored lip.
        tree = [LayerGroup('Outer 日本語', [LayerGroup('Inner', [
            PixelLayer(TARGET, feature, False),
            PixelLayer('unchanged.feature', feature, True),
        ], True, True)], False), PixelLayer('neutral', baseline)]
        write_psd_groups(self.path, baseline, tree, compression_level=9)
        self.source = self.path.read_bytes()
        self.original = feature[3:8, 4:10].copy()
        self.candidate = self.original.copy()
        self.candidate[1, 1, :3] = (230, 190, 175)
        self.protected = np.zeros(self.original.shape[:2], bool)
        self.protected[2, 2] = True

    def test_patch_is_deterministic_and_preserves_other_record_payloads(self):
        result, report = patch_psd(self.source, self.candidate, self.protected)
        repeated, _ = patch_psd(self.source, self.candidate, self.protected)
        self.assertEqual(result, repeated)
        self.assertEqual(report['unchanged_other_pixel_layers'], 2)
        self.assertEqual(report['changed_rgb_pixels'], 1)
        old, new = inspect_psd(self.source), inspect_psd(result)
        self.assertEqual(tree_signature(old), tree_signature(new))
        self.assertEqual(self.source[old.mask_end:], result[new.mask_end:])
        self.path.write_bytes(result)
        reloaded, size = parse_psd_groups(self.path)
        self.assertEqual(size, (14, 12))
        actual = next(p.rgba for p in flatten(reloaded) if p.name == TARGET)
        np.testing.assert_array_equal(actual[3:8, 4:10], self.candidate)
        np.testing.assert_array_equal(composite_psd_groups(reloaded), rgba(self.path))

    def test_alpha_change_is_rejected(self):
        broken = self.candidate.copy()
        broken[0, 0, 3] += 1
        with self.assertRaisesRegex(ValueError, 'alpha'):
            patch_psd(self.source, broken, self.protected)

    def test_protected_lip_change_is_rejected(self):
        broken = self.candidate.copy()
        broken[2, 2, 0] += 1
        with self.assertRaisesRegex(ValueError, 'protected lip'):
            patch_psd(self.source, broken, self.protected)

    def test_wrong_dimensions_and_empty_mask_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            patch_psd(self.source, self.candidate[:, :-1], self.protected)
        with self.assertRaisesRegex(ValueError, 'must not be empty'):
            patch_psd(self.source, self.candidate, np.zeros_like(self.protected))

    def test_transparent_rgb_change_is_rejected(self):
        original = self.original.copy()
        original[0, 0] = 0
        candidate = original.copy()
        candidate[0, 0, 0] = 12
        with self.assertRaisesRegex(ValueError, 'transparent'):
            validate_candidate(original, candidate, self.protected)

    def test_saved_neutral_damage_is_rejected(self):
        result, _ = patch_psd(self.source, self.candidate, self.protected)
        damaged = result[:-1] + bytes([result[-1] ^ 1])
        with self.assertRaisesRegex(ValueError, 'neutral merged'):
            verify_patch(self.source, damaged, self.candidate, self.protected)

    def test_truncated_channel_is_rejected(self):
        with self.assertRaises(ValueError):
            inspect_psd(self.source[:100])


@unittest.skipUnless(PSD.exists(), 'The reviewed v17 candidate has not been integrated yet')
class SkinV17IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_bytes = SOURCE.read_bytes()
        cls.new_bytes = PSD.read_bytes()
        cls.before = inspect_psd(cls.source_bytes)
        cls.after = inspect_psd(cls.new_bytes)
        # Independent, existing PSD parser rather than the surgical patch reader.
        cls.tree, cls.size = parse_psd_groups(PSD)
        cls.groups = {g.name: g for g in cls.tree if isinstance(g, LayerGroup)}
        cls.layers = {layer.name: layer for layer in flatten(cls.tree)}
        cls.baseline = rgba(SOURCE)
        cls.candidate = rgba(CANDIDATE)
        with Image.open(PROTECTED_MASK) as image:
            cls.protected = np.asarray(image.convert('L')) > 0
        cls.manifest = json.loads(MANIFEST.read_text())
        cls.original_manifest = json.loads(git_blob('runtime/model/model.json'))
        cls.expressions = {e['id']: e for e in cls.manifest['expressions']}

    def test_exact_original_layer_count_tree_and_all_metadata(self):
        self.assertEqual(self.size, (1086, 1448))
        self.assertEqual(len(self.after.records), 129)
        self.assertEqual(len(self.layers), 115)
        self.assertEqual(len(self.groups), 7)
        self.assertEqual(tree_signature(self.before), tree_signature(self.after))
        for old, new in zip(self.before.records, self.after.records):
            self.assertEqual(old.metadata_bytes(), new.metadata_bytes(), old.name)
            if old.name != TARGET:
                self.assertEqual(old.raw, new.raw, old.name)
                self.assertEqual(old.channels, new.channels, old.name)

    def test_114_other_pixel_layers_are_exact_after_independent_decode(self):
        preserved = 0
        for record in self.before.records:
            if record.section is not None or record.name == TARGET:
                continue
            x0, y0, x1, y1 = record.bbox
            original = decode_record(record)
            actual = self.layers[record.name].rgba
            np.testing.assert_array_equal(actual[y0:y1, x0:x1], original, err_msg=record.name)
            self.assertEqual(int(np.count_nonzero(actual)), int(np.count_nonzero(original)), record.name)
            preserved += 1
        self.assertEqual(preserved, 114)

    def test_corrected_sprite_psd_and_protected_lip_are_pixel_exact(self):
        record = self.before.named(TARGET)
        original = decode_record(record)
        actual = decode_record(self.after.named(TARGET))
        self.assertEqual(record.bbox, TARGET_RECT)
        self.assertEqual(actual.shape, (69, 91, 4))
        np.testing.assert_array_equal(actual, self.candidate)
        np.testing.assert_array_equal(actual, rgba(SPRITE))
        np.testing.assert_array_equal(original, rgba(ORIGINAL_SPRITE))
        np.testing.assert_array_equal(actual[:, :, 3], original[:, :, 3])
        np.testing.assert_array_equal(actual[self.protected], original[self.protected])
        self.assertGreater(int(np.count_nonzero(self.protected)), 0)
        self.assertGreater(int(np.count_nonzero(np.any(actual[:, :, :3] != original[:, :, :3], axis=2))), 0)
        old_alpha = next(c.payload for c in record.channels if c.channel_id == -1)
        new_alpha = next(c.payload for c in self.after.named(TARGET).channels if c.channel_id == -1)
        self.assertEqual(old_alpha, new_alpha)

    def test_neutral_pixels_and_saved_merged_preview_are_exact(self):
        np.testing.assert_array_equal(composite_psd_groups(self.tree), self.baseline)
        np.testing.assert_array_equal(rgba(PSD), self.baseline)
        self.assertEqual(self.source_bytes[self.before.mask_end:], self.new_bytes[self.after.mask_end:])

    def test_manifest_changes_only_versioned_sprite_and_psd_pointers(self):
        expected = deepcopy(self.original_manifest)
        expected['expression_source_psd'] = str(PSD.relative_to(ROOT))
        expression = next(e for e in expected['expressions'] if e['id'] == 'surprised')
        part = next(p for p in expression['parts'] if p['name'] == 'mouth.closed')
        part['file'] = str(SPRITE.relative_to(MODEL))
        self.assertEqual(self.manifest, expected)
        # Rects, eye states, parameters, mouth geometry, and motion are included.

    def test_all_64_runtime_endpoint_combinations_match_new_psd(self):
        count = 0
        for key, entry in self.expressions.items():
            base = rgba(MODEL/entry['base'])
            sprites = {}
            for part in entry['parts']:
                full = np.zeros_like(base)
                x0, y0, x1, y1 = part['rect']
                full[y0:y1, x0:x1] = rgba(MODEL/part['file'])
                sprites[part['name']] = full
            for bits in itertools.product((0, 1), repeat=3):
                states = {name: 'open' if value else 'closed' for name, value in zip(PARTS, bits)}
                runtime = base.copy()
                for part in entry['parts']:
                    name, state = part['name'].rsplit('.', 1)
                    if states[name] == state:
                        runtime = alpha_over(runtime, sprites[part['name']])
                prefix = '' if key == 'neutral' else key+'.'
                show = [prefix+name+'.'+states[name] for name in PARTS]
                hide = [prefix+name+'.'+('closed' if states[name] == 'open' else 'open') for name in PARTS]
                if key == 'neutral':
                    check_tree = self.tree
                else:
                    show.append(entry['folder'])
                    check_tree = [self.groups[entry['folder']], PixelLayer('verified neutral base', self.baseline)]
                rendered = composite_psd_groups(check_tree, show=show, hide=hide)
                np.testing.assert_array_equal(runtime, rendered, err_msg=f'{key}/{bits}')
                np.testing.assert_array_equal(runtime[:, :, 3], self.baseline[:, :, 3], err_msg=f'{key}/{bits} alpha')
                count += 1
        self.assertEqual(count, 64)

    def test_preexisting_artwork_and_historical_v17_motion_sources_are_exact(self):
        rows = subprocess.check_output([
            'git', '-C', str(ROOT), 'ls-tree', '-r', '-z', BASELINE,
            'assets', 'runtime/model', 'runtime/web',
        ]).split(b'\0')
        checked = 0
        for row in rows:
            if not row:
                continue
            metadata, path_bytes = row.split(b'\t', 1)
            _, kind, expected_hash = metadata.split()
            if kind != b'blob':
                continue
            relative = path_bytes.decode()
            if relative == 'runtime/model/model.json':
                continue  # Separately checked above, with only two fields allowed.
            # v18 deliberately adds body/arm motion. Keep the v17 historical
            # no-motion-change assertion pinned to its accepted commit, while
            # continuing to test all current artwork/model bytes below.
            if relative.startswith('runtime/web/'):
                actual = subprocess.check_output(['git', '-C', str(ROOT), 'show',
                    f'e70184fb6c5bc6fe33e1d0da0cd47f0fc2970415:{relative}'])
            else:
                actual = (ROOT/relative).read_bytes()
            git_hash = hashlib.sha1(b'blob '+str(len(actual)).encode()+b'\0'+actual).hexdigest()
            self.assertEqual(git_hash, expected_hash.decode(), relative)
            checked += 1
        self.assertGreater(checked, 300)
        self.assertEqual(sha256(SOURCE.read_bytes()), SOURCE_SHA256)

    def test_regeneration_matches_frozen_psd_byte_for_byte(self):
        regenerated, report = patch_psd(self.source_bytes, self.candidate, self.protected)
        self.assertEqual(regenerated, self.new_bytes)
        self.assertEqual(report['unchanged_other_pixel_layers'], 114)
        self.assertEqual(report['protected_lip_changes'], 0)
        self.assertEqual(report['alpha_changes'], 0)


if __name__ == '__main__':
    unittest.main()
