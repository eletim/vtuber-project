#!/usr/bin/env python3
"""Generate Koma's layered PSD with ROI-aware skin/hair/clothing base reconstruction.

Requires the confirmed PNG. Structural art draft, NOT a rigged Cubism model.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import cv2, numpy as np
from PIL import Image
from time import perf_counter
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from koma_v6_support import (foreground_alpha,region_labels,region_polygon_mask,REGIONS,FACE_OUTLINE,FEATURES,polygon_mask,paint_rgba)
from psd_writer import write_psd
REGION_MAP={n:p for n,p in REGIONS}; REF_W,REF_H=1086,1448
HAIR_PARTS=['front_bangs','hair_side_left','hair_side_right','hair_crown','hair_back_left','hair_back_right','hair_accessory']
CLOTHING_PARTS=['blouse','vest_left','vest_right','skirt_and_belt','lower_body']
TOP_EXACT=['hair_accessory','front_bangs','hair_side_left','hair_side_right','left_eyebrow','right_eyebrow','hair_crown','hair_back_left','hair_back_right','neck','left_hand','right_hand','left_arm_sleeve','right_arm_sleeve','vest_left','vest_right','blouse','skirt_and_belt','lower_body']

def region_mask(name,w,h):
    return (region_polygon_mask((w,h), REGION_MAP[name]).astype(np.uint8)*255)

def union(*masks):
    x=np.zeros_like(masks[0],dtype=np.uint8)
    for m in masks: x=np.maximum(x,m)
    return x

def sample_mask(rgb,mask,rule):
    return (((mask>0)&rule(rgb)).astype(np.uint8)*255)

def reconstruct(rgb,target,sample,boost=None,sig=(18,52)):
    """Normalized multiscale fill in a local ROI, evaluated at quarter resolution."""
    h,w=target.shape
    ys,xs=np.nonzero(target)
    canvas=np.zeros((h,w,4),dtype=np.uint8)
    if not len(ys): return canvas
    pad=int(max(sig)*0.9)+8
    y0=max(0,int(ys.min())-pad); y1=min(h,int(ys.max())+pad+1)
    x0=max(0,int(xs.min())-pad); x1=min(w,int(xs.max())+pad+1)
    rgb_roi=rgb[y0:y1,x0:x1]; target_roi=target[y0:y1,x0:x1]
    sample_roi=sample[y0:y1,x0:x1]
    sample_bool=sample_roi>0
    if int(sample_bool.sum())<32: sample_bool=target_roi>0
    if not np.any(sample_bool): return canvas
    scale=4
    sw=max(2,(x1-x0+scale-1)//scale); sh=max(2,(y1-y0+scale-1)//scale)
    weight=cv2.resize(sample_bool.astype(np.float32),(sw,sh),interpolation=cv2.INTER_AREA)
    sig0,sig1=[max(0.6,v*w/REF_W/scale) for v in sig]
    denom0=cv2.GaussianBlur(weight,(0,0),sig0)
    denom1=cv2.GaussianBlur(weight,(0,0),sig1)
    src=cv2.resize(rgb_roi.astype(np.float32)*sample_bool[:,:,None],(sw,sh),interpolation=cv2.INTER_AREA)
    result=np.empty_like(src)
    for ch in range(3):
        near=cv2.GaussianBlur(src[:,:,ch],(0,0),sig0)/(denom0+1e-6)
        far=cv2.GaussianBlur(src[:,:,ch],(0,0),sig1)/(denom1+1e-6)
        result[:,:,ch]=0.72*near+0.28*far
    result=cv2.resize(result,(x1-x0,y1-y0),interpolation=cv2.INTER_LINEAR)
    result=np.rint(np.clip(result,0,255)).astype(np.uint8)
    if boost:
        for ch,v in enumerate(boost): result[:,:,ch]=np.maximum(result[:,:,ch],v)
    region=canvas[y0:y1,x0:x1]; region[:,:,:3]=result
    region[:,:,3]=np.where(target_roi>0,255,0)
    return canvas

def audit_mask_coverage(layers):
    targets=['front_bangs','hair_side_left','hair_side_right','hair_crown','hair_back_left','hair_back_right','hair_accessory','left_arm_sleeve','right_arm_sleeve','left_hand','right_hand','neck','blouse','vest_left','vest_right','skirt_and_belt','lower_body','left_eyebrow','right_eyebrow','eye_screen_left.open','eye_screen_right.open','mouth.open']
    idx={n:i for i,(n,_) in enumerate(layers)}
    result=[]; lower_acc=[None]*len(layers)
    acc=np.zeros(layers[0][1].shape[:2],dtype=bool)
    for i in range(len(layers)-1,-1,-1):
        lower_acc[i]=acc.copy()
        acc |= layers[i][1][:,:,3]>0
    for name in targets:
        i=idx[name]; mask=layers[i][1][:,:,3]>0
        total=mask.sum(); cov=((mask & lower_acc[i]).sum()/total) if total else 0.0
        result.append({'layer':name,'lower_coverage':round(float(cov),4),'pass':bool(cov>0.98)})
    return result

def build(source:Path,dest:Path):
    dest.mkdir(parents=True,exist_ok=True)
    started=perf_counter()
    rgb=np.asarray(Image.open(source).convert('RGB'),dtype=np.uint8); h,w=rgb.shape[:2]
    alpha=foreground_alpha(rgb); reference=np.dstack((rgb,alpha))
    labels,names=region_labels((w,h))
    region_rgba={}; region_alpha={}
    for idx,name in enumerate(names):
        a=np.where(labels==idx,alpha,0).astype(np.uint8)
        region_alpha[name]=a
        region_rgba[name]=np.dstack((rgb,a))
    expr={n:polygon_mask(w,h,p) for n,p in FEATURES.items()}
    expr_union=union(*expr.values())
    face=np.minimum(union(polygon_mask(w,h,FACE_OUTLINE),expr_union,
                          region_alpha['face_base'],region_alpha['left_eye'],region_alpha['right_eye'],
                          region_alpha['mouth']),alpha)
    excluded=cv2.dilate(expr_union,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(23,23)))
    rr,gg,bb=(rgb[:,:,i] for i in range(3))
    yy,xx=np.ogrid[:h,:w]
    face_sample=((face>0)&(excluded==0)&(rr>198)&(gg>147)&(bb>128)&
                 ((rr.astype(np.int16)-gg)>5)&((gg.astype(np.int16)-bb)>3)&
                 ((rr.astype(np.int16)-bb)>24)&
                 (xx>368*w/REF_W)&(xx<683*w/REF_W)&
                 (yy>195*h/1448)&(yy<419*h/1448))
    face_skin=reconstruct(rgb,face,face_sample.astype(np.uint8)*255,
                          boost=(222,176,162),sig=(22,68))
    open_expr={n:np.dstack((rgb,np.minimum(m,alpha))) for n,m in expr.items()}
    closed_expr=paint_rgba(w,h)
    eyebrow_union=union(region_alpha['left_eyebrow'],region_alpha['right_eyebrow'])
    face_details=np.dstack((rgb,np.where((face>0)&(expr_union==0)&(eyebrow_union==0),alpha,0).astype(np.uint8)))
    prep_time=perf_counter()
    hair_union=union(*[region_mask(n,w,h) for n in HAIR_PARTS])
    hair_base=reconstruct(rgb,np.minimum(hair_union,alpha),sample_mask(rgb,hair_union,lambda img:(img[:,:,0]>105)&(img[:,:,1]>70)&(img[:,:,2]>38)&(img[:,:,0]<220)),boost=(118,82,54),sig=(22,68))
    neck_mask=region_mask('neck',w,h)
    neck_base=reconstruct(rgb,np.minimum(neck_mask,alpha),sample_mask(rgb,neck_mask,lambda img:(img[:,:,0]>198)&(img[:,:,1]>148)&(img[:,:,2]>130)),boost=(220,172,158),sig=(10,28))
    torso_union=union(*[region_mask(n,w,h) for n in CLOTHING_PARTS])
    torso_base=reconstruct(rgb,np.minimum(torso_union,alpha),sample_mask(rgb,torso_union,lambda img:(img[:,:,0]>70)&(img[:,:,1]>55)&(img[:,:,2]>40)),sig=(26,72))
    lsm=region_mask('left_arm_sleeve',w,h); rsm=region_mask('right_arm_sleeve',w,h)
    lhm=region_mask('left_hand',w,h); rhm=region_mask('right_hand',w,h)
    sleeve_rule=lambda img:(img[:,:,0]>70)&(img[:,:,1]>55)&(img[:,:,2]>42)
    hand_rule=lambda img:(img[:,:,0]>198)&(img[:,:,1]>145)&(img[:,:,2]>126)
    left_sleeve_base=reconstruct(rgb,np.minimum(lsm,alpha),sample_mask(rgb,lsm,sleeve_rule),sig=(18,46))
    right_sleeve_base=reconstruct(rgb,np.minimum(rsm,alpha),sample_mask(rgb,rsm,sleeve_rule),sig=(18,46))
    left_hand_base=reconstruct(rgb,np.minimum(lhm,alpha),sample_mask(rgb,lhm,hand_rule),boost=(220,172,158),sig=(10,25))
    right_hand_base=reconstruct(rgb,np.minimum(rhm,alpha),sample_mask(rgb,rhm,hand_rule),boost=(220,172,158),sig=(10,25))
    base_time=perf_counter()
    controlled_union=union(hair_union,neck_mask,torso_union,lsm,rsm,lhm,rhm,face)
    misc_lower=[]; skip=set(TOP_EXACT)|{'face_base','mouth','left_eye','right_eye','left_iris','right_iris'}
    for idx,name in enumerate(names):
        if name in skip: continue
        a=np.where((labels==idx)&(controlled_union==0),alpha,0).astype(np.uint8)
        if np.any(a): misc_lower.append((name,np.dstack((rgb,a))))
    layers=[]
    for n in ('eye_screen_left','eye_screen_right','mouth'):
        layers.extend([(n+'.open',open_expr[n]),(n+'.closed',closed_expr[n])])
    layers.extend([
        ('hair_accessory',region_rgba['hair_accessory']),('front_bangs',region_rgba['front_bangs']),
        ('hair_side_left',region_rgba['hair_side_left']),('hair_side_right',region_rgba['hair_side_right']),
        ('left_eyebrow',region_rgba['left_eyebrow']),('right_eyebrow',region_rgba['right_eyebrow']),
        ('face_details_without_expression',face_details),('hair_crown',region_rgba['hair_crown']),
        ('hair_back_left',region_rgba['hair_back_left']),('hair_back_right',region_rgba['hair_back_right']),
        ('neck',region_rgba['neck']),('left_hand',region_rgba['left_hand']),('right_hand',region_rgba['right_hand']),
        ('left_arm_sleeve',region_rgba['left_arm_sleeve']),('right_arm_sleeve',region_rgba['right_arm_sleeve']),
        ('vest_left',region_rgba['vest_left']),('vest_right',region_rgba['vest_right']),('blouse',region_rgba['blouse']),
        ('skirt_and_belt',region_rgba['skirt_and_belt']),('lower_body',region_rgba['lower_body']),
        ('face_skin_FULL_beneath_eyes_mouth',face_skin),('hair_base_FULL_beneath_hair_parts',hair_base),
        ('neck_base_FULL_beneath_neck',neck_base),('left_hand_base_FULL_beneath_left_hand',left_hand_base),
        ('right_hand_base_FULL_beneath_right_hand',right_hand_base),
        ('left_sleeve_base_FULL_beneath_left_sleeve',left_sleeve_base),
        ('right_sleeve_base_FULL_beneath_right_sleeve',right_sleeve_base),
        ('torso_clothing_base_FULL_beneath_torso_parts',torso_base)
    ])
    layers+=list(reversed(misc_lower))
    open_composite=np.zeros_like(reference)
    for name,layer in reversed(layers):
        if name.endswith('.closed'): continue
        mask=layer[:,:,3]>0
        open_composite[mask]=layer[mask]
    original_mask=reference[:,:,3]>0
    diff=np.any(open_composite[original_mask]!=reference[original_mask],axis=1)
    pixel_errors=int(diff.sum())
    alpha_errors=int(np.count_nonzero(open_composite[:,:,3]!=reference[:,:,3]))
    audit=audit_mask_coverage(layers)
    report={'source':source.name,'audit_scope':'structural and initial rendering only; not rigging/art quality',
        'psd':'koma_structure_v6.psd','layer_count':len(layers),'audit':audit,
        'pass_all':bool(all(x['pass'] for x in audit) and pixel_errors==0 and alpha_errors==0),
        'open_pixel_errors':pixel_errors,'open_alpha_errors':alpha_errors,
        'artwork_ready_for_cubism':False,
        'base_layers':['face_skin_FULL_beneath_eyes_mouth','hair_base_FULL_beneath_hair_parts',
        'neck_base_FULL_beneath_neck','left_hand_base_FULL_beneath_left_hand',
        'right_hand_base_FULL_beneath_right_hand','left_sleeve_base_FULL_beneath_left_sleeve',
        'right_sleeve_base_FULL_beneath_right_sleeve','torso_clothing_base_FULL_beneath_torso_parts']}
    layout_time=perf_counter()
    assert report['pass_all'],'Layer structure or image pixel audit failed'
    psd=dest/'koma_structure_v6.psd'
    write_psd(psd,reference,layers,hidden_names=[name for name,_ in layers if name.endswith('.closed')])
    export_time=perf_counter()
    report['timings_seconds']={'prepare':round(prep_time-started,3),
        'base_generation':round(base_time-prep_time,3),
        'layout_audit':round(layout_time-base_time,3),
        'psd_export':round(export_time-layout_time,3),
        'total':round(export_time-started,3)}
    (dest/'build_info.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    Image.fromarray(open_composite).save(dest/'01_open_actual_layers.png')
    print(json.dumps({'pass_all':report['pass_all'],
        'open_pixel_errors':pixel_errors,'timings_seconds':report['timings_seconds']},ensure_ascii=False,indent=2))
    return psd

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('source',type=Path,nargs='?',default=ROOT/'assets/original/koma_confirmed.png')
    ap.add_argument('--output',type=Path,default=ROOT/'assets/parts/v6')
    args=ap.parse_args()
    build(args.source,args.output)
