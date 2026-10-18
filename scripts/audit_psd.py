#!/usr/bin/env python3
"""Independent layered PSD reader and render audit for 8-bit RGB/alpha PSD."""
from __future__ import annotations
import argparse, json, struct, zlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

def parse_psd(path):
    f=path.open('rb')
    def get(n):
        b=f.read(n)
        if len(b)!=n: raise ValueError('Truncated PSD')
        return b
    def ui16(): return struct.unpack('>H',get(2))[0]
    def si16(): return struct.unpack('>h',get(2))[0]
    def ui32(): return struct.unpack('>I',get(4))[0]
    if get(4)!=b'8BPS' or ui16()!=1: raise ValueError('Bad PSD header')
    get(6); channels=ui16();h=ui32();w=ui32();depth=ui16();mode=ui16()
    if (channels,depth,mode)!=(4,8,3): raise ValueError('Expected RGBA PSD')
    get(ui32());get(ui32())
    ui32()
    info_len=ui32();info_end=f.tell()+info_len
    count=abs(si16())
    records=[]
    for _ in range(count):
        y0,x0,y1,x1=struct.unpack('>iiii',get(16))
        chan=[(si16(),ui32()) for _ in range(ui16())]
        if get(4)!=b'8BIM': raise ValueError('Bad layer signature')
        get(4);flags=get(4)
        extra_size=ui32();extra_end=f.tell()+extra_size
        get(ui32());get(ui32());namelen=get(1)[0]
        name=get(namelen).decode('ascii','replace')
        f.seek(extra_end)
        records.append(dict(name=name,visible=not bool(flags[2]&2),
            bbox=(x0,y0,x1,y1),channels=chan))
    layers=[]
    for rec in records:
        x0,y0,x1,y1=rec['bbox'];hh=y1-y0;ww=x1-x0
        out=np.zeros((h,w,4),dtype=np.uint8)
        for channel,length in rec.pop('channels'):
            raw=get(length);cm=struct.unpack('>H',raw[:2])[0]
            if cm==2: data=zlib.decompress(raw[2:])
            elif cm==0: data=raw[2:]
            else: raise ValueError('Unsupported channel compression')
            if len(data)!=hh*ww: raise ValueError('Bad layer length')
            channel_index={0:0,1:1,2:2,-1:3}[channel]
            out[y0:y1,x0:x1,channel_index]=np.frombuffer(data,dtype=np.uint8).reshape(hh,ww)
        rec['data']=out
        layers.append(rec)
    f.seek(info_end);f.close()
    return layers,(w,h)

def composite(layers,hide=(),show=()):
    h,w=layers[0]['data'].shape[:2]
    dst=np.zeros((h,w,4),dtype=np.uint8)
    hide=set(hide);show=set(show)
    for rec in reversed(layers):
        name=rec['name']
        if name in hide or (not rec['visible'] and name not in show): continue
        src=rec['data']; a=src[:,:,3]
        mid=(a>0)&(a<255)
        if mid.any():
            av=(a[mid].astype(np.float32)/255)[:,None]
            dst[mid,:3]=np.rint(dst[mid,:3].astype(np.float32)*(1-av)+src[mid,:3].astype(np.float32)*av).astype(np.uint8)
            dst[mid,3]=np.rint(dst[mid,3]+a[mid]*(1-dst[mid,3]/255)).astype(np.uint8)
        mask=a==255;dst[mask]=src[mask]
    return dst

def audit(psd,original,out):
    out.mkdir(parents=True,exist_ok=True)
    layers,_=parse_psd(psd)
    reference=np.asarray(Image.open(original).convert('RGB'))
    expected_alpha=np.asarray(Image.open(psd).convert('RGBA'))[:,:,3]
    visible=composite(layers)
    rgb_errors=int(np.count_nonzero(np.any(visible[:,:,:3]!=reference,axis=2)&(expected_alpha>0)))
    alpha_errors=int(np.count_nonzero(visible[:,:,3]!=expected_alpha))
    scenes={
        '00_default':[],
        '01_face_features_hidden':['eye_screen_left.open','eye_screen_right.open','mouth.open'],
        '02_bangs_hidden':['front_bangs'],
        '03_accessory_hidden':['hair_accessory'],
        '04_vest_hidden':['vest_left','vest_right'],
        '05_sleeves_hidden':['left_arm_sleeve','right_arm_sleeve'],
        '06_hands_hidden':['left_hand','right_hand'],
        '07_neck_hidden':['neck'],
        '08_side_hair_hidden':['hair_side_left','hair_side_right']
    }
    scene_checks={}
    panel=Image.new('RGB',(750,1230),(255,249,245))
    draw=ImageDraw.Draw(panel)
    for i,(name,hidden) in enumerate(scenes.items()):
        rendered=composite(layers,hide=hidden)
        holes=int(np.count_nonzero((rendered[:,:,3]==0)&(expected_alpha>0)))
        scene_checks[name]={'holes':holes,'pass':holes==0}
        if not i: Image.fromarray(rendered).save(out/'00_default.png')
        tile=Image.fromarray(rendered).crop((130,60,1010,1300)).resize((250,350))
        white=Image.new('RGBA',tile.size,(255,249,245,255))
        white.alpha_composite(tile)
        x=(i%3)*250;y=(i//3)*410
        panel.paste(white.convert('RGB'),(x,y+25))
        draw.text((x+5,y+6),name.replace('_',' ')[:30],fill=(50,40,40))
    panel.save(out/'layer_hide_audit.jpg',quality=90)
    report={
        'source_psd':psd.name,'layer_count':len(layers),
        'pixel_errors_vs_original':rgb_errors,'alpha_errors':alpha_errors,
        'closed_layers_hidden_by_default':all(not r['visible'] for r in layers if r['name'].endswith('.closed')),
        'scene_checks':scene_checks,
        'pass_structural':rgb_errors==0 and alpha_errors==0 and all(x['pass'] for x in scene_checks.values()),
        'artwork_review':'INCOMPLETE: underlays are approximate; not a Cubism-ready model'
    }
    (out/'audit_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if not report['pass_structural']: raise SystemExit(1)
    return report

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('psd',type=Path)
    ap.add_argument('--original',type=Path,default=Path(__file__).resolve().parents[1]/'assets/original/koma_confirmed.png')
    ap.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]/'assets/parts/v6/audit')
    a=ap.parse_args()
    audit(a.psd,a.original,a.out)
