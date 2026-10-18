#!/usr/bin/env python3
"""Create expression-ready PSD draft from the approved Koma design.

Run: python scripts/build_expression_psd.py assets/original/koma_confirmed.png
Output: assets/parts/v1/.  This is a sprite prototype, NOT a Cubism rig.
Requires the validated PSD writer already in this repository.
"""
import argparse
import json
from pathlib import Path
import sys
import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from build_psd import extract_foreground, load_labels
from psd_writer import write_psd

ROOT = Path(__file__).resolve().parents[1]
REF = (1086, 1448)
REGIONS = {
    "eye_screen_left": [(367,290),(379,268),(418,254),(459,247),(503,253),(525,276),(526,304),(501,323),(445,338),(391,330),(370,307)],
    "eye_screen_right": [(534,277),(543,254),(562,241),(592,238),(619,246),(632,265),(625,287),(605,302),(573,308),(542,296)],
    "mouth": [(472,352),(486,338),(519,335),(559,334),(584,347),(590,371),(577,390),(548,398),(504,395),(476,378)],
}
LINES = {
    "eye_screen_left": [(386,293),(413,282),(444,279),(471,281),(501,289)],
    "eye_screen_right": [(542,272),(558,263),(580,259),(601,261),(625,271)],
    "mouth": [(493,360),(515,369),(538,369),(562,356)]
}

def feature_masks(w, h):
    result = {}
    for key, poly in REGIONS.items():
        points = np.asarray(poly,np.float32)*[w/REF[0],h/REF[1]]
        mask = np.zeros((h,w),np.uint8)
        cv2.fillPoly(mask,[np.rint(points).astype(np.int32)],255)
        result[key] = mask
    return result

