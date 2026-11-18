from pathlib import Path
import json,hashlib,numpy as np
from PIL import Image
from psd_groups_v14 import PixelLayer,LayerGroup,parse_psd_groups,composite_psd_groups,write_psd_groups
root=Path(__file__).resolve().parents[1];model=json.loads((root/'runtime/model/model.json').read_text(encoding='utf-8'))
tree,_=parse_psd_groups(root/'assets/parts/v46/koma_separated_eyes_v46.psd');before=composite_psd_groups(tree);groups=[]
for definition in model['eyeComponents']:
 folder=root/'runtime/model'/definition['directory'];meta=json.loads((folder/definition['profile']).read_text());layers=[]
 for source in sorted(folder.glob('*.png')):
  image=Image.new('RGBA',tuple(model['size']));image.paste(Image.open(source).convert('RGBA'),tuple(meta['rect'][:2]));layers.append(PixelLayer(source.stem,np.array(image),False))
 groups.append(LayerGroup(definition['name']+' / native source + registered hidden supplements',layers,False))
for expression in model['expressions']:
 layers=[]
 for part in expression['parts']:
  if not part['name'].startswith('eye_'):continue
  image=Image.new('RGBA',tuple(model['size']));image.paste(Image.open(root/'runtime/model'/part['file']).convert('RGBA'),tuple(part['rect'][:2]));layers.append(PixelLayer(part['name'],np.array(image),False))
 groups.append(LayerGroup(expression['id']+' / authored open-closed endpoints in model coordinates',layers,False))
tree.insert(0,LayerGroup('V47 registered eye source endpoints / procedural aperture',groups,False))
merged=composite_psd_groups(tree);assert np.array_equal(merged,before)
target=root/'assets/parts/v47/koma_aligned_eyes_v47.psd';write_psd_groups(target,merged,tree,compression_level=6,merged_rle=False)
check,_=parse_psd_groups(target);assert np.array_equal(merged,composite_psd_groups(check))
model['source_psd']='assets/parts/v47/koma_aligned_eyes_v47.psd';(root/'runtime/model/model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report=dict(path=str(target),bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),original_merged_difference=0,roundtrip_difference=0,source_groups=10,procedural_runtime='eye-components.js: registered opaque endpoints, premultiplied lid correspondence, unscaled iris')
(root/'assets/parts/v47/psd-integrated.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
manifest=json.loads((root/'assets/parts/v36/psd-runtime-v36.json').read_text())
manifest.update(psd=model['source_psd'],sha256=report['sha256'],roundtrip_changed_values=0,eye_source_groups=[d['name'] for d in model['eyeComponents']])
(root/'assets/parts/v47/psd-runtime-v47.json').write_text(json.dumps(manifest,indent=2)+'\n')
