"""Keep the accepted v36 PSD intact and append exact v43 runtime material overlays."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
from psd_groups_v14 import PixelLayer,LayerGroup,parse_psd_groups,composite_psd_groups,write_psd_groups
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/parts/v43'
source=ROOT/'assets/parts/v36/koma_hand_angle_v36.psd'
tree,_=parse_psd_groups(source)
before=composite_psd_groups(tree)
layers=[]
for direction in ['left','right','up','down']:
 im=Image.new('RGBA',(1086,1448));patch=Image.open(OUT/'runtime-face-final-review/nose-materials'/f'{direction}.png').convert('RGBA');im.paste(patch,(515,281));layers.append(PixelLayer(direction+' nose overlay / registered highlight and tip',np.array(im),False))
added=LayerGroup('V43 ANGLE MATERIALS / runtime face-angle-rig.js applies shared mesh',layers,False)
result=[added]+tree
composite=composite_psd_groups(result)
assert np.array_equal(before,composite)
target=OUT/'koma_face_directions_v43.psd'
write_psd_groups(target,composite,result,compression_level=6,merged_rle=False)
check,_=parse_psd_groups(target)
assert np.array_equal(composite_psd_groups(check),before)
model_path=ROOT/'runtime/model/model.json'
model=json.loads(model_path.read_text(encoding='utf-8'));model['source_psd']='assets/parts/v43/koma_face_directions_v43.psd';model['expression_source_psd']=model['source_psd'];model_path.write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report={'source':str(source),'output':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,'original_composite_changed_pixels':0,'roundtrip_changed_values':int(np.count_nonzero(composite_psd_groups(check)!=before)),'expressions':len(model['expressions']),'new_layers':4,'overlay_rect':[515,281,590,346],'runtime_mapping':'runtime/web/face-angle-rig.js','limitation':'PSD stores source parts and registered nose overlays; animated geometry remains in runtime, not a flattened replacement head.'}
(OUT/'psd-runtime-v43.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
