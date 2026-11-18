#!/usr/bin/env python3
"""Create independently owned v19 arms, fixed torso, skirt, legs, and hair.

Only ownership masks, source registration and PSD/PNG packaging are computed.
New RGB artwork comes exclusively from retained image-tool-painted sources.
The accepted v17 source and original runtime expression files are never edited.
Run from any working directory. Output is intentionally versioned and must be
visually reviewed before publication; original thigh cutouts are not repaired.
"""
import sys,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0,str(ROOT/'scripts'))
from psd_groups_v14 import *
from PIL import Image,ImageDraw
import numpy as np
ns,size=parse_psd_groups('assets/parts/v17/koma_expression_skin_v17.psd');src=composite_psd_groups(ns)
left_inner=[(398,486),(395,520),(392,530),(389,540),(386,550),(383,560),(380,570),(377,580),(374,590),(371,600),(368,610),(368,620),(366,630),(363,640),(360,650),(358,660),(358,670),(356,680),(356,700),(358,720),(359,730),(363,750),(369,775),(375,800),(381,825),(384,850),(384,875),(380,900),(372,925),(359,950),(352,965),(350,975),(335,990),(309,1005),(311,1020),(313,1040),(315,1060),(318,1080),(321,1100),(312,1115),(300,1125),(280,1135),(280,1150),(280,1170),(281,1180),(267,1195),(256,1200),(221,1213),(217,1240),(211,1270),(202,1294),(181,1317),(188,1332),(182,1347),(189,1355),(177,1390),(150,1415)]
left_outer=[(80,1420),(75,1300),(25,1210),(20,1040),(75,930),(155,860),(180,820),(210,750),(241,714),(256,680),(257,648),(278,645),(279,630),(280,610),(283,590),(285,570),(290,550),(295,530),(300,520),(307,510),(320,500),(340,490)]
right_inner=[(731, 501), (740, 530), (743, 540), (746, 550), (749, 560), (753, 570), (758, 580), (761, 590), (761, 600), (764, 610), (767, 620), (770, 630), (770, 640), (774, 650), (781, 660), (785, 670), (793, 680), (790, 690), (791, 700), (792, 710), (792, 720), (792, 730), (791, 740), (790, 750), (788, 760), (786, 770), (784, 780), (782, 790), (779, 800), (777, 810), (775, 820), (772, 830), (770, 840), (767, 850), (765, 860), (763, 870), (761, 880), (760, 890), (760, 900), (762, 910), (763, 920), (763, 930), (768, 940), (773, 950), (776, 960), (780, 970), (790, 990), (800, 1010), (813, 1030), (823, 1050), (833, 1070), (840, 1090), (850, 1110), (859, 1130), (867, 1150), (875, 1170), (878, 1178), (884, 1239), (889, 1248), (896, 1270), (903, 1285), (908, 1305), (920, 1334), (920, 1354), (931, 1371), (922, 1383), (936, 1404), (970, 1420)]
right_outer=[(1035,1420),(1040,1270),(1055,1190),(1055,990),(945,900),(913,820),(890,770),(872,730),(862,678),(854,678),(829,674),(829,650),(827,625),(824,600),(819,575),(814,551),(808,537),(800,524),(790,515),(770,508),(750,498)]
def poly(points):
 im=Image.new('L',size);ImageDraw.Draw(im).polygon(points,fill=255);return np.asarray(im)>0