def reconstructed_skin(rgb, masks):
    """Estimate hidden skin from neighboring exposed skin; approximation only."""
    h,w = rgb.shape[:2]
    ys,xs = np.ogrid[:h,:w]
    face = (xs>335*w/1086)&(xs<712*w/1086)&(ys>218*h/1448)&(ys<405*h/1448)
    r,g,b = (rgb[:,:,c].astype(np.float32) for c in range(3))
    skin = (r>190)&(g>139)&(b>123)&(r-g>7)&(g-b>4)
    occupied = np.maximum.reduce(list(masks.values()))
    exclude = cv2.dilate(occupied,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(27,27)))
    valid = (skin&face&(exclude==0)).astype(np.float32)
    small = (max(1,w//4),max(1,h//4))
    weight = cv2.resize(valid,small,interpolation=cv2.INTER_AREA)
    sigma = 45*w/1086/4
    norm = gaussian_filter(weight,sigma=sigma)+1e-5
    channels = []
    for c in range(3):
        source = cv2.resize(rgb[:,:,c].astype(np.float32)*valid,small,interpolation=cv2.INTER_AREA)
        values = gaussian_filter(source,sigma=sigma)/norm
        channels.append(cv2.resize(values,(w,h),interpolation=cv2.INTER_LINEAR))
    return np.clip(np.stack(channels,axis=2),0,255).astype(np.uint8)

def closed_art(skin, name, w, h):
    pic = skin.copy()
    sx,sy = w/REF[0], h/REF[1]
    pts = np.rint(np.asarray(LINES[name],np.float32)*[sx,sy]).astype(np.int32)
    color = (155,83,82) if name=="mouth" else (89,47,44)
    cv2.polylines(pic,[pts],False,color,max(1,round((2 if name=="mouth" else 4)*sx)),cv2.LINE_AA)
    if name=="eye_screen_left":
        lashes=[[(389,293),(383,286)],[(394,290),(386,289)],[(401,285),(393,281)]]
    elif name=="eye_screen_right":
        lashes=[[(613,267),(622,255)],[(619,269),(630,262)],[(606,264),(614,255)]]
    else:
        lashes=[]
    for line in lashes:
        points=np.rint(np.asarray(line,np.float32)*[sx,sy]).astype(np.int32)
        cv2.polylines(pic,[points],False,(94,51,43),max(1,round(2*sx)),cv2.LINE_AA)
    return pic

def preview_composite(rgb, alpha, states, closed):
    canvas = np.dstack((rgb,alpha)).copy()
    for name,(opened,closed_layer) in states.items():
        layer = closed_layer if name in closed else opened
        weight = layer[:,:,3:4].astype(np.float32)/255.0
        canvas[:,:,:3] = np.rint(
            canvas[:,:,:3].astype(np.float32)*(1-weight) +
            layer[:,:,:3].astype(np.float32)*weight
        ).astype(np.uint8)
    return canvas

def generate(source, output, config):
    output.mkdir(parents=True,exist_ok=True)
    rgb = np.asarray(Image.open(source).convert("RGB"),np.uint8)
    h,w = rgb.shape[:2]
    alpha = extract_foreground(rgb)
    composite = np.dstack((rgb,alpha))
    conf = json.loads(config.read_text(encoding="utf-8"))
    labels,names = load_labels(w,h,conf)
    masks = feature_masks(w,h)
    occupied = np.maximum.reduce(list(masks.values()))
    skin = reconstructed_skin(rgb,masks)
    states={}
    top=[]
    for name,mask in masks.items():
        a=np.minimum(mask,alpha)
        opened=np.dstack((rgb,a))
        picture=closed_art(skin,name,w,h)
        dist=cv2.distanceTransform((a>0).astype(np.uint8),cv2.DIST_L2,3)
        closed_a=np.rint(a*np.clip(dist/8,0,1)).astype(np.uint8)
        closed=np.dstack((picture,closed_a))
        states[name]=(opened,closed)
        # Open sits ABOVE closed. Toggle off each *.open layer to see *.closed.
        top.extend([(name+".open",opened),(name+".closed",closed)])
    bottom=[]
    for i,name in enumerate(names):
        a=np.where((labels==i)&(occupied==0),alpha,0).astype(np.uint8)
        if np.any(a): bottom.append((name,np.dstack((rgb,a))))
    # Validate the visible-pixel partition before PSD export.
    reconstructed=np.zeros_like(composite)
    for _,layer in bottom:
        m=layer[:,:,3]>0
        reconstructed[m]=layer[m]
    for name,(opened,_) in states.items():
        m=opened[:,:,3]>0
        reconstructed[m]=opened[m]
    assert np.array_equal(reconstructed[:,:,3],alpha), "Missing visible pixels"
    assert np.array_equal(reconstructed[alpha>0],composite[alpha>0]), "Source image differs"
    layers=top+list(reversed(bottom))
    target=output/"koma_expression_draft.psd"
    write_psd(target,composite,layers)
    Image.fromarray(composite).save(output/"initial_open_preview.png")
    Image.fromarray(preview_composite(rgb,alpha,states,set(states))).save(output/"blink_closed_preview.png")
    timings=[470,110,130,110,500,200,300,210,370,220,320,200]
    poses=[set(),{"mouth"},set(states),{"eye_screen_left","eye_screen_right"},set(),{"mouth"},set(),{"mouth"},set(),{"mouth"},set(),{"mouth"}]
    frames=[]
    for pose in poses:
        composed=preview_composite(rgb,alpha,states,pose)
        crop=Image.fromarray(composed).crop((230,100,850,670)).resize((465,428))
        backdrop=Image.new("RGBA",crop.size,(252,249,246,255))
        backdrop.alpha_composite(crop)
        frames.append(backdrop.convert("RGB").quantize(colors=128))
    frames[0].save(output/"blink_talk_preview.gif",save_all=True,append_images=frames[1:],
                   duration=timings,loop=0,optimize=True)
    report={"status":"expression prototype, not Live2D rig", "layers":len(layers),
            "pixel_perfect_open_state":True,"resolution":[w,h],
            "features":list(REGIONS),"limitations":[
            "Closed expressions are approximate skin infills",
            "Part boundaries and obscured regions require cleanup",
            "No Cubism mesh/deformers or cmo3/model3.json"] }
    (output/"build_info.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Built {target} ({len(layers)} layers)")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("source",type=Path,nargs="?",default=ROOT/"assets/original/koma_confirmed.png")
    p.add_argument("--output",type=Path,default=ROOT/"assets/parts/v1")
    p.add_argument("--config",type=Path,default=ROOT/"config/koma_regions.json")
    args=p.parse_args()
    generate(args.source,args.output,args.config)
