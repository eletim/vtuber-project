"""Run directly or with unittest; psd-tools independent tests are optional."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from psd_groups_v14 import (LayerGroup, PixelLayer, composite_psd_groups,
                            parse_psd_groups, write_psd_groups)

try:
    from psd_tools import PSDImage
except ImportError:
    PSDImage = None


class PSDGroupsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'groups.psd'
        self.base = np.zeros((20, 30, 4), np.uint8)
        self.base[2:19, 2:29] = [180, 150, 140, 255]
        self.eye = np.zeros_like(self.base)
        self.eye[6:9, 9:15] = [30, 20, 10, 255]
        self.expression = np.zeros_like(self.base)
        self.expression[5:10, 8:16] = [100, 80, 70, 255]
        self.tree = [
            LayerGroup('01 笑顔 😀', [
                LayerGroup('内側', [PixelLayer('表情', self.expression)], expanded=True)
            ], visible=False),
            PixelLayer('eye.closed', self.expression, visible=False),
            PixelLayer('eye.open', self.eye),
            PixelLayer('base', self.base)]
        self.neutral = composite_psd_groups(self.tree)

    def tearDown(self):
        self.temp.cleanup()

    def test_nested_unicode_visibility_and_merged_preview(self):
        write_psd_groups(self.path, self.neutral, self.tree)
        parsed, size = parse_psd_groups(self.path)
        self.assertEqual(size, (30, 20))
        self.assertEqual([n.name for n in parsed], [n.name for n in self.tree])
        self.assertIsInstance(parsed[0], LayerGroup)
        self.assertFalse(parsed[0].visible)
        self.assertTrue(parsed[0].children[0].expanded)
        self.assertEqual(parsed[0].children[0].children[0].name, '表情')
        np.testing.assert_array_equal(composite_psd_groups(parsed), self.neutral)
        with Image.open(self.path) as preview:
            np.testing.assert_array_equal(np.array(preview.convert('RGBA')), self.neutral)
        np.testing.assert_array_equal(composite_psd_groups(parsed, show=['表情']), self.neutral)
        self.assertEqual(composite_psd_groups(parsed, show=['01 笑顔 😀'])[6, 10].tolist(), [100, 80, 70, 255])
        self.assertEqual(composite_psd_groups(parsed, show=['01 笑顔 😀'], hide=['内側'])[6, 10].tolist(), [30, 20, 10, 255])

    def test_raw_preview_and_hidden_names(self):
        write_psd_groups(self.path, self.base, self.tree, hidden_names=['eye.open'], merged_rle=False)
        parsed, _ = parse_psd_groups(self.path)
        np.testing.assert_array_equal(composite_psd_groups(parsed), self.base)
        with Image.open(self.path) as preview:
            np.testing.assert_array_equal(np.array(preview.convert('RGBA')), self.base)

    def test_partial_alpha_and_empty_layer(self):
        red = np.zeros_like(self.base)
        red[4, 4] = [200, 0, 0, 128]
        tree = [PixelLayer('empty', np.zeros_like(red)), PixelLayer('red', red)]
        rendered = composite_psd_groups(tree)
        np.testing.assert_array_equal(rendered, red)
        write_psd_groups(self.path, rendered, tree)
        parsed, _ = parse_psd_groups(self.path)
        np.testing.assert_array_equal(composite_psd_groups(parsed), rendered)

    def test_rejects_invalid_input(self):
        with self.assertRaises(ValueError):
            write_psd_groups(self.path, self.base, [])
        with self.assertRaises(ValueError):
            write_psd_groups(self.path, self.base, [PixelLayer('bad', self.eye[:1])])

    @unittest.skipIf(PSDImage is None, 'Install psd-tools for independent validation')
    def test_independent_psd_tools_real_render_and_group_tree(self):
        write_psd_groups(self.path, self.neutral, self.tree)
        psd = PSDImage.open(self.path)
        # psd-tools exposes BOTTOM FIRST, unlike our public tree.
        self.assertEqual([n.name for n in psd], ['base', 'eye.open', 'eye.closed', '01 笑顔 😀'])
        folder = psd[-1]
        self.assertEqual(folder.kind, 'group')
        self.assertFalse(folder.visible)
        self.assertFalse(folder[0][0].is_visible())
        self.assertLess(psd._record.layer_and_mask_information.layer_info.layer_count, 0)
        result = np.array(psd.composite(ignore_preview=True, apply_icc=False).convert('RGBA'))
        mask = self.neutral[:, :, 3] > 0
        self.assertLessEqual(np.abs(result[mask].astype(int) - self.neutral[mask].astype(int)).max(), 1)
        folder.visible = True
        result = np.array(psd.composite(ignore_preview=True, apply_icc=False).convert('RGBA'))
        np.testing.assert_array_equal(result[6, 10], self.expression[6, 10])


if __name__ == '__main__':
    unittest.main()