masks={'arm_screen_left':poly(left_inner+left_outer),'arm_screen_right':poly(right_inner+right_outer)}
# Long vest tails remain on fixed torso; skirt begins under lower belt edge.
# Explicit skirt silhouette includes petticoat and long back ruffles, excludes legs.
skirt=[(424,985),(687,997),(705,1020),(733,1040),(770,1080),(809,1140),(864,1190),(897,1250),(914,1347),(875,1390),(787,1403),(748,1360),(709,1308),(669,1293),(605,1295),(549,1285),(492,1270),(435,1250),(400,1240),(356,1234),(320,1242),(285,1230),(275,1260),(239,1306),(207,1339),(185,1335),(187,1291),(211,1249),(246,1200),(275,1175),(286,1130),(319,1087),(354,1040),(390,1000)]
skirtmask=poly(skirt)
# Include skirt outer silhouette to bottom, but reserve exact front leg contours.
legleft=[(283,1214),(300,1216),(325,1223),(350,1230),(375,1238),(400,1243),(400,1264),(428,1272),(430,1249),(460,1254),(480,1262),(500,1270),(525,1278),(550,1284),(555,1448),(340,1448),(290,1368),(271,1320),(268,1260)]
legright=[(550,1284),(570,1286),(600,1282),(625,1282),(650,1280),(675,1278),(700,1275),(700,1288),(725,1292),(745,1289),(785,1284),(767,1330),(755,1370),(720,1448),(550,1448)]
legs=poly(legleft)|poly(legright)
masks['legs_static']=legs & ~(masks['arm_screen_left']|masks['arm_screen_right'])
masks['skirt']=(np.indices(src.shape[:2])[0]>=985) & ~legs & ~(masks['arm_screen_left']|masks['arm_screen_right'])
# Fix vest tails in front of moving skirt.
vestleft=poly([(379,655),(467,653),(461,840),(449,889),(420,945),(392,987),(349,1045),(331,1090),(303,1146),(277,1176),(280,1135),(300,1125),(312,1115),(321,1100),(315,1060),(309,1005),(335,990),(350,975),(369,875),(371,839)])
vestright=poly([(677,478)]+right_inner[:right_inner.index((878,1178))+1]+[(838,1175),(812,1150),(790,1115),(748,1050),(712,977),(694,938),(687,846),(704,718)])
masks['skirt']&=~(vestleft|vestright)
# Head and hair ownership. The main face/neck is protected, exterior side hair
# stays behind moving arms; inner locks over the lapels are front hair.
y,x=np.indices(src.shape[:2]); head=(y<450)
head|=poly([(0,450),(370,450),(350,480),(320,498),(299,520),(282,570),(265,646),(257,648),(256,680),(241,714),(210,750),(180,780),(0,780)])
head|=poly([(715,450),(1086,450),(1086,480),(1086,780),(890,780),(872,730),(862,678),(854,678),(829,674),(829,650),(827,625),(824,600),(819,575),(814,551),(808,537),(800,524),(790,515),(770,508),(750,498)])
head|=poly([(428,423),(454,442),(478,500),(504,530),(514,570),(503,615),(485,650),(459,675),(428,682),(401,670),(390,650),(421,651),(444,632),(462,610),(468,582),(458,554),(436,530),(421,500)])
head&=~(masks['arm_screen_left']|masks['arm_screen_right'])
front= head & ((y<450)|((x>375)&(x<741)))
back=head&~front
masks['head_hair_front']=front;masks['hair_back']=back
owned=np.logical_or.reduce(list(masks.values()));masks['torso_clothing']=~owned
# Deliver the semantic rig as native editable groups, with only image-tool paint
# on previously occluded supports. All retained visible RGBA comes from v17.
import copy, hashlib, shutil
from scipy.ndimage import distance_transform_edt
from psd_groups_v14 import PixelLayer,LayerGroup,write_psd_groups,parse_psd_groups,composite_psd_groups
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/parts/v19';MODEL=ROOT/'runtime/model';BODY=MODEL/'body_v19';BODY.mkdir(exist_ok=True)
source_path=ROOT/'assets/parts/v17/koma_expression_skin_v17.psd'
base=np.asarray(Image.open(MODEL/'base.png').convert('RGBA'))
opaque=src[:,:,3]==255
arm_union=masks['arm_screen_left']|masks['arm_screen_right']
# The new shoulder support is behind FRONT hair. Retain the exact front strand
# ownership at the contact; the large free rear locks stay behind the arms.
near_arm=distance_transform_edt(~arm_union)<24
contact=masks['hair_back']&near_arm&(y<650)
masks['head_hair_front']|=contact;masks['hair_back']&=~contact
# Unassigned leg-edge pixels belong to skin, never the moving skirt. Follow the
# exact lower leg outer contours, without inventing missing source pixels.
# Masks are semantic ownership; original alpha remains untouched.
leg_outer=poly([(307,1218),(301,1230),(294,1240),(286,1248),(285,1260),(287,1290),(291,1310),(293,1330),(298,1350),(302,1370),(306,1380),(310,1390),(314,1400),(318,1410),(322,1420),(326,1430),(330,1440),(333,1448),(550,1448),(550,1292),(540,1292),(520,1288),(515,1283),(500,1279),(480,1272),(470,1268),(460,1257),(441,1255),(441,1280),(398,1268),(398,1246),(375,1241),(350,1233),(325,1226)])
leg_outer|=poly([(550,1292),(555,1288),(580,1291),(600,1293),(620,1291),(640,1288),(655,1287),(660,1290),(680,1287),(700,1284),(700,1296),(720,1299),(740,1300),(750,1297),(760,1294),(780,1291),(789,1287),(787,1300),(786,1320),(782,1340),(776,1360),(770,1375),(764,1390),(761,1400),(757,1410),(754,1420),(751,1430),(747,1440),(745,1448),(550,1448)])
leg_outer&=~arm_union
masks['skirt']|=masks['legs_static'];masks['legs_static']=leg_outer
masks['skirt']&=~masks['legs_static'];masks['torso_clothing']&=~masks['legs_static']
shoulder_exterior=poly([(0,450),(350,450),(340,490),(320,500),(307,510),(300,520),(295,530),(290,550),(285,570),(283,590),(280,610),(279,630),(278,645),(257,648),(256,680),(241,714),(210,750),(180,780),(0,780)])
shoulder_exterior|=poly([(735,450),(1086,450),(1086,780),(890,780),(872,730),(862,678),(854,678),(829,674),(829,650),(827,625),(824,600),(819,575),(814,551),(808,537),(800,524),(790,515),(770,508),(750,498)])
shoulder_exterior &= ~arm_union & (y>=450)
for k in ['torso_clothing','head_hair_front']:
 masks[k]&=~shoulder_exterior
