#!/usr/bin/env python3
"""Integrate retained sleeves and localized painted hair/clothing reveals."""
import copy
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import label,distance_transform_edt
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_psd import parse_psd,composite
from psd_writer import write_psd
from clean_sleeves_arms_hands_v8 import clean_layers
from review_v8_candidate import moved_composite,on_background

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/parts/v10'
SOURCE=ROOT/'assets/parts/v9/koma_expressions_v9.psd'


def painted_reveal(layers,names,paint,box,name,remove_background=False):
    baseline=composite(layers)
    selected=[r for r in layers if r['name'] in names]
    original_masks=[r['data'][:,:,3]>0 for r in selected]
    rgba=composite([{**r,'visible':True} for r in selected])
    mask=rgba[:,:,3]>0
    # Never bake an eye or mouth into a moving hair piece.
    for r in layers:
        if r['name'].endswith(('.open','.closed')):
            mask &= r['data'][:,:,3]==0
    x0,y0,x1,y1=box
    within=np.zeros_like(mask);within[y0:y1,x0:x1]=True;mask &= within
    source=np.asarray(Image.open(paint).convert('RGB').resize((x1-x0,y1-y0),Image.Resampling.LANCZOS))
    data=np.zeros_like(baseline);data[y0:y1,x0:x1,:3]=source
    data[:,:,3]=mask.astype('uint8')*255
    if remove_background:
        color=source[0,0].astype('int16')
        candidate=np.max(np.abs(source.astype('int16')-color),axis=2)<18
        labels,_=label(candidate)
        boundary=np.unique(np.concatenate([labels[0],labels[-1],labels[:,0],labels[:,-1]]))
        background=np.isin(labels,boundary[boundary!=0])
        background_full=np.zeros_like(mask);background_full[y0:y1,x0:x1]=background
        yy,_=np.indices(mask.shape)
        # Fixed antialiased copies outside the old part masks are also hair.
        # Reassign only areas where the authored reveal is exterior background.
        mask |= background_full&(baseline[:,:,3]>0)&(yy>180)&(yy<780)
        for r in layers:
            if r['name'].endswith(('.open','.closed')):
                mask &= r['data'][:,:,3]==0
        data[:,:,3]=mask.astype('uint8')*255
        data[background_full,3]=0
    # Edge pixels belong to the moving part too. Their old alpha must not leave
    # fixed brown antialias fragments behind. Keep translucent original edges
    # only where the reveal is transparent, avoiding double alpha in rest pose.
    mask &= (baseline[:,:,3]==255)|(data[:,:,3]==0)
    data[~mask]=0
    data[data[:,:,3]==0]=0
    for r in layers:
        if r['visible'] and r['name'] not in names:
            r['data'][mask]=0
    remaining=mask.copy()
    for r in selected:
        owned=remaining&(r['data'][:,:,3]>0)
        r['data'][mask]=0
        r['data'][owned]=baseline[owned]
        remaining &= ~owned
    if remaining.any():
        nearest=np.argmin(np.stack([distance_transform_edt(~a) for a in original_masks]),axis=0)
        for i,r in enumerate(selected):
            owned=remaining&(nearest==i)
            r['data'][owned]=baseline[owned]
    index=max(i for i,r in enumerate(layers) if r['name'] in names)+1
    layers.insert(index,{'name':name,'visible':True,'data':data})
    assert np.array_equal(composite(layers),baseline),name+' changed rest pose'
    return int(mask.sum())


def build():
    original,_=parse_psd(SOURCE)
    layers=clean_layers(original)
    repairs={}
    repairs['vest']=painted_reveal(layers,['vest_left','vest_right'],OUT/'vest_hidden_painted_source.png',
        (130,450,990,1400),'vest_continuous_painted_reveal_v10')
    repairs['hair']=painted_reveal(layers,['hair_side_left','hair_side_right','hair_back_left','hair_back_right'],
        OUT/'hair_hidden_painted_source.png',(0,0,1086,950),'hair_continuous_painted_reveal_v10',True)
    baseline=composite(original)
    assert np.array_equal(composite(layers),baseline)
    path=OUT/'koma_integrated_v10.psd'
    write_psd(path,baseline,[(r['name'],r['data']) for r in layers],
        hidden_names=[r['name'] for r in layers if not r['visible']],compression_level=9,merged_rle=True)
    reread,_=parse_psd(path)
    assert np.array_equal(composite(reread),baseline)
    scenes={'hair':('hair_side_left','hair_side_right','hair_back_left','hair_back_right'),
            'vest':('vest_left','vest_right'),
            'sleeves':('left_arm_sleeve','right_arm_sleeve','left_inner_cuff','right_inner_cuff'),
            'hands':('left_hand','right_hand')}
    for name,names in scenes.items():
        box=(50,0,1036,900) if name=='hair' else (90,430,1040,1448)
        frames=[('normal',baseline),('hidden',composite(reread,hide=names)),
                ('moved',moved_composite(reread,names,6,-3))]
        panel=Image.new('RGB',(990,390),'#eeeae6')
        for i,(state,frame) in enumerate(frames):
            image=on_background(frame).crop(box);image.thumbnail((330,360));panel.paste(image,(330*i,25))
            ImageDraw.Draw(panel).text((330*i+5,5),name+' '+state,fill='black')
        panel.save(OUT/f'{name}_review.png')
    Image.fromarray(baseline).save(OUT/'normal.png')
    (OUT/'integration.json').write_text(json.dumps({'layers':len(layers),'normal_rgba_changed_pixels':0,
        'painted_reveal_pixels':repairs,'visual_review':'PENDING','cubism_rigging':False},indent=2)+'\n')
    print('Integrated',len(layers),'layers:',path)


if __name__=='__main__':build()
