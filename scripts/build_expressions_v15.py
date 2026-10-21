#!/usr/bin/env python3
"""Package painted eye/mouth endpoints without drawing any new artwork.

v14 authored poses remain exact. Every new expression is a clean painted facial
plate plus six independently switchable, opaque-restoration feature layers.
Only existing/image-tool-painted RGB pixels, geometry, masks and packaging are
used. The original 66 v10 layers and top-level runtime textures stay unchanged.
"""
from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_psd import parse_psd, composite
from build_expressions_v14 import STATES, CROP, make_support
from psd_groups_v14 import (
    PixelLayer, LayerGroup, write_psd_groups, parse_psd_groups,
    composite_psd_groups,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/parts/v15'
MODEL = ROOT / 'runtime/model'
SOURCE = ROOT / 'assets/parts/v10/koma_integrated_v10.psd'
V14 = ROOT / 'assets/parts/v14'
PSD = OUT / 'koma_expression_motion_v15.psd'
PARTS = ('eye_screen_left', 'eye_screen_right', 'mouth')
PARAMETERS = dict(zip(PARTS, ('ParamEyeROpen', 'ParamEyeLOpen', 'ParamMouthOpenY')))
DRAW_ORDER = ('mouth.open','eye_screen_right.open','eye_screen_right.closed',
              'eye_screen_left.open','eye_screen_left.closed','mouth.closed')

# Coordinates are local to the recorded 400 x 300 facial source crop. These
# are packaging masks, not painted marks. Eyebrows and cheeks stay on the plate.
SUPPORT_POLYGONS = {
    'eye_screen_left': [(75,127),(85,107),(104,92),(137,86),(160,92),
                        (174,110),(176,139),(163,156),(137,161),
                        (111,156),(92,146)],
    'eye_screen_right': [(227,101),(234,81),(254,67),(284,59),(307,64),
                         (323,78),(322,105),(307,122),(282,129),
                         (251,128),(233,117)],
    'mouth': [(170,168),(187,159),(216,156),(244,160),(260,174),
              (257,205),(243,219),(215,224),(187,217),(174,201)],
}

# Newly generated paintings may also change their brows. Clip their painted
# eye endpoints to the eyelids only, then retain the clean expression-specific
# base everywhere else inside the opaque restoration sprite.
NEW_ART_POLYGONS = {
    'eye_screen_left': [(76,132),(92,116),(114,106),(146,103),
                        (174,115),(176,140),(149,151),(110,155),(88,146)],
    'eye_screen_right': [(226,105),(239,89),(262,79),(286,74),
                         (319,78),(326,98),(313,114),(284,123),
                         (250,127),(229,118)],
}

# The bounding core deliberately excludes forehead, brows, large hair masses
# and the support's stationary feathered border. Runtime deformation takes
# place inside this core, never by scaling an entire rectangular face patch.
MOTION_LOCAL = {
    'eye_screen_left': {'anchor':[129,125], 'bounds':[83,99,168,153]},
    'eye_screen_right': {'anchor':[270,98], 'bounds':[235,68,316,123]},
    'mouth': {'anchor':[213,191], 'bounds':[181,171,250,215]},
}

# Only explicit source registration transforms are permitted. The generated
# paintings are resized to CROP, and any later small translation is recorded.
SOURCE_OFFSETS = {key: (0, 0) for key, *_ in STATES[1:]}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def flatten(nodes):
    for node in nodes:
        if isinstance(node, LayerGroup):
            yield from flatten(node.children)
        else:
            yield node


def alpha_over(dst, src):
    """Exact normal blend used for endpoint verification, preserving alpha."""
    out = dst.copy()
    a = src[:, :, 3]
    opaque = a == 255
    partial = (a > 0) & (a < 255)
    out[opaque] = src[opaque]
    if partial.any():
        sa = a[partial, None].astype(np.float64) / 255
        da = dst[partial, 3:4].astype(np.float64) / 255
        oa = sa + da * (1-sa)
        out[partial, :3] = np.rint((src[partial, :3]*sa +
            dst[partial, :3]*da*(1-sa))/oa).clip(0,255).astype(np.uint8)
        out[partial, 3] = np.rint(oa[:,0]*255).astype(np.uint8)
    return out


def local_masks(key=None):
    outer = make_support()
    masks = {}
    for name, polygon in SUPPORT_POLYGONS.items():
        polygon=copy.deepcopy(polygon)
        if key=='surprised' and name!='mouth':
            # Surprise raises the upper lash substantially; its high brows
            # remain outside this widened eyelid-only support.
            polygon=[(x,y-15 if i in (1,2,3,4) else y)
                     for i,(x,y) in enumerate(polygon)]
            if name=='eye_screen_right':
                for i,y in ((1,54),(2,42),(3,40),(4,45)):
                    polygon[i]=(polygon[i][0],y)
        elif key=='thinking' and name=='eye_screen_right':
            for i,y in ((1,65),(2,45),(3,42),(4,48)):
                polygon[i]=(polygon[i][0],y)
        im = Image.new('L', (400, 300), 0)
        ImageDraw.Draw(im).polygon(polygon, fill=255)
        distance = distance_transform_edt(np.asarray(im) > 0)
        feather=2 if name!='mouth' else 4
        alpha = np.rint(np.clip((distance-0.5)/feather,0,1)*255).astype(np.uint8)
        alpha[outer == 0] = 0
        # The underpaint only changes beneath the opaque feature interior.
        # Feather pixels sit on identical original pixels at the rest endpoint.
        erase = np.rint(np.clip((distance-feather-0.5)/2,0,1)*255).astype(np.uint8)
        erase[(alpha < 255) | (outer < 255)] = 0
        masks[name] = (alpha, erase)
    return masks


def load_painting(key):
    path = OUT / 'sources' / f'{key}_blink_speech.png'
    src = Image.open(path).convert('RGBA')
    original_size = list(src.size)
    src = src.resize((400, 300), Image.Resampling.LANCZOS)
    dx, dy = SOURCE_OFFSETS[key]
    if dx or dy:
        src = src.transform((400,300), Image.Transform.AFFINE,
            (1,0,-dx,0,1,-dy), resample=Image.Resampling.BICUBIC)
    return np.asarray(src).copy(), {
        'file':str(path.relative_to(ROOT)), 'sha256':sha256(path),
        'original_size':original_size, 'mapped_crop':list(CROP),
        'translation':[dx,dy],
    }


def authored_defaults(key):
    return {
        'ParamEyeLOpen':0 if key == 'big_smile' else 1,
        'ParamEyeROpen':0 if key == 'big_smile' else 1,
        'ParamMouthOpenY':1 if key in ('neutral','big_smile','surprised') else 0,
    }


def motion_for(name,key=None):
    local = copy.deepcopy(MOTION_LOCAL[name])
    if key=='surprised' and name!='mouth':
        local['bounds'][1]=78 if name=='eye_screen_left' else 54
    x,y,_,_ = CROP
    a = local['anchor']; b=local['bounds']
    return {'anchor':[a[0]+x,a[1]+y],
            'bounds':[b[0]+x,b[1]+y,b[2]+x,b[3]+y]}


def save_part(out, key, name, state, full):
    ys,xs = np.nonzero(full[:,:,3])
    rect=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
    filename=f'expressions/{key}/{name}_{state}.png'
    path=out/filename;path.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(full).crop(rect).save(path)
    return {'name':f'{name}.{state}','parameter':PARAMETERS[name],
            'state':state,'rect':rect,'file':filename,'motion':motion_for(name,key)}


def composition(base, parts, states):
    result=base.copy()
    for full_name in DRAW_ORDER:
        name,state=full_name.rsplit('.',1)
        if states[name]==state:result=alpha_over(result,parts[(name,state)])
    return result


def build_expression(key, label, jp, baseline, original_overlay, skin, masks):
    generated, source_info=load_painting(key)
    x0,y0,x1,y1=CROP
    rest=np.asarray(Image.open(V14/'previews'/f'{key}_full.png').convert('RGBA'))
    rest_crop=rest[y0:y1,x0:x1]
    plate=original_overlay.copy()
    plate_crop=plate[y0:y1,x0:x1]
    for name,(alpha,erase) in masks.items():
        mask=erase>0
        t=erase[mask,None].astype(np.float64)/255
        plate_crop[mask,:3]=np.rint(skin[mask,:3]*t+
            plate_crop[mask,:3]*(1-t)).astype(np.uint8)
    base=alpha_over(baseline,plate)
    defaults=authored_defaults(key)
    art={};children=[];manifest_parts=[]
    # Both smile-eye endpoints are the approved closed-eye design. This is
    # intentional: blinking must not turn a joyful smile into another eye style.
    for name in PARTS:
        alpha,_=masks[name]
        for state in ('closed','open'):
            endpoint=int(state == 'open')
            use_rest=(endpoint==defaults[PARAMETERS[name]])
            if key=='big_smile' and name!='mouth':use_rest=True
            rgb=rest_crop if use_rest else generated
            if not use_rest and name in NEW_ART_POLYGONS:
                gate=Image.new('L',(400,300),0)
                ImageDraw.Draw(gate).polygon(NEW_ART_POLYGONS[name],fill=255)
                distance=distance_transform_edt(np.asarray(gate)>0)
                a=np.clip((distance-0.5)/3,0,1)[:,:,None]
                rgb=base[y0:y1,x0:x1].copy()
                rgb[:,:,:3]=np.rint(generated[:,:,:3]*a+
                    rgb[:,:,:3]*(1-a)).astype(np.uint8)
            # Image-tool source alpha is retained verbatim in sources. Its
            # painted facial RGB is deliberately made opaque inside the support
            # (some returned paintings contain translucent but complete skin).
            assert np.all(rgb[:,:,3][alpha>0]>0), f'{key}/{name}/{state}: missing painted RGB'
            full=np.zeros_like(baseline)
            full[y0:y1,x0:x1,:3]=rgb[:,:,:3]
            full[y0:y1,x0:x1,3]=alpha
            full[full[:,:,3]==0]=0
            art[(name,state)]=full
            visible=endpoint==defaults[PARAMETERS[name]]
            children.append(PixelLayer(f'{key}.{name}.{state}',full,visible))
            manifest_parts.append(save_part(MODEL,key,name,state,full))
    children.append(PixelLayer(f'{key}.face_plate.brows_cheeks',plate,True))
    group=LayerGroup(f'EXP {label} | {jp}',children,False)
    filename=f'expressions/{key}/base.png'
    Image.fromarray(base).save(MODEL/filename)
    entry={'id':key,'label':label,'label_ja':jp,'base':filename,
           'parts':manifest_parts,'defaults':{**defaults,'ParamMouthOpenY':0},
           'authoredDefaults':defaults,'eyeOpenMax':0 if key=='big_smile' else 1,
           'folder':group.name}
    states={name:'open' if defaults[PARAMETERS[name]] else 'closed' for name in PARTS}
    assert np.array_equal(composition(base,art,states),rest),f'{key}: rest differs from v14'
    return group,entry,base,art,source_info


def contact_sheet(rows, filename, subtitle):
    w,h=400,300
    cols=len(rows[0][1]); rh=h+38
    im=Image.new('RGB',(cols*w,70+len(rows)*rh),'#f4eee8')
    d=ImageDraw.Draw(im)
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    title=ImageFont.truetype(font,23);small=ImageFont.truetype(font,16)
    d.text((16,12),'HAZUKI KOMA / EXPRESSION MOTION v15',fill='#49372d',font=title)
    d.text((16,43),subtitle,fill='#876b59',font=small)
    for row,(label,frames) in enumerate(rows):
        for col,(name,frame) in enumerate(frames):
            x=col*w;y=70+row*rh
            crop=Image.fromarray(frame).crop(CROP)
            bg=Image.new('RGBA',(w,h),'#eee6de');bg.alpha_composite(crop)
            im.paste(bg.convert('RGB'),(x,y))
            d.text((x+10,y+h+8),f'{label} / {name}',fill='#49372d',font=small)
    im.save(filename)


def build():
    for directory in (OUT,OUT/'previews',OUT/'supports',MODEL/'expressions'):
        directory.mkdir(parents=True,exist_ok=True)
    missing=[str(OUT/'sources'/f'{key}_blink_speech.png') for key,*_ in STATES[1:]
             if not (OUT/'sources'/f'{key}_blink_speech.png').exists()]
    if missing:raise FileNotFoundError('Waiting for painted sources: '+', '.join(missing))
    legacy=json.loads((MODEL/'model.json').read_text())
    legacy.pop('expressions',None)
    legacy.pop('expression_source_psd',None)
    original,size=parse_psd(SOURCE)
    baseline=composite(original)
    v14_tree,_=parse_psd_groups(V14/'koma_expression_collection_v14.psd')
    original_overlays={g.children[0].name.split('.')[0]:g.children[0].rgba
                       for g in v14_tree if isinstance(g,LayerGroup)}
    skin_full=np.zeros_like(baseline)
    skin_full[130:480,305:730]=np.asarray(Image.open(
        ROOT/'assets/parts/v9/face_skin_painted_source.png').convert('RGBA').resize(
        (425,350),Image.Resampling.LANCZOS))
    x0,y0,x1,y1=CROP;skin=skin_full[y0:y1,x0:x1]
    masks=local_masks()
    for name,(alpha,erase) in masks.items():
        Image.fromarray(alpha).save(OUT/'supports'/f'{name}.png')
        Image.fromarray(erase).save(OUT/'supports'/f'{name}_underpaint.png')
    originals=[PixelLayer(r['name'],r['data'],r['visible']) for r in original]
    groups=[];entries=[];sources={};assets={};rows=[]
    neutral_parts=copy.deepcopy(legacy['parts'])
    for p in neutral_parts:p['motion']=motion_for(p['name'].rsplit('.',1)[0])
    # The legacy face supports overlap slightly. Match the original PSD's
    # bottom-to-top order here, while leaving top-level legacy metadata intact.
    neutral_parts.sort(key=lambda p:DRAW_ORDER.index(p['name']))
    entries.append({'id':'neutral','label':STATES[0][1],'label_ja':STATES[0][2],
        'base':legacy['base'],'parts':neutral_parts,
        'defaults':{**authored_defaults('neutral'),'ParamMouthOpenY':0},
        'authoredDefaults':authored_defaults('neutral'),'eyeOpenMax':1,
        'folder':'All EXP folders off'})
    for key,label,jp in STATES[1:]:
        expression_masks=local_masks(key)
        (OUT/'supports'/key).mkdir(exist_ok=True)
        for name,(alpha,erase) in expression_masks.items():
            Image.fromarray(alpha).save(OUT/'supports'/key/f'{name}.png')
            Image.fromarray(erase).save(OUT/'supports'/key/f'{name}_underpaint.png')
        group,entry,base,art,info=build_expression(
            key,label,jp,baseline,original_overlays[key],skin,expression_masks)
        groups.append(group);entries.append(entry);sources[key]=info
        assets[key]=(base,art)
    manifest={**legacy,'expressions':entries,'expression_source_psd':str(PSD.relative_to(ROOT))}
    (MODEL/'model.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Runtime textures and manifest ready; PSD roundtrip verification in progress.',flush=True)
    tree=groups+originals
    assert np.array_equal(composite_psd_groups(tree),baseline)
    write_psd_groups(PSD,baseline,tree,compression_level=9)
    reread,reread_size=parse_psd_groups(PSD)
    assert reread_size==size
    assert np.array_equal(composite_psd_groups(reread),baseline)
    actual={n.name:n for n in flatten(reread)}
    for r in original:
        assert np.array_equal(actual[r['name']].rgba,r['data']),r['name']
        assert actual[r['name']].visible==r['visible'],r['name']
    scope=np.zeros(baseline.shape[:2],bool);scope[y0:y1,x0:x1]=make_support()>0
    measurements={}
    for index,(key,label,jp) in enumerate(STATES):
        entry=entries[index];defaults=entry['authoredDefaults']
        if key=='neutral':
            base=np.asarray(Image.open(MODEL/entry['base']).convert('RGBA'))
            art={(name,state):next(r['data'] for r in original if r['name']==name+'.'+state)
                 for name in PARTS for state in ('closed','open')}
        else:base,art=assets[key]
        frames=[]
        for bits in itertools.product((0,1),repeat=3):
            states={name:'open' if value else 'closed' for name,value in zip(PARTS,bits)}
            frame=composition(base,art,states)
            selected=[];hidden=[]
            for name in PARTS:
                prefix=f'{key}.' if key!='neutral' else ''
                selected.append(prefix+name+'.'+states[name])
                hidden.append(prefix+name+'.'+('closed' if states[name]=='open' else 'open'))
            if key!='neutral':selected.append(groups[index-1].name)
            # Original base was verified above; reuse its exact composite for
            # expression-only checks rather than reblending 66 invariant layers.
            check_tree=reread if key=='neutral' else [reread[index-1],PixelLayer('verified legacy base',baseline)]
            rendered=composite_psd_groups(check_tree,show=selected,hide=hidden)
            assert np.array_equal(frame,rendered),f'{key}/{bits}: PSD endpoint mismatch'
            assert np.array_equal(frame[:,:,3],baseline[:,:,3]),f'{key}/{bits}: alpha changed'
            if key!='neutral':
                assert np.array_equal(frame[~scope],baseline[~scope]),f'{key}/{bits}: face scope'
            basename=f'{key}_L{bits[0]}_R{bits[1]}_M{bits[2]}'
            Image.fromarray(frame).crop(CROP).save(OUT/'previews'/f'{basename}_face.png')
            if bits==tuple(defaults[PARAMETERS[name]] for name in PARTS):
                expected=np.asarray(Image.open(V14/'previews'/f'{key}_full.png').convert('RGBA'))
                assert np.array_equal(frame,expected),f'{key}: v14 authored pose not exact'
                Image.fromarray(frame).save(OUT/'previews'/f'{key}_authored_full.png')
            frames.append((f'L{bits[0]} R{bits[1]} M{bits[2]}',frame))
        Image.fromarray(base).crop(CROP).save(OUT/'previews'/f'{key}_features_hidden.png')
        # Four useful simultaneous endpoints, plus separate-eye contacts.
        rows.append((label,[frames[i] for i in (6,7,0,1)]))
        contact_sheet([(label,frames[:4]),(label,frames[4:])],
                      OUT/'previews'/f'{key}_state_contact_sheet.png','All independent eye / mouth endpoints')
        measurements[key]={'combinations_reloaded':8,'psd_runtime_exact':True,
            'v14_authored_pose_exact':True,'alpha_changes':0,
            'outside_expression_face_changes':0 if key!='neutral' else 'Legacy unchanged'}
    contact_sheet(rows,OUT/'expression_motion_contact_sheet.png',
                  'Open / closed eyes x open / closed mouth; big-smile eyes intentionally stay closed')
    hidden_rows=[(label,[("Features hidden",np.asarray(Image.open(MODEL/entry['base']).convert('RGBA')))])
                 for (key,label,jp),entry in zip(STATES,entries)]
    contact_sheet(hidden_rows,OUT/'painted_underpaint_contact_sheet.png','Painted clean skin reveal; brows and cheeks remain on each facial plate')
    manifest={**legacy,'expressions':entries,'expression_source_psd':str(PSD.relative_to(ROOT))}
    (MODEL/'model.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    report={
        'source_psd':str(SOURCE.relative_to(ROOT)),'source_sha256':sha256(SOURCE),
        'v14_psd':str((V14/'koma_expression_collection_v14.psd').relative_to(ROOT)),
        'v14_sha256':sha256(V14/'koma_expression_collection_v14.psd'),
        'canvas':list(size),'original_pixel_layers_preserved':66,
        'expression_groups':7,'new_pixel_layers':49,'total_pixel_layers':115,
        'neutral_changed_pixels':0,'legacy_combinations_exact':8,
        'states':measurements,'sources':sources,
        'underpaint_source':'assets/parts/v9/face_skin_painted_source.png',
        'underpaint_source_sha256':sha256(ROOT/'assets/parts/v9/face_skin_painted_source.png'),
        'underpaint_source_crop':[305,130,730,480],
        'artwork_method':'Built-in image-tool endpoint paintings and existing approved painted sources only; code masks and packaging only.',
        'scope':'Facial animation only. Existing thigh cutouts and hair matte are unchanged, not repaired. Not a Cubism moc3 export.',
        'visual_review':'PENDING','independent_psd_render':'PENDING',
    }
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(PSD)


if __name__=='__main__':
    build()
