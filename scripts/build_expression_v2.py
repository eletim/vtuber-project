#!/usr/bin/env python3
"""Refine only the closed-eye/closed-mouth PSD layers of the confirmed VTuber art.

Open states preserve the original illustration. The closed expressions use
hand-controlled SVG curves plus local skin reconstruction, not new AI renders.
This is expression artwork, not an exported Live2D Cubism rig.
"""
import argparse
import json
from io import BytesIO
from pathlib import Path
import cv2
import cairosvg
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from build_psd import extract_foreground, load_labels
from psd_writer import write_psd

ROOT = Path(__file__).resolve().parents[1]
SIZE = (1086, 1448)
FEATURES = {
 "eye_screen_left": [(372,287),(379,268),(406,248),(438,244),(473,247),(503,257),(518,279),(519,301),(500,325),(464,338),(422,338),(385,320),(371,305)],
 "eye_screen_right": [(553,263),(563,240),(582,224),(605,219),(630,222),(656,238),(668,260),(664,281),(650,298),(606,304),(574,290)],
 "mouth": [(482,354),(498,339),(533,334),(562,332),(586,339),(598,350),(595,373),(576,391),(543,396),(509,392),(487,379)]
}
ART = {
"eye_screen_left": '''<path d="M403 311 C426 305 468 304 490 312" fill="none" stroke="#bd7f77" stroke-width="1.2" opacity=".34"/>
<path d="M403 307 C425 302 465 303 486 309" fill="none" stroke="#ffe9dd" stroke-width="1.15" opacity=".68"/>
<path d="M387 302 C407 292 434 285 458 284 C480 284 494 292 503 298" fill="none" stroke="#593937" stroke-width="3.4" stroke-linecap="round" opacity=".95"/>
<path d="M389 300 Q382 300 377 293 Q386 295 397 296 Z" fill="#69413b" opacity=".96"/>
<path d="M398 296 Q391 292 389 285 Q397 291 405 293 Z" fill="#634039" opacity=".87"/>
<path d="M412 290 Q407 287 406 283 Q414 288 419 289 Z" fill="#78504a" opacity=".82"/>''',
"eye_screen_right": '''<path d="M571 291 C595 284 620 286 639 294" fill="none" stroke="#bd8077" stroke-width="1.2" opacity=".35"/>
<path d="M575 289 C594 286 619 289 636 294" fill="none" stroke="#ffeadc" stroke-width="1.1" opacity=".66"/>
<path d="M564 278 C580 265 598 258 617 259 C630 260 642 267 654 275" fill="none" stroke="#573735" stroke-width="3.4" stroke-linecap="round" opacity=".96"/>
<path d="M643 268 Q652 267 657 260 Q656 269 651 273 Z" fill="#573733" opacity=".9"/>
<path d="M632 262 Q640 260 643 255 Q644 262 639 267 Z" fill="#66413a" opacity=".85"/>
<path d="M621 258 Q626 255 630 249 Q631 257 628 262 Z" fill="#80554a" opacity=".82"/>''',
"mouth": '''<path d="M498 359 C506 367 522 373 542 369 C554 367 562 360 571 354 C568 360 557 368 543 372 C524 376 505 369 498 359 Z" fill="#a75e5b" opacity=".86"/>
<path d="M503 362 C523 373 548 371 567 356" fill="none" stroke="#98514f" stroke-width="1.35" opacity=".92"/>
<path d="M506 363 C523 371 545 370 561 361" fill="none" stroke="#d78e87" stroke-width="1.5" opacity=".45"/>
<path d="M516 381 Q535 386 549 379" fill="none" stroke="#f6c6ba" stroke-width="2.1" opacity=".58"/>
<path d="M520 384 Q534 388 545 383" fill="none" stroke="#fff2e9" stroke-width="1" opacity=".66"/>'''
}

def masks_of(w,h):
    out={}
    for name,polygon in FEATURES.items():
        arr=np.asarray(polygon,dtype=np.float32)*[w/SIZE[0],h/SIZE[1]]
        mask=np.zeros((h,w),dtype=np.uint8)
        cv2.fillPoly(mask,[np.rint(arr).astype(np.int32)],255)
        out[name]=mask
    return out

