"""Low-contrast skin regression: opaque gray is a defect even without black RGB."""
from pathlib import Path
import base64
import json
import subprocess
import unittest

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'runtime/model'
CROP=(493,326,615,397)


class MouthSkinTone(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=json.loads((MODEL/'model.json').read_text())
        cls.expression=next(e for e in cls.model['expressions'] if e['id']=='surprised')
        cls.parts={p['state']:p for p in cls.expression['parts'] if p['parameter']=='ParamMouthOpenY'}
        cls.base=Image.open(MODEL/cls.expression['base']).convert('RGBA')
        cls.mask=np.asarray(Image.open(ROOT/'assets/parts/v17/review/surprised_skin_mask.png'))>0
        assert cls.mask.sum()==2916, 'Do not change the frozen pre-fix pale-skin selection'
        cls.open=Image.open(MODEL/cls.parts['open']['file']).convert('RGBA')
        cls.closed=Image.open(MODEL/cls.parts['closed']['file']).convert('RGBA')

    def skin_delta(self,sprite,rect):
        image=self.base.copy();image.alpha_composite(sprite,tuple(rect[:2]))
        before=np.asarray(self.base.crop(CROP))[:,:,:3].astype(float)
        after=np.asarray(image.crop(CROP))[:,:,:3].astype(float)
        return ((after-before)@np.array([.2126,.7152,.0722]))[self.mask]

    def test_frozen_mask_detects_original_diffuse_gray_endpoint(self):
        old=Image.open(MODEL/'expressions/surprised/mouth_closed.png').convert('RGBA')
        delta=self.skin_delta(old,self.parts['closed']['rect'])
        self.assertLess(delta.mean(),-6)
        self.assertGreater((delta<-3).mean(),.8)

    def test_corrected_closed_skin_matches_surrounding_pale_gradient(self):
        delta=self.skin_delta(self.closed,self.parts['closed']['rect'])
        self.assertLess(abs(delta.mean()),1)
        self.assertLess((delta<-3).mean(),.05)

    def test_shared_runtime_helper_never_reintroduces_halo_during_closure(self):
        scales=[.06+i*.005 for i in range(17)]+[.15,.2,.25,.35,.65,1]
        payload={'part':self.parts['open'],'source':base64.b64encode(self.open.tobytes()).decode(),
                 'width':self.open.width,'height':self.open.height,'scales':scales,
                 'closed':{'pixels':base64.b64encode(self.closed.tobytes()).decode(),
                           'width':self.closed.width,'height':self.closed.height,'rect':self.parts['closed']['rect']}}
        code="""import fs from 'node:fs';
import {deformMouthPixels} from './runtime/web/expressions.js';
const p=JSON.parse(fs.readFileSync(0,'utf8'));
p.closed.pixels=Buffer.from(p.closed.pixels,'base64');
const source=Buffer.from(p.source,'base64');
console.log(JSON.stringify(p.scales.map(scale=>Buffer.from(deformMouthPixels(source,p.width,p.height,p.part,scale,'surprised',p.closed)).toString('base64'))));
"""
        output=subprocess.check_output(['node','--input-type=module','-e',code],cwd=ROOT,input=json.dumps(payload).encode())
        for scale,pixels in zip(scales,json.loads(output)):
            with self.subTest(scale=scale):
                image=Image.frombytes('RGBA',self.open.size,base64.b64decode(pixels))
                delta=self.skin_delta(image,self.parts['open']['rect'])
                self.assertLess(abs(delta.mean()),1)
                self.assertLess((delta<-3).mean(),.05)


if __name__=='__main__':unittest.main()
