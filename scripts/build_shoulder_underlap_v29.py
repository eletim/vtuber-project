from pathlib import Path
import json
import numpy as np
from PIL import Image
p=Path('runtime/model/model.json');m=json.loads(p.read_text(encoding='utf-8'));im=Image.open('assets/parts/v19/sources/shoulder_hidden_paint_v19.png').convert('RGBA');mapped=im.transform((1086,1448),Image.Transform.AFFINE,(1/.83,0,-8/.83,0,1/.86,-429/.86),resample=Image.Resampling.BICUBIC);rect=[330,478,405,520];a=np.array(mapped.crop(rect));rgb=a[:,:,:3].astype(int);valid=(rgb[:,:,0]>200)&(rgb[:,:,1]>130)&(rgb[:,:,2]>120)&(rgb[:,:,0]-rgb[:,:,1]>8);a[~valid]=0;file='body_v29/left_shoulder_underlap.png';Image.fromarray(a).save(Path('runtime/model')/file)
if not any(l['id']=='left_shoulder_underlap' for l in m['bodyLayers']):m['bodyLayers'].insert(next(i for i,l in enumerate(m['bodyLayers']) if l['id']=='left_shoulder_original_support'),{'id':'left_shoulder_underlap','role':'armLeft','file':file,'rect':rect,'articulation':{'joint':'upper','bind':'raised','variant':'raised'},'psdGroup':'v29 shoulder/retained painted underlap'})
p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
