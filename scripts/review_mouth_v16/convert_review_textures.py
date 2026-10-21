from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont
D = Path(__file__).resolve().parent
R = D / 'source/runtime/model'
output = D.parent / 'generated'
output.mkdir(exist_ok=True)
for metadata in (R / 'review_textures').glob('*.png.json'):
    size = json.loads(metadata.read_text())
    Image.frombytes('RGBA', (size['width'], size['height']), metadata.with_suffix('.rgba').read_bytes()).save(metadata.with_suffix(''))
model = json.loads((R / 'model.json').read_text())
amounts = [0, .141, .15, .16, .20, .214, .25, .35, .65, 1]
sheet = Image.new('RGB', (len(amounts) * 240, len(model['expressions']) * 175), 'white')
draw = ImageDraw.Draw(sheet)
font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
for row, expression in enumerate(model['expressions']):
    for col, amount in enumerate(amounts):
        part = next(p for p in expression['parts'] if p['parameter'] == 'ParamMouthOpenY' and p['state'] == ('closed' if amount == 0 else 'open'))
        avatar = Image.open(R / expression.get('base', model['base'])).convert('RGBA')
        file = R / part['file'] if amount in [0, 1] else R / f'review_textures/{expression["id"]}_{amount:.3f}.png'
        avatar.alpha_composite(Image.open(file).convert('RGBA'), part['rect'][:2])
        sheet.paste(avatar.crop((495, 315, 615, 395)).resize((240, 160)), (col * 240, row * 175))
        draw.text((col * 240, row * 175 + 160), f'{expression["id"]} {amount:.3f}', font=font, fill='black')
sheet.save(output / 'all_mouths_pre_mesh.png')
print(f'Converted exact helper outputs to PNG and saved {output / "all_mouths_pre_mesh.png"}.')