def repaired_skin(rgb,masks):
    h,w=rgb.shape[:2]
    yy,xx=np.ogrid[:h,:w]
    occupied=np.maximum.reduce(list(masks.values()))
    excl=cv2.dilate(occupied,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(19,19)))
    r,g,b=[rgb[:,:,i].astype(np.float32) for i in range(3)]
    skin=(r>198)&(g>152)&(b>135)&(r-g>6)&(g-b>3)&(r-b>21)
    face=(xx>350*w/SIZE[0])&(xx<689*w/SIZE[0])&(yy>218*h/SIZE[1])&(yy<420*h/SIZE[1])
    valid=(skin&face&(excl==0)).astype(np.float32)
    sigma=24*w/SIZE[0]
    d=gaussian_filter(valid,sigma)+1e-6
    field=np.stack([gaussian_filter(rgb[:,:,i].astype(np.float32)*valid,sigma)/d for i in range(3)],axis=-1)
    field[:,:,1]=np.clip(field[:,:,1]+5,0,255)
    field[:,:,2]=np.clip(field[:,:,2]+7,0,255)
    canvas=rgb.astype(np.float32).copy()
    for mask in masks.values():
        distance=cv2.distanceTransform(mask,cv2.DIST_L2,5)
        t=np.clip(distance/(12*w/SIZE[0]),0,1)
        t=t*t*(3-2*t)
        canvas=canvas*(1-t[:,:,None])+field*t[:,:,None]
    return np.rint(np.clip(canvas,0,255)).astype(np.uint8)

def artwork(w,h):
    result={}
    for name,parts in ART.items():
        svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1086 1448">'+parts+'</svg>'
        png=cairosvg.svg2png(bytestring=svg.encode(),output_width=w,output_height=h)
        result[name]=np.asarray(Image.open(BytesIO(png)).convert("RGBA"),dtype=np.uint8)
    return result

def over(canvas,layer):
    output=canvas.copy()
    a=layer[:,:,3:4].astype(np.float32)/255
    output[:,:,:3]=np.rint(canvas[:,:,:3].astype(np.float32)*(1-a)+layer[:,:,:3].astype(np.float32)*a).astype(np.uint8)
    output[:,:,3]=np.rint(canvas[:,:,3].astype(np.float32)+layer[:,:,3].astype(np.float32)*(1-canvas[:,:,3].astype(np.float32)/255)).astype(np.uint8)
    return output

def generate(source,output):
    rgb=np.asarray(Image.open(source).convert("RGB"),dtype=np.uint8)
    h,w=rgb.shape[:2];output.mkdir(parents=True,exist_ok=True)
    alpha=extract_foreground(rgb)
    original=np.dstack((rgb,alpha))
    masks=masks_of(w,h)
    base_rgb=repaired_skin(rgb,masks)
    base=np.dstack((base_rgb,alpha))
    drawings=artwork(w,h)
    opens={name:np.dstack((rgb,np.minimum(mask,alpha))) for name,mask in masks.items()}
    cfg=json.loads((ROOT/"config/koma_regions.json").read_text(encoding="utf-8"))
    labels,names=load_labels(w,h,cfg)
    body=[]
    for index,name in enumerate(names):
        a=np.where(labels==index,alpha,0).astype(np.uint8)
        if np.any(a): body.append((name,np.dstack((rgb,a))))
    layers=[]
    for name in FEATURES:
        layers.extend([(name+".open",opens[name]),(name+".closed",drawings[name])])
    occupied=np.maximum.reduce(list(masks.values()))
    layers.append(("facial_skin_reconstruction",np.dstack((base_rgb,np.minimum(occupied,alpha)))))
    layers+=list(reversed(body))
    psd=output/"koma_expression_refined.psd"
    write_psd(psd,original,layers,hidden_names=[name for name,_ in layers if name.endswith(".closed")])
    def expression(selected):
        image=base.copy()
        for name in FEATURES:
            image=over(image,drawings[name] if name in selected else opens[name])
        return image
    opened=expression(set())
    assert np.array_equal(opened[alpha==255],original[alpha==255]), "Initial expression changed"
    previews={"initial_open":set(),"closed_eyes":{"eye_screen_left","eye_screen_right"},
              "closed_mouth":{"mouth"},"closed_both":set(FEATURES)}
    for name,selected in previews.items():
        Image.fromarray(expression(selected)).save(output/(name+"_preview.png"))
    panel=Image.new("RGB",(1400,840),(255,248,245))
    for i,name in enumerate(previews):
        im=Image.open(output/(name+"_preview.png")).convert("RGBA")
        im=im.crop((340,210,690,420)).resize((700,420))
        tile=Image.new("RGBA",im.size,(255,248,245,255))
        tile.alpha_composite(im)
        panel.paste(tile.convert("RGB"),((i%2)*700,(i//2)*420))
    panel.save(output/"expression_comparison.png")
    report={"version":"v2-refined-closed-eyes-mouth","source":source.name,"resolution":[w,h],
            "layer_count":len(layers),"open_expression_matches_original":True,
            "changes":["closed left eye","closed right eye","closed mouth"],
            "limitations":["Skin in-fill and lash artwork are algorithmic drafts.",
                           "No Live2D meshes or deformers have been created."]}
    (output/"build_info.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("Created",psd,"with",len(layers),"layers")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("source",type=Path,nargs="?",default=ROOT/"assets/original/koma_confirmed.png")
    p.add_argument("--output",type=Path,default=ROOT/"assets/parts/v2")
    args=p.parse_args()
    generate(args.source,args.output)
