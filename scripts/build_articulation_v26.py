from pathlib import Path
import json,subprocess,copy
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];MODEL=ROOT/'runtime/model';OUT=ROOT/'assets/parts/v26';OUT.mkdir(exist_ok=True);DEST=MODEL/'body_v26';DEST.mkdir(exist_ok=True)
model=json.loads(subprocess.check_output(['git','show','9d15e2f98e2c468d8a2cc7a84d243f80fcaffb67:runtime/model/model.json'],cwd=ROOT))
new=[];report=[]
for layer in model['bodyLayers']:
 if layer['id'] not in ['legs_static','torso_clothing']:new.append(layer);continue
 im=np.array(Image.open(MODEL/layer['file']).convert('RGBA'));x0,y0,x1,y1=layer['rect'];yy,xx=np.mgrid[y0:y1,x0:x1]
 specs=[('thigh_left','legLeft',xx<540),('thigh_right','legRight',xx>=540)] if layer['id']=='legs_static' else [('chest_clothing','chest',yy<820),('abdomen_clothing','abdomen',(yy>=820)&(yy<980)),('pelvis_clothing','pelvis',yy>=980)]
 assembled=np.zeros_like(im)
 for name,role,mask in specs:
  art=im.copy();art[~mask]=0;assembled[mask]=art[mask]
  # Full source rectangle supplies a transparent guard band around each cut.
  Image.fromarray(art).save(DEST/(name+'.png'))
  part=copy.deepcopy(layer);part.update(id=name,role=role,file='body_v26/'+name+'.png',psdGroup='v26 articulated body/'+name);new.append(part)
 assert np.array_equal(assembled,im)
 report.append({'source':layer['file'],'parts':[s[0] for s in specs],'recombined_changed_values':0})
model['bodyLayers']=new
model['bodyRig']['segmentOwnership']={'chest':[450,820],'abdomen':[820,980],'pelvis':[980,1178],'hips':[[400,1225],[650,1225]],'note':'Exact source partitions; common attachment strip at torso joins and inner thigh split. No knee artwork exists.'}
(MODEL/'model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(OUT/'partition-audit.json').write_text(json.dumps(report,indent=2)+'\n')
