"""Save editable v22 bind-pose groups and eight expression states; keep v19 native backup."""
from pathlib import Path
import copy,json,hashlib
import numpy as np
from PIL import Image
from psd_groups_v14 import PixelLayer,LayerGroup,parse_psd_groups,composite_psd_groups,write_psd_groups
ROOT=Path(__file__).resolve().parents[1];MODEL=ROOT/'runtime/model';OUT=ROOT/'assets/parts/v22'
model=json.loads((MODEL/'model.json').read_text(encoding='utf-8'));size=tuple(model['size'])
def full(file,rect):
 im=Image.new('RGBA',size);im.paste(Image.open(MODEL/file).convert('RGBA'),tuple(rect[:2]));a=np.array(im);a[a[:,:,3]==0]=0;return a
face=next(l for l in model['bodyLayers'] if l.get('features'))
ownership=full(face['movingHairMask'],face['rect'])[:,:,3]>0
def feature_group(expression):
 layers=[]
 defaults={'ParamEyeLOpen':1,'ParamEyeROpen':1,'ParamMouthOpenY':0,**expression.get('defaults',{})}
 for part in expression['parts']:
  pixels=full(part['file'],part['rect']);pixels[ownership]=0
  state='open' if defaults.get(part['parameter'],0)>.5 else 'closed'
  layers.append(PixelLayer(expression['id']+'/'+part['name'],pixels,part['state']==state))
 layers.append(PixelLayer(expression['id']+'/fixed face without moving hair',full(face['expressionFiles'][expression['id']],face['rect'])))
 return layers
neutral=next(e for e in model['expressions'] if e['id']=='neutral')
visible=[]
for layer in reversed(model['bodyLayers']):
 if layer.get('features'):visible.append(LayerGroup(layer['psdGroup'],feature_group(neutral)))
 else:visible.append(LayerGroup(layer['psdGroup'],[PixelLayer(layer['id'],full(layer['file'],layer['rect']))]))
expressions=[LayerGroup('EXPRESSION '+e['id'],feature_group(e),False) for e in model['expressions'] if e['id']!='neutral']
original,_=parse_psd_groups(ROOT/'assets/parts/v19/koma_separated_body_v19.psd')
tree=expressions+visible+[LayerGroup('ORIGINAL v19 / native backup DO NOT DELETE',copy.deepcopy(original),False)]
composite=composite_psd_groups(tree);target=OUT/'koma_articulated_v22.psd'
write_psd_groups(target,composite,tree,compression_level=6,merged_rle=False)
check,_=parse_psd_groups(target);assert np.array_equal(composite_psd_groups(check),composite)
Image.fromarray(composite).save(OUT/'psd-bind-pose.png')
model['source_psd']='assets/parts/v22/koma_articulated_v22.psd'
model['expression_source_psd']='assets/parts/v22/koma_articulated_v22.psd'
(MODEL/'model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report={'psd':model['source_psd'],'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'saved_default':'raised hand bind pose; runtime starts with lowered articulated pose','native_v19_backup':True,'roundtrip_changed_values':0,'expressions':len(expressions)+1,'runtime_groups':len(model['bodyLayers']),'articulated_groups':[l['id'] for l in model['bodyLayers'] if l.get('articulation')],'hair_groups':[l['id'] for l in model['bodyLayers'] if l.get('hairMotion')]}
(OUT/'psd-runtime-v22.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
