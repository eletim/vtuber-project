"""Independent v19 PSD, runtime part and original expression preservation checks."""
from pathlib import Path
import itertools,json,sys,hashlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from psd_groups_v14 import LayerGroup,PixelLayer,parse_psd_groups,composite_psd_groups
OUT=ROOT/'assets/parts/v19';MODEL=ROOT/'runtime/model'

def flat(nodes):
 for n in nodes:
  if isinstance(n,LayerGroup):yield from flat(n.children)
  else:yield n

def render_runtime(fragment,expression,params):
 canvas=Image.new('RGBA',(1086,1448))
 for layer in fragment['bodyLayers']:
  file=layer.get('expressionFiles',{}).get(expression['id'],layer['file'])
  im=Image.open(MODEL/file).convert('RGBA');rect=layer['rect']
  assert im.size==(rect[2]-rect[0],rect[3]-rect[1])
  if layer.get('features'):
   for part in expression['parts']:
    if params[part['parameter']] != (part['state']=='open'):continue
    feature=Image.open(MODEL/part['file']).convert('RGBA');r=part['rect']
    im.alpha_composite(feature,(r[0]-rect[0],r[1]-rect[1]))
  canvas.alpha_composite(im,tuple(rect[:2]))
 return np.asarray(canvas)

def main():
 old,_=parse_psd_groups(ROOT/'assets/parts/v17/koma_expression_skin_v17.psd')
 new,size=parse_psd_groups(OUT/'koma_separated_body_v19.psd');assert size==(1086,1448)
 backup=new[-1];assert isinstance(backup,LayerGroup) and not backup.visible and backup.name.startswith('99 SOURCE')
 active=new[:-1];oldflat={n.name:n for n in flat(old)};newflat={n.name:n for n in flat(active)}
 for name,n in oldflat.items():
  if '.' in name and (name.endswith(('.open','.closed','.face_plate.brows_cheeks'))):
   assert name in newflat,name
   assert n.visible==newflat[name].visible,name
   assert np.array_equal(n.rgba,newflat[name].rgba),name
 for name in ['face_skin_FULL_beneath_eyes_mouth','face_details_without_expression','face_expression_painted_skin_v9','left_eyebrow','right_eyebrow']:
  assert np.array_equal(oldflat[name].rgba,newflat['head_hair_front/'+name].rgba),name
 # Every original backup pixel array and visibility is exact; no source rewrite.
 backflat=list(flat(backup.children)); assert len(backflat)==len(list(flat(old)))
 for a,b in zip(flat(old),backflat):
  assert a.name==b.name and a.visible==b.visible and np.array_equal(a.rgba,b.rgba)
 assert np.array_equal(composite_psd_groups(old),composite_psd_groups(new))
 # Near-opaque generated paint must not silently vanish (source alpha is
 # predominantly252/253, not255). Keep alpha, not threshold-to-opaque fills.
 supports={n.name:n.rgba[:,:,3] for n in flat(active) if n.name.endswith('/painted_hidden_overlap_v19')}
 for name,minimum in [('torso_clothing',1000),('arm_screen_left',100),('arm_screen_right',100),('skirt',1000)]:
  a=supports[name+'/painted_hidden_overlap_v19']
  assert np.count_nonzero(a)>minimum,(name,'missing hidden overlap')
  assert np.count_nonzero((a>0)&(a<255))>(100 if name=='skirt' else minimum//2),(name,'generated alpha was discarded')  # skirt also reuses opaque native waistband pixels
 fragment=json.loads((OUT/'model-body-v19.json').read_text());manifest=json.loads((MODEL/'model.json').read_text())
 assert set(l['role'] for l in fragment['bodyLayers'])=={'root','head','torso','armLeft','armRight','skirt'}
 # Full neutral RGBA was compared above. Every expression-dependent layer
 # is confined to this ROI, so exact ROI endpoints plus invariant exterior
 # establish complete-frame equality without scanning240+full canvas layers
 # for every one of the64 cases.
 roi=(300,150,720,450);x0,y0,x1,y1=roi
 def cropped(nodes):
  out=[]
  for n in nodes:
   if isinstance(n,LayerGroup):
    out.append(LayerGroup(n.name,cropped(n.children),n.visible,n.expanded))
   else:out.append(PixelLayer(n.name,n.rgba[y0:y1,x0:x1],n.visible))
  return out
 for n in flat(old):
  if n.name.endswith(('.open','.closed','.face_plate.brows_cheeks')):
   a=n.rgba[:,:,3];assert not(a[:y0].any() or a[y1:].any() or a[:, :x0].any() or a[:,x1:].any()),n.name
 original_base=np.asarray(Image.open(MODEL/'base.png').convert('RGBA'))
 for exp in manifest['expressions']:
  a=np.asarray(Image.open(MODEL/exp['base']).convert('RGBA'));difference=np.any(a!=original_base,axis=2);difference[y0:y1,x0:x1]=False
  assert not difference.any(),exp['id']
 old_roi=cropped(old);new_roi=cropped(active)
 groups={n.name:n for n in old if isinstance(n,LayerGroup)}
 records=[]
 for exp in manifest['expressions']:
  gid=next((name for name,g in groups.items() if any(p.name.startswith(exp['id']+'.') for p in g.children)),None)
  prefix='' if exp['id']=='neutral' else exp['id']+'.'
  for left,right,mouth in itertools.product((False,True),repeat=3):
   states={'eye_screen_left':left,'eye_screen_right':right,'mouth':mouth}
   show=[gid] if gid else [];hide=[]
   for part,is_open in states.items():
    show.append(prefix+part+('.open' if is_open else '.closed'))
    hide.append(prefix+part+('.closed' if is_open else '.open'))
   before=composite_psd_groups(old_roi,show=show,hide=hide)
   after=composite_psd_groups(new_roi,show=show,hide=hide)
   changed=int(np.count_nonzero(np.any(before!=after,axis=2)));assert changed==0,(exp['id'],states,changed)
   runtime=render_runtime(fragment,exp,{'ParamEyeROpen':left,'ParamEyeLOpen':right,'ParamMouthOpenY':mouth})
   runtime_changed=int(np.count_nonzero(np.any(runtime[y0:y1,x0:x1]!=after,axis=2)))
   assert runtime_changed==0,(exp['id'],states,runtime_changed)
   records.append({'expression':exp['id'],'left_open':left,'right_open':right,'mouth_open':mouth,'psd_changed_pixels':changed,'runtime_changed_pixels':runtime_changed})
 # Independent semantic interior checks avoid relabeling cloth as arm/skirt.
 sentinels=[((805,1020),'torso_clothing'),((820,1060),'torso_clothing'),((850,1140),'torso_clothing'),((403,943),'torso_clothing'),((560,865),'torso_clothing'),((835,620),'hair_back'),((275,630),'hair_back'),((780,1320),'legs_static'),((275,1300),'skirt'),((310,560),'arm_screen_left'),((800,600),'arm_screen_right'),((318,1390),'legs_static'),((338,1440),'legs_static'),((750,1420),'legs_static'),((740,1440),'legs_static'),((480,1268),'skirt'),((530,1286),'skirt'),((660,1285),'skirt'),((735,1295),'skirt'),((435,1260),'skirt')]
 sentinels += [((250,680),'hair_back'),((240,700),'hair_back'),((230,720),'hair_back'),((236,715),'hair_back'),((858,690),'hair_back'),((852,715),'hair_back'),((858,745),'hair_back'),((872,740),'hair_back'),((272,675),'arm_screen_left'),((275,690),'arm_screen_left'),((252,720),'arm_screen_left'),((843,700),'arm_screen_right'),((841,715),'arm_screen_right'),((850,750),'arm_screen_right')]
 masks={p.stem.removesuffix('_mask'):np.asarray(Image.open(p))>0 for p in (OUT/'review').glob('*_mask.png')}
 assert np.all(sum(m.astype('uint8') for m in masks.values())==1)
 for (x,y),expected in sentinels:assert [k for k,m in masks.items() if m[y,x]]==[expected],((x,y),expected)
 # Reviewed native anatomical edge strips, including every scanline between
 # landmarks. These catch thin stationary skin/sleeve remnants that interior
 # sentinels miss. Keep three pixels on each side, away from edge antialiasing.
 # Left x is the inner arm/sleeve edge, right x is its mirrored skin edge.
 left_trace=[(389,540),(386,550),(383,560),(380,570),(377,580),(374,590),(371,600),(368,610),(368,620),(366,630),(363,640),(360,650),(358,660),(358,670),(356,680),(356,700),(358,720),(359,730),(363,750),(369,775),(375,800),(381,825),(384,850),(384,875),(380,900),(372,925),(359,950),(352,965),(350,975)]
 right_trace=[(743, 540), (746, 550), (749, 560), (753, 570), (758, 580), (761, 590), (761, 600), (764, 610), (767, 620), (770, 630), (770, 640), (774, 650), (781, 660), (785, 670), (793, 680), (790, 690), (791, 700), (792, 710), (792, 720), (792, 730), (791, 740), (790, 750), (788, 760), (786, 770), (784, 780), (782, 790), (779, 800), (777, 810), (775, 820), (772, 830), (770, 840), (767, 850), (765, 860), (763, 870), (761, 880), (760, 890), (760, 900), (762, 910), (763, 920), (763, 930), (768, 940), (773, 950), (776, 960), (780, 970)]
 boundary_samples=0
 for trace,arm,direction in [(left_trace,'arm_screen_left',-1),(right_trace,'arm_screen_right',1)]:
  for row in range(trace[0][1],trace[-1][1]+1):
   edge=int(round(float(np.interp(row,[p[1] for p in trace],[p[0] for p in trace]))))
   for distance in (3,4,5):
    inside=edge+direction*distance;outside=edge-direction*distance
    assert masks[arm][row,inside],(arm,'stationary anatomical strip',inside,row)
    assert masks['torso_clothing'][row,outside],(arm,'foreign cloth strip',outside,row)
    boundary_samples+=2
 for x,y in [(384,550),(375,570),(366,600),(378,850)]:
  assert masks['arm_screen_left'][y,x],('native skin/sleeve fixed to torso',x,y)
 # The outside of each cuff includes original brown hair and white hair
 # matte. Test continuous strips around the cuff and the accessory join.
 left_outer=[(258,650),(258,660),(261,670),(265,680),(267,685),(265,690),(266,695),(268,700),(265,705),(250,710),(246,715),(246,720),(246,725),(244,730),(234,735),(226,740),(220,745),(214,750)]
 right_outer=[(855,680),(853,690),(850,700),(848,705),(846,710),(847,715),(848,720),(845,725),(841,730),(845,735),(853,740),(853,745),(855,750),(855,755),(852,760),(857,765),(866,770),(874,775)]
 cuff_samples=0
 for trace,arm,direction in [(left_outer,'arm_screen_left',1),(right_outer,'arm_screen_right',-1)]:
  for row in range(trace[0][1],trace[-1][1]+1):
   edge=int(round(float(np.interp(row,[p[1] for p in trace],[p[0] for p in trace]))))
   for distance in (3,4,5):
    assert masks[arm][row,edge+direction*distance],(arm,'cuff/accessory lost',row,edge)
    assert masks['hair_back'][row,edge-direction*distance],(arm,'foreign hair on sleeve',row,edge)
    cuff_samples+=2
 report={'pass':True,'source_sha256':hashlib.sha256((ROOT/'assets/parts/v17/koma_expression_skin_v17.psd').read_bytes()).hexdigest(),'psd_sha256':hashlib.sha256((OUT/'koma_separated_body_v19.psd').read_bytes()).hexdigest(),'endpoint_scope':'Full neutral frame plus64 expression ROI composites; all state-dependent source/support pixels proven confined to ROI and complete exterior invariant.','endpoint_roi':list(roi),'endpoint_cases':len(records),'endpoints':records,'face_expression_pixels_preserved':True,'semantic_sentinels_pass':True,'anatomical_boundary_strip_samples':boundary_samples,'anatomical_boundary_strips_pass':True,'outer_cuff_boundary_strip_samples':cuff_samples,'outer_cuff_boundary_strips_pass':True,'original_backup_exact':True,'source_ownership_exclusive':True}
 (OUT/'psd-runtime-verification.json').write_text(json.dumps(report,indent=2)+'\n')
 print('PASS v19 native PSD/rest/64 expression endpoints/runtime ordered RGBA/semantic sentinels/hidden original backup')
if __name__=='__main__':main()
