"""Register an authored angle image to the existing wrist; no repainting."""
from pathlib import Path
import json, shutil, hashlib, math
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'assets/parts/v35'; out.mkdir(parents=True,exist_ok=True)
dst=ROOT/'runtime/model/body_v35'; dst.mkdir(parents=True,exist_ok=True)
source=ROOT.parent/'library-v35-import/hand-side-original.png'
shutil.copyfile(source,out/'hand-side-library-original.png')
im=Image.open(source).convert('RGBA')
# Similarity registration: authored wrist centre and middle fingertip.
p=np.array([600.,850.]); q=np.array([1155.,135.])
a=np.array([27.,127.]); b=np.array([156.,22.])
v=q-p; w=b-a; c=np.dot(v,w)/np.dot(v,v); s=(v[0]*w[1]-v[1]*w[0])/np.dot(v,v)
M=np.array([[c,-s],[s,c]]); inv=np.linalg.inv(M); offset=p-inv@a
registered=im.transform((163*4,155*4),Image.Transform.AFFINE,(*(inv[0]/4),offset[0],*(inv[1]/4),offset[1]),Image.Resampling.BICUBIC).resize((163,155),Image.Resampling.LANCZOS)
registered.save(dst/'left_raised_hand_side.png')
meta={'library_file_id':'libfile_f54582935e3881918c471077b21eec9c','file_id':'file_00000000ac8c822fbf6849c43916a215','version':0,'original_bytes':source.stat().st_size,'original_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'metadata_original':'/home/koji/koma-v35-library-import/exec-402d1d9f-09fe-4fa9-a65f-a33bc599640c.png','registration':{'source_wrist':p.tolist(),'source_middle_tip':q.tolist(),'target_wrist':a.tolist(),'target_middle_tip':b.tolist(),'matrix':M.tolist()},'original_preserved':True}
(out/'hand-source.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
print(json.dumps(meta))