masks['hair_back']|=shoulder_exterior
contact=masks['hair_back'] & near_arm & (y<550) & opaque
masks['head_hair_front']|=contact;masks['hair_back']&=~contact
# Native outer cuff silhouettes separate both sleeves/bows from rear hair.
# White islands outside these contours are retained original hair matte, not
# sleeve fabric. This is ownership only: no new alpha or painted pixels.
left_cuff_edge=[(278,645),(271,646),(258,650),(258,660),(261,670),(265,680),(267,685),(265,690),(266,695),(268,700),(265,705),(250,710),(246,715),(246,720),(246,725),(244,730),(234,735),(226,740),(220,745),(214,750)]
right_cuff_edge=[(840,673),(850,676),(855,680),(853,690),(850,700),(848,705),(846,710),(847,715),(848,720),(845,725),(841,730),(845,735),(853,740),(853,745),(855,750),(855,755),(852,760),(857,765),(866,770),(874,775)]
for name,zone,exterior in [
 ('arm_screen_left',(y>=645)&(y<=750)&(x>140)&(x<320),poly([(0,645)]+[(px-1,py) for px,py in left_cuff_edge]+[(0,750)])),
 ('arm_screen_right',(y>=673)&(y<=775)&(x>820)&(x<940),poly([(1086,673)]+[(px+1,py) for px,py in right_cuff_edge]+[(1086,775)]))]:
 for mask in masks.values():mask[zone]=False
 masks[name][zone]=~exterior[zone]
 masks['hair_back'][zone]=exterior[zone]
arm_union=masks['arm_screen_left']|masks['arm_screen_right']
# Exclusive ownership must account for every source pixel exactly once.
assert np.all(np.sum(np.stack(list(masks.values())),axis=0)==1)

def masked(data,mask):
 a=data.copy();a[~mask]=0;return a

def put_source(name,box):
 a=np.zeros_like(src);x0,y0,x1,y1=box
 a[y0:y1,x0:x1]=np.asarray(Image.open(OUT/'sources'/name).convert('RGBA').resize((x1-x0,y1-y0),Image.Resampling.LANCZOS))
 return a
body_paint=put_source('body_hidden_paint_v19.png',(130,420,960,1448))
under={name:np.zeros_like(src) for name in masks}
# The smooth painted garment sides are limited to covered original-arm pixels.
# Not alpha dilation, nearest-neighbour color filling, or a duplicate sleeve.
torso_reveal=arm_union&opaque&(y>=650)&(y<1120)&(distance_transform_edt(~masks['torso_clothing'])<18)&(body_paint[:,:,3]>=240)
torso_reveal |= masks['head_hair_front'] & opaque & (y>=450) & (y<700) & (body_paint[:,:,3]>=240)
under['torso_clothing']=masked(body_paint,torso_reveal)
# A narrow covered source-color overlap prevents LINEAR sampling cracks at
# same-role rear/front hair joins; it is opaque and never changes rest pixels.
hair_join=masks['head_hair_front'] & opaque & (distance_transform_edt(~masks['hair_back'])<3)
under['hair_back']=masked(base,hair_join)
skirt_reveal=arm_union&opaque&(y>=1200)&(distance_transform_edt(~masks['skirt'])<42)&(body_paint[:,:,3]>=240)
under['skirt']=masked(body_paint,skirt_reveal)
# Existing native skirt underlayers are already painted and have a small hidden
# continuation beneath the fixed waistband. Reuse their pixels, never extend
# original thigh coverage or invent new anatomy.
waist=(y>=970)&(y<1000)&masks['torso_clothing']&opaque&(x>410)&(x<710)
native_waist=next(n.rgba for n in ns if isinstance(n,PixelLayer) and n.name=='skirt_and_belt')
under['skirt'][waist]=native_waist[waist]
# Shoulder reconstruction registration is restricted to opaque front hair.
shoulder_image=Image.open(OUT/'sources/shoulder_hidden_paint_v19.png').convert('RGBA')
for side,offset in [('left',8),('right',-32)]:
 name='arm_screen_'+side
 mapped=np.asarray(shoulder_image.transform(size,Image.Transform.AFFINE,(1/.83,0,-offset/.83,0,1/.86,-435/.86),resample=Image.Resampling.BICUBIC))
 support=masks['head_hair_front']&opaque&(y>=480)&(y<650)&(distance_transform_edt(~masks[name])<28)&(mapped[:,:,3]>=240)
 under[name]=masked(mapped,support)
