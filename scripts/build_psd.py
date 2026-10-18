#!/usr/bin/env python3
"""AI-assisted first-pass part separation for the approved VTuber illustration.

Produces 26 named, editable PSD layers. Regions are approximate polygons and
are NOT yet ready to deform in Live2D Cubism. Concealed art is not reconstructed.
"""
import argparse
import csv
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from psd_writer import write_psd

ROOT = Path(__file__).resolve().parents[1]

def extract_foreground(rgb):
    """Find connected paper-colored background pixels from image borders."""
    h, w = rgb.shape[:2]
    edge = np.concatenate((rgb[:30].reshape(-1,3),rgb[:,:30].reshape(-1,3),rgb[:,-30:,:].reshape(-1,3)))
    sample = np.median(edge,axis=0).astype(np.uint8)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    bg = cv2.cvtColor(sample.reshape(1,1,3),cv2.COLOR_RGB2LAB)[0,0]
    candidate = (np.linalg.norm(lab.astype(np.float32)-bg.astype(np.float32),axis=2)<20).astype(np.uint8)
    _, labels = cv2.connectedComponents(candidate, connectivity=8)
    ids = np.unique(np.r_[labels[0],labels[-1],labels[:,0],labels[:,-1]])
    return np.where((candidate>0)&np.isin(labels,ids),0,255).astype(np.uint8)

def load_labels(w,h,config):
    ref_w, ref_h = config["reference_size"]
    entries = config["regions"]
    names = ["body_remaining"] + [r[0] for r in entries] + [iris[0] for iris in config["irises"]]
    labels = np.zeros((h,w),dtype=np.uint8)
    for index, (_,vertices) in enumerate(entries,1):
        pts = np.asarray(vertices,dtype=np.float32)
        pts[:,0] *= w/ref_w
        pts[:,1] *= h/ref_h
        cv2.fillPoly(labels,[np.rint(pts).astype(np.int32)],index)
    ys,xs = np.ogrid[:h,:w]
    for j,(_,center,radius) in enumerate(config["irises"]):
        x,y = center[0]*w/ref_w, center[1]*h/ref_h
        rx,ry = radius[0]*w/ref_w,radius[1]*h/ref_h
        labels[((xs-x)/rx)**2 + ((ys-y)/ry)**2 <= 1] = 1+len(entries)+j
    return labels,names

def build(source,output,config_file):
    rgb = np.asarray(Image.open(source).convert("RGB"),dtype=np.uint8)
    h,w = rgb.shape[:2]
    config=json.loads(config_file.read_text(encoding="utf-8"))
    labels,names=load_labels(w,h,config)
    alpha=extract_foreground(rgb)
    composite=np.dstack((rgb,alpha))
    output.mkdir(parents=True,exist_ok=True)
    Image.fromarray(composite).save(output/"flattened_transparent.png")
    layers=[]
    counts=[]
    for i,name in enumerate(names):
        layer_alpha=np.where(labels==i,alpha,0).astype(np.uint8)
        layers.append((name,np.dstack((rgb,layer_alpha))))
        counts.append([name,int(np.count_nonzero(layer_alpha))])
    assert np.array_equal(np.maximum.reduce([im[:,:,3] for _,im in layers]),alpha)
    psd=output/"koma_parts_draft.psd"
    write_psd(psd,composite,list(reversed(layers)))
    with (output/"part_manifest.csv").open("w",encoding="utf-8",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(["layer","opaque_pixels"])
        writer.writerows(counts)
    info={"source":source.name,"size":[w,h],"layer_count":len(names),
        "status":"draft; not Live2D-rig-ready",
        "next":["restore hidden face/hair/eyelids","clean cut boundaries","draw closed eyes and phoneme mouths","set Cubism meshes and deformers"]}
    (output/"build_info.json").write_text(json.dumps(info,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Saved {psd}: {len(names)} editable layers ({psd.stat().st_size} bytes)")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("source",type=Path,nargs="?",default=ROOT/"assets/original/koma_confirmed.png")
    p.add_argument("--config",type=Path,default=ROOT/"config/koma_regions.json")
    p.add_argument("--output",type=Path,default=ROOT/"assets/parts/v0")
    a=p.parse_args()
    build(a.source,a.output,a.config)
