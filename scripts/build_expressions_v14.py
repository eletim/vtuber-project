#!/usr/bin/env python3
"""Package image-tool-painted expressions as additive, switchable PSD folders.

No new facial marks are drawn here. This script only scales the saved paintings,
clips them to a fixed facial support, and packages original pixels and previews.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_psd import parse_psd, composite
from psd_groups_v14 import PixelLayer, LayerGroup, write_psd_groups, parse_psd_groups, composite_psd_groups

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/parts/v14'
SOURCE = ROOT / 'assets/parts/v10/koma_integrated_v10.psd'
CROP = (340, 165, 740, 465)
STATES = [
    ('neutral', '00 Neutral', '通常（元の表情）'),
    ('soft_smile', '01 Soft smile', '微笑み'),
    ('big_smile', '02 Big smile', 'にっこり'),
    ('worried', '03 Worried', '困り顔'),
    ('surprised', '04 Surprised', '驚き'),
    ('bashful', '05 Bashful', '照れ'),
    ('displeased', '06 Displeased', '不満'),
    ('thinking', '07 Thinking', '考え顔'),
]


def make_support():
    # Packaging support follows the inner face and includes the old AND new
    # eyebrows/eyelids/mouth, so no obsolete marks show through. The head outline,
    # exterior hair, accessories, neck and costume are never replaced.
    mask = Image.new('L', (400, 300), 0)
    outline = [(80,105),(87,76),(104,47),(126,24),(148,39),
        (164,76),(190,94),(204,93),(207,20),(237,21),(277,28),
        (300,48),(322,76),(329,103),(316,136),(304,162),
        (286,188),(258,214),(213,241),(175,225),(143,206),
        (116,183),(99,159),(86,137),(76,121)]
    ImageDraw.Draw(mask).polygon(outline, fill=255)
    distance = distance_transform_edt(np.asarray(mask)>0)
    alpha = np.rint(np.clip((distance - 0.5) / 5.0, 0, 1)*255).astype(np.uint8)
    return alpha


def flatten(nodes):
    for node in nodes:
        if isinstance(node, LayerGroup): yield from flatten(node.children)
        else: yield node


def sheet(frames, names, path):
    w, h = 400, 300
    sheet = Image.new('RGB',(w*4, (h+70)*2+75),'#f4eee8')
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    title=ImageFont.truetype(font, 26)
    label=ImageFont.truetype(font, 19)
    small=ImageFont.truetype(font, 13)
    d=ImageDraw.Draw(sheet)
    d.text((24,15),'HAZUKI KOMA  /  EXPRESSION COLLECTION',fill='#49372d',font=title)
    d.text((26,49),'8 ready-to-switch PSD states · Original neutral preserved · v14',fill='#876b59',font=small)
    for i,(frame,name) in enumerate(zip(frames,names)):
        x=(i%4)*w;y=75+(i//4)*(h+70)
        im=Image.fromarray(frame).crop(CROP)
        bg=Image.new('RGBA',im.size,'#eee6de');bg.alpha_composite(im)
        sheet.paste(bg.convert('RGB'),(x,y))
        d.text((x+17,y+h+15),name,fill='#49372d',font=label)
    sheet.save(path)


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'previews').mkdir(exist_ok=True)
    original,size=parse_psd(SOURCE)
    baseline=composite(original)
    alpha=make_support()
    Image.fromarray(alpha).save(OUT/'sources/expression_support_mask.png')
    x0,y0,x1,y1=CROP
    groups=[]
    support=np.zeros(baseline.shape[:2],bool);support[y0:y1,x0:x1]=alpha>0
    source_info={}
    for key,label,jp in STATES[1:]:
        painting_path=OUT/'sources'/f'{key}_painted.png'
        painting=Image.open(painting_path).convert('RGBA').resize((400,300),Image.Resampling.LANCZOS)
        rgb=np.asarray(painting)
        # Source alpha is retained in sources; opaque facial replacement uses
        # the original character's opaque support to prevent ghosted old marks.
        assert np.all(rgb[:,:,3][alpha>0]>=230),f'{key}: missing painted face coverage'
        overlay=np.zeros_like(baseline)
        overlay[y0:y1,x0:x1,:3]=rgb[:,:,:3]
        overlay[y0:y1,x0:x1,3]=alpha
        overlay[overlay[:,:,3]==0]=0
        groups.append(LayerGroup(f'EXP {label} | {jp}',[PixelLayer(f'{key}.painted_face',overlay)],False))
        source_info[key]={'file':str(painting_path.relative_to(ROOT)), 'sha256':hashlib.sha256(painting_path.read_bytes()).hexdigest(),'original_size':Image.open(painting_path).size}
    # Preserve every original layer in its exact original order. Legacy blink
    # toggles work when expression folders are off; the selector resets them
    # before activating a coordinated painted expression.
    tree=groups+[PixelLayer(r['name'],r['data'],r['visible']) for r in original]
    assert np.array_equal(composite_psd_groups(tree),baseline)
    path=OUT/'koma_expression_collection_v14.psd'
    write_psd_groups(path,baseline,tree,compression_level=9)
    reread,readsize=parse_psd_groups(path)
    assert readsize==size
    assert np.array_equal(composite_psd_groups(reread),baseline)
    readlayers={n.name:n for n in flatten(reread)}
    for r in original:
        assert np.array_equal(readlayers[r['name']].rgba,r['data']),r['name']
        assert readlayers[r['name']].visible==r['visible']
    frames=[];measurements={}
    for index,(key,label,jp) in enumerate(STATES):
        show=[] if index==0 else [groups[index-1].name]
        frame=composite_psd_groups(reread,show=show)
        assert np.array_equal(frame,composite_psd_groups(tree,show=show))
        assert np.array_equal(frame[~support],baseline[~support])
        assert np.array_equal(frame[:,:,3],baseline[:,:,3])
        Image.fromarray(frame).save(OUT/'previews'/f'{key}_full.png')
        Image.fromarray(frame).crop(CROP).save(OUT/'previews'/f'{key}_face.png')
        frames.append(frame)
        measurements[key]={'psd_roundtrip_exact':True,'outside_face_changed_pixels':0,'alpha_changed_pixels':0,
            'changed_pixels':int(np.any(frame!=baseline,axis=2).sum()),'folder':show[0] if show else 'All EXP folders off'}
    sheet(frames,[s[1] for s in STATES],OUT/'expression_contact_sheet.png')
    # Preview animation uses the exact same PSD compositions, not source art.
    gif=[Image.fromarray(f).crop(CROP).convert('RGB') for f in frames]
    palette=Image.open(OUT/'expression_contact_sheet.png').quantize(colors=255)
    gif=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in gif]
    gif[0].save(OUT/'expression_cycle.gif',save_all=True,append_images=gif[1:],duration=1250,loop=0)
    # Original neutral independent-eye and mouth swaps also remain byte exact.
    old_states={
        'blink_left':('eye_screen_left',),
        'blink_right':('eye_screen_right',),
        'blink_both':('eye_screen_left','eye_screen_right'),
        'closed_mouth':('mouth',),
        'all_closed':('eye_screen_left','eye_screen_right','mouth')}
    for key,parts in old_states.items():
        hide=[p+'.open' for p in parts];show=[p+'.closed' for p in parts]
        assert np.array_equal(composite(original,hide=hide,show=show),composite_psd_groups(reread,hide=hide,show=show)),key
    report={'source_psd':str(SOURCE.relative_to(ROOT)), 'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'canvas':size,'original_pixel_layers_preserved':66,'expression_folders':7,'total_pixel_layers':73,
        'neutral_changed_pixels':0,'original_blink_states_exact':list(old_states),
        'states':measurements,'artwork_method':'Built-in image_gen edit, one individual painting per expression',
        'crop':CROP,'support':'sources/expression_support_mask.png','sources':source_info,
        'scope':'Facial expression collection only. Existing thigh cutouts and hair matte are unchanged, not repaired.',
        'visual_review':'PENDING','independent_psd_render':'PENDING'}
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(path)

if __name__=='__main__':build()
