"""Production v14 preservation, folder switching and matched exports."""
from pathlib import Path
import itertools
import sys
import unittest
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_psd import parse_psd,composite
from psd_groups_v14 import PixelLayer,LayerGroup,parse_psd_groups,composite_psd_groups
from build_expressions_v14 import STATES,CROP,OUT,SOURCE,make_support

class ExpressionCollection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old,cls.size=parse_psd(SOURCE)
        cls.tree,size=parse_psd_groups(OUT/'koma_expression_collection_v14.psd')
        assert size==cls.size
        cls.base=composite(cls.old)
        cls.groups=[n for n in cls.tree if isinstance(n,LayerGroup)]
        cls.originals=[n for n in cls.tree if isinstance(n,PixelLayer)]
    def test_original_layers_exact_and_same_order(self):
        self.assertEqual(len(self.originals),66)
        for a,b in zip(self.old,self.originals):
            self.assertEqual(a['name'],b.name)
            self.assertEqual(a['visible'],b.visible)
            self.assertTrue(np.array_equal(a['data'],b.rgba),b.name)
    def test_neutral_exact_and_merged_exact(self):
        self.assertTrue(np.array_equal(self.base,composite_psd_groups(self.tree)))
        self.assertTrue(np.array_equal(self.base,np.asarray(Image.open(OUT/'koma_expression_collection_v14.psd').convert('RGBA'))))
    def test_all_expression_exports_and_support(self):
        self.assertEqual(len(self.groups),7)
        x0,y0,x1,y1=CROP
        support=np.zeros(self.base.shape[:2],bool);support[y0:y1,x0:x1]=make_support()>0
        for idx,(key,*_) in enumerate(STATES):
            show=[] if idx==0 else [self.groups[idx-1].name]
            f=composite_psd_groups(self.tree,show=show)
            self.assertTrue(np.array_equal(f,np.asarray(Image.open(OUT/'previews'/f'{key}_full.png').convert('RGBA'))),key)
            self.assertTrue(np.array_equal(f[y0:y1,x0:x1],np.asarray(Image.open(OUT/'previews'/f'{key}_face.png').convert('RGBA'))),key)
            self.assertTrue(np.array_equal(f[:,:,3],self.base[:,:,3]),key)
            self.assertTrue(np.array_equal(f[~support],self.base[~support]),key)
            if idx:self.assertGreater(np.count_nonzero(np.any(f!=self.base,axis=2)),10000)
    def test_all_legacy_blink_combinations(self):
        for bits in itertools.product([False,True],repeat=3):
            parts=[p for p,closed in zip(['eye_screen_left','eye_screen_right','mouth'],bits) if closed]
            hide=[p+'.open' for p in parts];show=[p+'.closed' for p in parts]
            self.assertTrue(np.array_equal(composite(self.old,hide=hide,show=show),composite_psd_groups(self.tree,hide=hide,show=show)),str(bits))
    def test_each_folder_is_coordinated_and_hidden(self):
        for group in self.groups:
            self.assertFalse(group.visible)
            self.assertEqual(len(group.children),1)
            self.assertTrue(group.children[0].visible)
            self.assertIsInstance(group.children[0],PixelLayer)
    def test_opaque_feature_coverage_never_ghosts(self):
        # If a user disregards the one-folder-only guide, the top expression still
        # wholly covers lower ones on the opaque facial support. Selector prevents it.
        x0,y0,x1,y1=CROP
        opaque=make_support()==255
        for a,b in itertools.combinations(self.groups,2):
            one=composite_psd_groups(self.tree,show=[a.name])[y0:y1,x0:x1]
            both=composite_psd_groups(self.tree,show=[a.name,b.name])[y0:y1,x0:x1]
            self.assertTrue(np.array_equal(one[opaque],both[opaque]))

if __name__=='__main__':unittest.main()