# Explicit native layers preserve authored face/skin/lip arrays exactly. All
# expression folders stay at top level so the selector remains familiar.
expressions=[n for n in ns if isinstance(n,LayerGroup)]
original=[n for n in ns if isinstance(n,PixelLayer)]
feature_names={p+'.'+s for p in ('eye_screen_left','eye_screen_right','mouth') for s in ('open','closed')}
order=['hair_back','legs_static','skirt','torso_clothing','arm_screen_left','arm_screen_right','head_hair_front']
roles={'hair_back':'head','legs_static':'root','skirt':'skirt','torso_clothing':'torso','arm_screen_left':'armLeft','arm_screen_right':'armRight','head_hair_front':'head'}
group_names={'hair_back':'07 Rear hair | 後ろ髪','legs_static':'06 Legs fixed | 脚・固定','skirt':'05 Skirt independent | スカート・独立','torso_clothing':'04 Torso clothing fixed | 胴体服・固定','arm_screen_left':'03 Screen-left arm | 画面左の腕・袖・手','arm_screen_right':'02 Screen-right arm | 画面右の腕・袖・手','head_hair_front':'01 Head and front hair | 頭・前髪'}
# Source coverage remains unchanged; filtered cut seams are handled by the
# runtime compositor, not by extending leg/skin alpha.
seams={name:np.zeros_like(src) for name in order}
active=[];native_counts={}
for name in reversed(order):
 children=[]
 for layer in original:
  data=masked(layer.rgba,masks[name])
  if not data[:,:,3].any():continue
  label=layer.name if layer.name in feature_names else name+'/'+layer.name
  children.append(PixelLayer(label,data,layer.visible))
 if under[name][:,:,3].any():children.append(PixelLayer(name+'/painted_hidden_overlap_v19',under[name]))
 if seams[name][:,:,3].any():children.append(PixelLayer(name+'/sampling_edge_overlap_v19',seams[name]))
 active.append(LayerGroup(group_names[name],children,True,name in ('arm_screen_left','arm_screen_right','skirt')))
 native_counts[name]=len(children)
# Backup preserves every original v17 layer and its original RGBA, name and
# visibility inside a hidden parent. Do not enable alongside active groups.
backup=LayerGroup('99 SOURCE V17 BACKUP | 元データ・表示禁止',ns,False)
tree=expressions+active+[backup]
actual=composite_psd_groups(tree)
assert np.array_equal(actual,src),f'rest pose changed {np.count_nonzero(np.any(actual!=src,axis=2))}'
psd=OUT/'koma_separated_body_v19.psd'
write_psd_groups(psd,src,tree,compression_level=6,merged_rle=False)
# Runtime uses the same parts but flattened only within each semantic group.
# Feature sprites stay byte-for-byte identical; expression bases become small
# head crops rather than eight duplicated full-body textures.
manifest=json.loads((MODEL/'model.json').read_text());layers=[]
for name in order:
 rgba=masked(base,masks[name]);rgba_image=Image.fromarray(seams[name]);rgba_image.alpha_composite(Image.fromarray(under[name]));rgba_image.alpha_composite(Image.fromarray(rgba));rgba=np.asarray(rgba_image)
 ys,xs=np.nonzero(rgba[:,:,3]);rect=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
 file='body_v19/'+name+'.png';Image.fromarray(rgba).crop(rect).save(MODEL/file)
 item={'id':name,'role':roles[name],'file':file,'rect':rect,'psdGroup':group_names[name]}
 if name=='head_hair_front':
  item['features']=True;item['expressionFiles']={}
  for exp in manifest['expressions']:
   head=masked(np.asarray(Image.open(MODEL/exp['base']).convert('RGBA')),masks[name])
   filename='body_v19/head_'+exp['id']+'.png';Image.fromarray(head).crop(rect).save(MODEL/filename)
   item['expressionFiles'][exp['id']]=filename
 layers.append(item)
