#!/usr/bin/env python3
"""PSD writer smoke test using synthetic art (no source image required)."""
from pathlib import Path
import tempfile
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from psd_writer import write_psd
from audit_psd import parse_psd, composite

def main():
    h,w=100,110
    base=np.zeros((h,w,4),dtype=np.uint8)
    base[5:95,5:105]=[234,193,171,255]
    eye=np.zeros_like(base)
    eye[28:42,27:64]=[40,22,37,255]
    closed=np.zeros_like(base)
    closed[34:37,24:67]=[90,40,43,255]
    merged=base.copy()
    merged[eye[:,:,3]>0]=eye[eye[:,:,3]>0]
    layers=[('eye.open',eye),('eye.closed',closed),('skin.base',base)]
    with tempfile.TemporaryDirectory() as d:
        path=Path(d)/'example.psd'
        write_psd(path,merged,layers,hidden_names=['eye.closed'])
        parsed,(rw,rh)=parse_psd(path)
        assert (rw,rh)==(w,h)
        assert len(parsed)==3
        assert [(r['name'],r['visible']) for r in parsed]==[
            ('eye.open',True),('eye.closed',False),('skin.base',True)]
        assert np.array_equal(composite(parsed),merged)
        hidden=composite(parsed,hide=['eye.open'])
        assert np.array_equal(hidden[34,40],base[34,40])
        shown=composite(parsed,hide=['eye.open'],show=['eye.closed'])
        assert np.array_equal(shown[35,40],closed[35,40])
        print('PASS: layers, visibility, composite and expression fallback')

if __name__=='__main__':
    main()
