from pathlib import Path
import json
from PIL import Image
D = Path(__file__).resolve().parent
R = D / 'source/runtime/model'
model = json.loads((R / 'model.json').read_text())
count = 0
for expression in model['expressions']:
    for part in expression.get('parts', model['parts']):
        if part['parameter'] == 'ParamMouthOpenY':
            target = R / (part['file'] + '.rgba')
            target.write_bytes(Image.open(R / part['file']).convert('RGBA').tobytes())
            count += 1
print(f'Prepared {count} straight RGBA mouth fixtures in the snapshot only.')
