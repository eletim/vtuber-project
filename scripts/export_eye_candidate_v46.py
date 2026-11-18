from pathlib import Path
import json,hashlib,numpy as np
from PIL import Image
from psd_groups_v14 import PixelLayer,LayerGroup,parse_psd_groups,composite_psd_groups,write_psd_groups
root=Path(__file__).resolve().parents[1];out=root/'assets/parts/v46'
model=json.loads((root/'runtime/model/model.json').read_text(encoding='utf-8'))
tree,_=parse_psd_groups(root/model['source_psd']);layers=[]
for source in sorted((root/'runtime/model/eyes_v46').glob('*.png')):
 image=Image.new('RGBA',tuple(model['size']));image.paste(Image.open(source).convert('RGBA'),(356,229));layers.append(PixelLayer(source.stem,np.array(image),False))
tree.insert(0,LayerGroup('V46 LEFT EYE CANDIDATE 3 / hidden / not production approved',layers,False))
merged=composite_psd_groups(tree);target=out/'koma_eye_components_v46_candidate3.psd'
write_psd_groups(target,merged,tree,compression_level=6,merged_rle=False)
check,_=parse_psd_groups(target);assert np.array_equal(merged,composite_psd_groups(check))
report={'path':str(target),'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'roundtrip_changed_values':0,'active_runtime_unchanged':True}
(out/'psd-candidate3.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
