"""Non-destructive native authoring checkpoint, not a released motion rig.

Existing native v19 groups remain retained in a hidden backup. Visible rest
pixels are partitioned once; new RGB paint is sourced only from imagegen.
No generated face or torso pixels replace approved artwork.
"""
from pathlib import Path
import copy, hashlib, json
import numpy as np
from PIL import Image, ImageDraw
from psd_groups_v14 import PixelLayer, LayerGroup, parse_psd_groups, composite_psd_groups, write_psd_groups

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/parts/v22'
SOURCE=ROOT/'assets/parts/v19/koma_separated_body_v19.psd'
EXPECTED='0f1d28279d0256f2a7ba860422709041f701dade3becf361c2b54bf5342ba3f4'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
tree,size=parse_psd_groups(SOURCE)
original=composite_psd_groups(tree)
y,x=np.indices(original.shape[:2])

def mask_polygon(points):
    mask=Image.new('L',size)
    ImageDraw.Draw(mask).polygon(points,fill=255)
    return np.asarray(mask)>0

def cut(pixels,mask):
    out=pixels.copy();out[~mask]=0
    return out

def partition(pixels,regions):
    remaining=np.ones(pixels.shape[:2],bool);layers=[]
    for name,mask in regions:
        owned=remaining&mask;remaining&=~mask
        layers.append(PixelLayer(name,cut(pixels,owned)))
    layers.append(PixelLayer('fixed remainder',cut(pixels,remaining)))
    assert np.array_equal(composite_psd_groups(layers),pixels)
    return layers

visible=[]
for node in tree:
    if not node.visible: continue
    pixels=composite_psd_groups([node])
    if node.name.startswith(('02 Screen','03 Screen')):
        side='screen-left' if node.name.startswith('03') else 'screen-right'
        # These are editable ownership cuts; elbow and cuff seams still need
        # authored overlap and final joint placement before rig activation.
        regions=[('wrist and hand',y>=1210),('forearm sleeve', (y>=820)&(y<1210)),('upper arm and upper sleeve',y<820)]
        visible.append(LayerGroup(f'{side} / joint authoring',partition(pixels,regions)))
    elif node.name.startswith('01 Head'):
        # Exclusive spatial regions include their existing baked pixels, so
        # no duplicate hair remains in the fixed remainder. Hidden reveal
        # artwork must be authored separately before these regions move.
        bangs=mask_polygon([(404,70),(563,35),(646,190),(650,242),(593,218),(566,276),(527,269),(488,251),(471,198),(429,245),(385,316),(366,243)])
        left=mask_polygon([(366,210),(406,260),(422,340),(463,386),(471,467),(490,540),(514,590),(483,655),(429,684),(390,666),(424,644),(465,604),(467,576),(435,536),(421,500),(376,485),(325,502),(285,480),(234,420),(240,270)])
        right=mask_polygon([(650,185),(703,210),(740,265),(728,350),(704,414),(740,476),(796,505),(865,520),(865,620),(752,580),(679,509),(609,502),(615,455),(649,404),(656,332),(662,265)])
        regions=[('bang left',bangs&(x<486)),('bang middle',bangs&(x>=486)&(x<565)),('bang right',bangs&(x>=565)),('left side inner',left&(x>=376)),('left side outer',left&(x<376)),('right side inner',right&(x<706)),('right side outer',right&(x>=706))]
        visible.append(LayerGroup('head hair ownership STUDY / reveal paint pending',partition(pixels,regions)))
    elif node.name.startswith('07 Rear'):
        regions=[('rear left outer',x<260),('rear left inner',(x>=260)&(x<543)),('rear right inner',(x>=543)&(x<820)),('rear right outer',x>=820)]
        visible.append(LayerGroup('rear hair ownership STUDY',partition(pixels,regions)))
    else: visible.append(copy.deepcopy(node))

paint=np.asarray(Image.open(OUT/'sources/bent-arm-imagegen.png').convert('RGBA'))
paint=paint.copy();paint[paint[:,:,3]==0]=0
assert (paint.shape[1],paint.shape[0])==size
arm=mask_polygon([(379,335),(398,325),(425,319),(429,332),(416,347),(442,343),(462,350),(474,359),(468,366),(453,365),(466,381),(482,402),(497,425),(498,449),(478,501),(465,545),(491,578),(520,636),(523,674),(510,701),(526,745),(513,782),(479,802),(478,842),(453,879),(406,911),(355,935),(310,927),(267,914),(226,882),(218,853),(192,831),(184,803),(198,746),(219,685),(260,621),(273,571),(302,562),(317,510),(348,482),(376,477),(401,490),(422,468),(439,449),(420,425),(399,410),(387,385),(379,359)])
pose=cut(paint,arm)
fold=mask_polygon([(377,526),(409,541),(430,576),(454,612),(484,640),(517,669),(498,692),(471,696),(435,675),(406,638),(391,586)])
parts=partition(pose,[('hand wrist / painted raised pose',y<460),('inner cuff and compressed fold / painted',fold),('upper arm / painted', (x<413)&(y<568)),('forearm and hanging sleeve / painted',np.ones(y.shape,bool))])
candidate=LayerGroup('HIDDEN raised arm PAINT STUDY / not rigged',parts,False)
expressions=[copy.deepcopy(n) for n in tree if n.name.startswith('EXP ')]
backup=LayerGroup('HIDDEN ORIGINAL v19 / exact native backup',copy.deepcopy(tree),False)
result=expressions+visible+[candidate,backup]
actual=composite_psd_groups(result)
assert np.array_equal(actual,original),'Visible approved rest changed'
OUT.mkdir(exist_ok=True)
target=OUT/'koma_v22_authoring_checkpoint.psd'
write_psd_groups(target,actual,result,compression_level=6,merged_rle=False)
roundtrip,_=parse_psd_groups(target)
assert np.array_equal(composite_psd_groups(roundtrip),original)
Image.fromarray(pose).save(OUT/'sources/bent-arm-extracted-study.png')
Image.fromarray(actual).save(OUT/'authoring-rest.png')
report={'status':'authoring checkpoint; NOT a finished or active v22 rig','source_sha256':EXPECTED,'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'rest_changed_rgba_values':int(np.count_nonzero(actual!=original)),'native_backup_retained':True,'expression_groups_retained':len(expressions),'source_paint':'built-in imagegen; single-arm pose source; generated face and body excluded','pending':['authored joint overlap and anatomy review','hair reveal paint and hair-only ownership refinement','eight runtime expression bases without baked hair','articulated runtime rig','intermediate pose and black/white combination QA','sample video of new motion']}
(OUT/'authoring-checkpoint.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
