#!/usr/bin/env python3
"""Replace PSD v7's closed eyes and mouth with accepted, separately drawn art.

No new generation. Preserve all other 49 PSD layers and the exact initial face.
Source illustrations and the v7 PSD are distributed in the v8 artwork ZIP.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_psd import parse_psd, composite
from psd_writer import write_psd

SOURCE=ROOT/"assets/original/koma_confirmed.png"
V7=ROOT/"assets/parts/v7/koma_illustrated_underlayers_v7.psd"
EYES=ROOT/"assets/expression_references/eyes_closed_mouth_open.png"
MOUTH=ROOT/"assets/expression_references/eyes_open_mouth_closed.png"
DEST=ROOT/"assets/parts/v8"
CANDIDATE_PSD=DEST/"koma_expression_repaired_v8_candidate.psd"
AREAS={
  "eye_screen_left":(EYES,(365,238,525,345),12,10),
  "eye_screen_right":(EYES,(546,212,678,316),11,10),
  "mouth":(MOUTH,(476,329,601,408),8,8),
}

def sprite(original,altered,box,padding,feather):
    h,w=original.shape[:2]
    x0,y0,x1,y1=box
    x=np.arange(w)[None,:]
    y=np.arange(h)[:,None]
    dx=np.maximum(np.maximum(x0-padding-x,x-x1-padding),0)
    dy=np.maximum(np.maximum(y0-padding-y,y-y1-padding),0)
    outside=np.sqrt(dx.astype(np.float32)**2+dy.astype(np.float32)**2)
    opacity=np.clip(1-outside/max(feather,1),0,1)
    ring=(outside>=1)&(outside<=feather+8)
    bias=np.median((original.astype(np.int16)-altered.astype(np.int16))[ring],axis=0)
    bias=np.clip(bias,-12,12).astype(np.int16)
    painted=np.uint8(np.clip(altered.astype(np.int16)+bias,0,255))
    result=np.zeros((h,w,4),dtype=np.uint8)
    visible=opacity>0
    result[:,:,:3][visible]=painted[visible]
    result[:,:,3]=np.rint(opacity*255).astype(np.uint8)
    return result

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    layers,(w,h)=parse_psd(V7)
    original=np.asarray(Image.open(SOURCE).convert("RGB"),dtype=np.uint8)
    assert original.shape==(h,w,3)
    candidates={p:np.asarray(Image.open(p).convert("RGB"),dtype=np.uint8)
                for p in (EYES,MOUTH)}
    for part,(file,box,pad,feather) in AREAS.items():
        rec=next(r for r in layers if r["name"]==part+".closed")
        rec["data"]=sprite(original,candidates[file],box,pad,feather)
        rec["visible"]=False
    # Closed sprite is a cover layer over the approved open artwork.
    for part in AREAS:
        at=next(i for i,r in enumerate(layers) if r["name"]==part+".closed")
        closed=layers.pop(at)
        above=next(i for i,r in enumerate(layers) if r["name"]==part+".open")
        layers.insert(above,closed)
    # Mouth must cover the lower overlap of the broad eye skin patches.
    mouth_index=next(i for i,r in enumerate(layers) if r["name"]=="mouth.closed")
    layers.insert(0,layers.pop(mouth_index))
    flattened=composite(layers)
    baseline_alpha=np.asarray(Image.open(V7).convert("RGBA"))[:,:,3]
    assert np.array_equal(flattened[:,:,3],baseline_alpha)
    assert np.array_equal(flattened[:,:,:3][baseline_alpha>0],original[baseline_alpha>0])
    path=CANDIDATE_PSD
    write_psd(path,flattened,[(r["name"],r["data"]) for r in layers],
              hidden_names=[r["name"] for r in layers if not r["visible"]])
    check,_=parse_psd(path)
    assert len(check)==49
    states={
      "open":[],
      "eyes_closed":["eye_screen_left.closed","eye_screen_right.closed"],
      "mouth_closed":["mouth.closed"],
      "both_closed":["eye_screen_left.closed","eye_screen_right.closed","mouth.closed"],
    }
    audit={}
    images={}
    for label,show in states.items():
        expected=composite(layers,show=show)
        actual=composite(check,show=show)
        assert np.array_equal(actual,expected)
        affected=np.zeros((h,w),dtype=bool)
        for name in show:
            part=next(r for r in check if r["name"]==name)
            affected|=part["data"][:,:,3]>0
        different=np.any(flattened[:,:,:3]!=actual[:,:,:3],axis=2)
        outside=int(np.count_nonzero(different&~affected))
        holes=int(np.count_nonzero((flattened[:,:,3]>0)&(actual[:,:,3]==0)))
        assert not outside and not holes,(label,outside,holes)
        audit[label]={"outside_sprite_changes":outside,"lost_alpha_pixels":holes}
        full=Image.fromarray(actual,"RGBA")
        full.save(DEST/f"{label}.png")
        cropped=full.crop((305,130,730,480)).resize((680,560),Image.Resampling.LANCZOS)
        canvas=Image.new("RGBA",cropped.size,(250,246,242,255))
        canvas.alpha_composite(cropped)
        images[label]=canvas.convert("RGB")
    sequence=[("open",750),("eyes_closed",110),("open",460),
      ("mouth_closed",260),("open",160),("mouth_closed",230),
      ("open",200),("both_closed",190),("open",750)]
    combined=Image.new("RGB",(680*len(images),560),(250,246,242))
    for i,(name,frame) in enumerate(images.items()):combined.paste(frame,(680*i,0))
    palette=combined.quantize(colors=244,method=Image.Quantize.MEDIANCUT)
    frames=[images[name].quantize(palette=palette,dither=Image.Dither.NONE) for name,_ in sequence]
    frames[0].save(DEST/"koma_expression_v8.gif",save_all=True,append_images=frames[1:],
                   duration=[delay for _,delay in sequence],loop=0,optimize=True,disposal=2)
    (DEST/"audit_report.json").write_text(json.dumps({
       "layers":len(check),"initial_rgb_pixel_diff":0,"initial_alpha_pixel_diff":0,
       "states":audit,"art_ready_for_cubism":False},ensure_ascii=False,indent=2)+"\n")
    print("PASS:",path,len(check),"layers; four expression states")
if __name__=="__main__":main()