fragment={'bodyLayers':layers,'bodyRig':{'shoulders':[[353,510],[775,530]],'elbows':[[275,935],[850,955]],'waist':[555,995],'skirtTop':995,'skirtHem':1395,'skirtRevealLimitPixels':3},'source_psd':str(psd.relative_to(ROOT))}
(OUT/'model-body-v19.json').write_text(json.dumps(fragment,ensure_ascii=False,indent=2)+'\n')
# Source ownership and paint supports are independently inspectable/testable.
for name,mask in masks.items():Image.fromarray((mask*255).astype('uint8')).save(OUT/'review'/f'{name}_mask.png')
for name,rgba in under.items():
 if rgba[:,:,3].any():Image.fromarray(rgba).save(OUT/'review'/f'{name}_hidden_overlap.png')
# Re-render the exported source-coordinate parts for an end-to-end check.
rest=Image.new('RGBA',size)
for item in layers:
 im=Image.open(MODEL/item['file']);rest.alpha_composite(im,tuple(item['rect'][:2]))
assert np.array_equal(np.asarray(rest),base),'runtime rest mismatch'
rest.save(OUT/'review/runtime_rest_base.png')
# Diagnostic only: rigid offsets expose underpaint ownership, not final rig.
scenes={}
for title,offsets in [('rest',{}),('left_arm_out',{'arm_screen_left':(-18,0)}),('right_arm_out',{'arm_screen_right':(18,0)}),('both_arms_out',{'arm_screen_left':(-18,0),'arm_screen_right':(18,0)}),('arms_hidden',{'arm_screen_left':None,'arm_screen_right':None}),('skirt_right_3px',{'skirt':(3,0)}),('skirt_left_3px',{'skirt':(-3,0)})]:
 frame=Image.new('RGBA',size)
 for name in order:
  offset=offsets.get(name,(0,0))
  if offset is None:continue
  layer=Image.fromarray(seams[name]);layer.alpha_composite(Image.fromarray(under[name]));layer.alpha_composite(Image.fromarray(masked(src,masks[name])))
  frame.alpha_composite(layer,offset)
 scenes[title]=frame;frame.save(OUT/'review'/f'{title}.png')
panel=Image.new('RGB',(4*362,2*500),'#d9dfdf');d=ImageDraw.Draw(panel)
for i,(title,frame) in enumerate(scenes.items()):
 frame=frame.copy();frame.thumbnail((362,470));px=i%4*362;py=i//4*500;panel.paste(frame,(px,py+25),frame);d.text((px+5,py+5),title,fill='black')
panel.save(OUT/'separation_reveal_contact_sheet.png')
# Refresh final semantic ownership sheet (no hidden overlap included).
panel=Image.new('RGB',(4*362,2*500),'#e3e2df');d=ImageDraw.Draw(panel)
for i,name in enumerate(order):
 a=masked(src,masks[name]);Image.fromarray(a).save(OUT/'review'/f'{name}_ownership.png');im=Image.fromarray(a);im.thumbnail((362,470));px=i%4*362;py=i//4*500;panel.paste(im,(px,py+25),im);d.text((px+3,py+5),name,fill='black')
panel.save(OUT/'review/ownership_contact_sheet.png')
report={'source_psd':str(source_path.relative_to(ROOT)),'source_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),'output_psd':str(psd.relative_to(ROOT)),'output_sha256':hashlib.sha256(psd.read_bytes()).hexdigest(),'rest_rgba_changed_pixels':0,'runtime_rest_rgba_changed_pixels':0,'semantic_groups':native_counts,'native_layer_count':sum(native_counts.values()),'paint_sources':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT/'sources').glob('*.png')},'hidden_overlap_pixels':{k:int(np.count_nonzero(v[:,:,3])) for k,v in under.items()},'sampling_edge_gutter_pixels':{k:int(np.count_nonzero(v[:,:,3])) for k,v in seams.items()},'sampling_edge_gutter_width':0,'sampling_edge_gutter_method':'No alpha-expanding native gutters; runtime compositor handles filtered cut seams.','expression_folders_preserved':True,'original_v17_backup_hidden':True,'thigh_underpaint':{'new_pixels_added':False,'handling':'Existing original thigh transparency is preserved. Conservative skirt reveal limits require runtime visual validation.'},'limitations':['PSD-derived preview rig, not Cubism moc3.','Original transparent cutouts within lower legs are preserved intentionally.','Skirt horizontal hem displacement should stay within 3 source pixels until larger authored underpaint is approved.']}
(OUT/'separation-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
