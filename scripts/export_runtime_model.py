#!/usr/bin/env python3
"""Export the integrated PSD's painted skin and expression controls for playback."""
from pathlib import Path
import json
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter,map_coordinates,binary_dilation
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
    mesh=(60,80)
    yy,xx=np.meshgrid(np.linspace(0,size[1]-1,mesh[1]+1),
                      np.linspace(0,size[0]-1,mesh[0]+1),indexing='ij')
    groups=[tuple(f'{side}_{part}' for part in ('hand','arm_sleeve','arm_wrist_join','inner_cuff'))
            for side in ('left','right')]
    groups.append(('hair_side_left','hair_side_right','hair_back_left','hair_back_right'))
    weights=[]
    for group in groups:
        mask=np.maximum.reduce([r['data'][:,:,3] for r in layers if r['name'] in group])/255.
        field=gaussian_filter(mask,14)
        weights.append(map_coordinates(field,[yy.ravel(),xx.ravel()],order=1,mode='nearest'))
    arm_mask=np.maximum.reduce([r['data'][:,:,3] for r in layers if r['name'] in groups[0]+groups[1]])>0
    attachment=gaussian_filter(binary_dilation(arm_mask,iterations=40).astype(float),26)
    weights.append(map_coordinates(attachment,[yy.ravel(),xx.ravel()],order=1,mode='nearest'))
    (out/'skinning.json').write_text(json.dumps({'mesh':list(mesh),
        'channels':['left_arm','right_arm','long_hair','arm_parent'],
        'weights':np.round(np.stack(weights,axis=1),4).tolist()},separators=(',',':'))+'\n')
    manifest={'name':'羽月こま','format':'koma-part-mesh-2','size':list(size),'base':'base.png',
              'source_psd':str(source.relative_to(ROOT)),'parts':parts,'mesh':list(mesh),
              'skinning':'skinning.json',
              'note':'PSD-derived preview mesh, not a Cubism moc3 export.'}
    (out/'model.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(out)


if __name__=='__main__':main()
