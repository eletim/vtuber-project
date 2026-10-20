"""Verify retained artwork integration and expression endpoints independently."""
from pathlib import Path
import sys
import json
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_psd import parse_psd,composite


def main():
    new,size=parse_psd(ROOT/'assets/parts/v10/koma_integrated_v10.psd')
    old,_=parse_psd(ROOT/'assets/parts/v9/koma_expressions_v9.psd')
    assert len(new)==66 and size==(1086,1448)
    assert np.array_equal(composite(new),composite(old))
    assert np.array_equal(composite(new),np.asarray(Image.open(
        ROOT/'assets/parts/v10/koma_integrated_v10.psd').convert('RGBA')))
    for bits in range(8):
        selected=[p for i,p in enumerate(['eye_screen_left','eye_screen_right','mouth']) if bits&(1<<i)]
        hide=[p+'.open' for p in selected];show=[p+'.closed' for p in selected]
        assert np.array_equal(composite(new,hide=hide,show=show),composite(old,hide=hide,show=show))
    model=json.loads((ROOT/'runtime/model/model.json').read_text())
    base=np.asarray(Image.open(ROOT/'runtime/model'/model['base']).convert('RGBA'))
    assert np.array_equal(base,composite(new,hide=['eye_screen_left.open','eye_screen_right.open','mouth.open']))
    for p in model['parts']:
        original=next(r['data'] for r in new if r['name']==p['name'])
        x0,y0,x1,y1=p['rect']
        actual=np.asarray(Image.open(ROOT/'runtime/model'/p['file']).convert('RGBA'))
        assert np.array_equal(actual,original[y0:y1,x0:x1])
    print('PASS 66-layer PSD neutral/merged/eight expressions; runtime texture coordinates and pixels')


if __name__=='__main__':main()
