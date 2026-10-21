"""Reloaded PSD, runtime endpoints, masks and unchanged legacy layers."""
from pathlib import Path
import itertools
import json
import sys
import unittest

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_psd import parse_psd,composite
from psd_groups_v14 import PixelLayer,LayerGroup,parse_psd_groups,composite_psd_groups
from build_expressions_v15 import (
    SOURCE,PSD,MODEL,V14,OUT,STATES,CROP,PARTS,PARAMETERS,make_support,
    alpha_over,local_masks,authored_defaults,
)


class ExpressionMotionV15(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original,cls.size=parse_psd(SOURCE)
        cls.tree,size=parse_psd_groups(PSD)
        assert size==cls.size
        cls.baseline=composite(cls.original)
        cls.groups=[g for g in cls.tree if isinstance(g,LayerGroup)]
        cls.manifest=json.loads((MODEL/'model.json').read_text())
        cls.expressions={e['id']:e for e in cls.manifest['expressions']}
        cls.scope=np.zeros(cls.baseline.shape[:2],bool)
        x0,y0,x1,y1=CROP
        cls.scope[y0:y1,x0:x1]=make_support()>0

    def test_original_66_layers_order_pixels_and_visibility(self):
        originals=[n for n in self.tree if isinstance(n,PixelLayer)]
        self.assertEqual(len(originals),66)
        for old,new in zip(self.original,originals):
            self.assertEqual(old['name'],new.name)
            self.assertEqual(old['visible'],new.visible)
            np.testing.assert_array_equal(old['data'],new.rgba,err_msg=new.name)

    def test_default_neutral_and_saved_merged_preview_exact(self):
        np.testing.assert_array_equal(composite_psd_groups(self.tree),self.baseline)
        with Image.open(PSD) as image:
            merged=np.asarray(image.convert('RGBA'))
        np.testing.assert_array_equal(merged,self.baseline)

    def test_all_legacy_toggle_combinations_exact(self):
        for bits in itertools.product((0,1),repeat=3):
            parts=[p for p,closed in zip(PARTS,bits) if closed]
            hide=[p+'.open' for p in parts];show=[p+'.closed' for p in parts]
            np.testing.assert_array_equal(
                composite_psd_groups(self.tree,hide=hide,show=show),
                composite(self.original,hide=hide,show=show),err_msg=str(bits))

    def test_legacy_runtime_base_and_sprites_unchanged(self):
        model=self.manifest
        actual=np.asarray(Image.open(MODEL/model['base']).convert('RGBA'))
        expected=composite(self.original,hide=[p+'.open' for p in PARTS])
        np.testing.assert_array_equal(actual,expected)
        for part in model['parts']:
            old=next(r['data'] for r in self.original if r['name']==part['name'])
            x0,y0,x1,y1=part['rect']
            sprite=np.asarray(Image.open(MODEL/part['file']).convert('RGBA'))
            np.testing.assert_array_equal(sprite,old[y0:y1,x0:x1])

    def test_safe_named_feature_layers_and_authored_visibility(self):
        self.assertEqual(len(self.groups),7)
        for group,(key,*_) in zip(self.groups,STATES[1:]):
            self.assertFalse(group.visible)
            self.assertEqual(len(group.children),7)
            layers={p.name:p for p in group.children}
            defaults=authored_defaults(key)
            for name in PARTS:
                for state in ('open','closed'):
                    layer=layers[f'{key}.{name}.{state}']
                    self.assertIsInstance(layer,PixelLayer)
                    self.assertEqual(layer.visible,int(state=='open')==defaults[PARAMETERS[name]])
            self.assertTrue(layers[f'{key}.face_plate.brows_cheeks'].visible)

    def test_all_runtime_endpoint_combinations_reload_exactly(self):
        x0,y0,x1,y1=CROP
        for key,*_ in STATES:
            e=self.expressions[key]
            base=np.asarray(Image.open(MODEL/e['base']).convert('RGBA'))
            parts={}
            for p in e['parts']:
                full=np.zeros_like(base);a,b,c,d=p['rect']
                full[b:d,a:c]=np.asarray(Image.open(MODEL/p['file']).convert('RGBA'))
                parts[p['name']]=full
            for bits in itertools.product((0,1),repeat=3):
                frame=base.copy();show=[];hide=[]
                states={name:'open' if value else 'closed' for name,value in zip(PARTS,bits)}
                for p in e['parts']:
                    name,state=p['name'].rsplit('.',1)
                    if states[name]==state:frame=alpha_over(frame,parts[p['name']])
                for name,value in zip(PARTS,bits):
                    state='open' if value else 'closed'
                    prefix=key+'.' if key!='neutral' else ''
                    show.append(prefix+name+'.'+state)
                    hide.append(prefix+name+'.'+('closed' if value else 'open'))
                if key!='neutral':show.append(e['folder'])
                check_tree=self.tree if key=='neutral' else [
                    next(g for g in self.groups if g.name==e['folder']),
                    PixelLayer('verified legacy base',self.baseline)]
                rendered=composite_psd_groups(check_tree,show=show,hide=hide)
                np.testing.assert_array_equal(frame,rendered,err_msg=f'{key}/{bits}')
                np.testing.assert_array_equal(frame[:,:,3],self.baseline[:,:,3])
                if key!='neutral':
                    np.testing.assert_array_equal(frame[~self.scope],self.baseline[~self.scope])
                preview=OUT/'previews'/f'{key}_L{bits[0]}_R{bits[1]}_M{bits[2]}_face.png'
                np.testing.assert_array_equal(frame[y0:y1,x0:x1],np.asarray(Image.open(preview)))
                if bits==tuple(e['authoredDefaults'][PARAMETERS[p]] for p in PARTS):
                    expected=np.asarray(Image.open(V14/'previews'/f'{key}_full.png').convert('RGBA'))
                    np.testing.assert_array_equal(frame,expected)

    def test_opaque_restoration_covers_painted_underlay(self):
        for key,*_ in STATES[1:]:
            for name,(alpha,erase) in local_masks(key).items():
                self.assertTrue(np.all(alpha[erase>0]==255),f'{key}/{name}')
                self.assertGreater(int((alpha==255).sum()),100)
                self.assertGreater(int(((alpha>0)&(alpha<255)).sum()),20)
        for group in self.groups:
            layers={p.name.rsplit('.',1)[0]+'.'+p.name.rsplit('.',1)[1]:p for p in group.children}
            prefix=group.children[0].name.split('.')[0]
            for name in PARTS:
                a=layers[f'{prefix}.{name}.closed'].rgba[:,:,3]
                b=layers[f'{prefix}.{name}.open'].rgba[:,:,3]
                np.testing.assert_array_equal(a,b)

    def test_runtime_schema_and_bounded_motion(self):
        self.assertEqual(list(self.expressions),[s[0] for s in STATES])
        for key,e in self.expressions.items():
            self.assertEqual(e['defaults']['ParamMouthOpenY'],0)
            self.assertEqual(e['eyeOpenMax'],0 if key=='big_smile' else 1)
            self.assertEqual(len(e['parts']),6)
            for p in e['parts']:
                a,b,c,d=p['motion']['bounds'];x,y=p['motion']['anchor']
                self.assertTrue(a<x<c and b<y<d)
                self.assertLessEqual(c-a,90)
                self.assertLessEqual(d-b,75)
                self.assertEqual(p['parameter'],PARAMETERS[p['name'].rsplit('.',1)[0]])
                self.assertTrue((MODEL/p['file']).is_file())

    def test_big_smile_keeps_closed_eye_design(self):
        e=self.expressions['big_smile']
        for name in PARTS[:2]:
            files={p['state']:MODEL/p['file'] for p in e['parts'] if p['name'].startswith(name+'.')}
            np.testing.assert_array_equal(np.asarray(Image.open(files['open'])),np.asarray(Image.open(files['closed'])))


if __name__=='__main__':unittest.main()
