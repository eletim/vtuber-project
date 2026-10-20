#!/usr/bin/env python3
"""Export the integrated PSD's painted skin and expression controls for playback."""
from pathlib import Path
import json
import sys
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_psd import parse_psd,composite
ROOT=Path(__file__).resolve().parents[1]


def main():
    source=ROOT/'assets/parts/v10/koma_integrated_v10.psd'
    layers,size=parse_psd(source)
    out=ROOT/'runtime/model';out.mkdir(parents=True,exist_ok=True)
    names={'eye_screen_left':'ParamEyeROpen','eye_screen_right':'ParamEyeLOpen','mouth':'ParamMouthOpenY'}
    Image.fromarray(composite(layers,hide=[p+'.open' for p in names])).save(out/'base.png')
    parts=[]
    for p,param in names.items():
        # Draw closed before open. Endpoints reproduce PSD visibility toggles.
        for state in ['closed','open']:
            data=next(r['data'] for r in layers if r['name']==p+'.'+state)
            ys,xs=np.nonzero(data[:,:,3]);rect=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
            filename=p+'_'+state+'.png'
            Image.fromarray(data).crop(rect).save(out/filename)
            parts.append({'name':p+'.'+state,'parameter':param,'state':state,'rect':rect,'file':filename})
    manifest={'name':'羽月こま','format':'koma-part-mesh-1','size':list(size),'base':'base.png',
              'source_psd':str(source.relative_to(ROOT)),'parts':parts,'mesh':[30,40],
              'note':'PSD-derived preview mesh, not a Cubism moc3 export.'}
    (out/'model.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(out)


if __name__=='__main__':main()
