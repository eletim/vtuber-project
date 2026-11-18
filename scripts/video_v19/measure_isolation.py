"""Verify actual role output arrays, not only parameter names or ownership metadata."""
from pathlib import Path
import json,hashlib
import numpy as np
D=Path(__file__).resolve().parent;plan=json.loads((D/'frames.json').read_text());model=json.loads((D/'source/runtime/model/model.json').read_text());n=len(plan['frames']);nx,ny=model['mesh'];nv=(nx+1)*(ny+1);size=np.array(model['size']);uv=np.array([(x/nx,y/ny) for y in range(ny+1) for x in range(nx+1)])
mesh={r:np.memmap(D/f'mesh-{r}.bin',np.float32,mode='r',shape=(n,nv,2)) for r in plan['roles']}
sections={'left_arm':(0,150,'armLeft'),'right_arm':(150,300,'armRight'),'skirt':(300,480,'skirt')};results={};peaks=[]
for name,(lo,hi,moving) in sections.items():
 fixed={r:bool(np.array_equal(mesh[r][lo:hi],np.broadcast_to(mesh[r][lo],mesh[r][lo:hi].shape))) for r in mesh if r!=moving}
 assert all(fixed.values()),(name,fixed)
 delta=np.linalg.norm((mesh[moving][lo:hi]-mesh[moving][lo])*size,axis=2);frame=int(np.argmax(delta.max(axis=1)))+lo;peaks.append(frame)
 maxmove=float(delta.max());assert maxmove>1,(name,maxmove)
 results[name]={'frames':[lo,hi-1],'moving_role':moving,'all_other_role_arrays_identical':fixed,'moving_role_peak_frame':frame,'max_source_pixel_displacement':maxmove}
 if moving=='skirt':
  top=model.get('bodyRig',{}).get('skirtTop',995)+8;waist=(uv[:,1]*size[1]<=top);anchored=bool(np.array_equal(mesh[moving][lo:hi,waist],np.broadcast_to(mesh[moving][lo,waist],mesh[moving][lo:hi,waist].shape)));assert anchored
  results[name]['waist_and_above_grid_vertices_bit_identical']=anchored;results[name]['waist_threshold_source_y']=top
# Independently reset diagnostic scenes are deliberate setup, never skipped simulation.
assert all(np.array_equal(mesh['torso'][0],mesh['torso'][i]) for i in range(540))
for r in mesh:
 assert np.isfinite(mesh[r]).all(),r
# Keep brief selection: baseline, both arm peaks, both skirt directions, combined eight faces, final.
skirt_delta=(mesh['skirt'][300:480]-mesh['skirt'][300])*size
skirt_opposite=300+int(np.argmin(skirt_delta[:,:,0].mean(axis=1)))
review=sorted(set([0,149,150,*peaks,skirt_opposite,479,539,570,675,780,885,990,1095,1200,1305,1439]))
face_reviews=[]
for expression in plan['ids']:
 eligible=[f for f in plan['frames'] if f['expressionFrame']['id']==expression and f['section']=='natural' and f['expressionFrame']['gate']>.99]
 for target in [0,.2,.55]:
  selected=min(eligible,key=lambda f:abs(f['facePose']['ParamMouthOpenY']-target))
  face_reviews.append({'expression':expression,'target_opening':target,'frame':selected['i'],'actual_opening':selected['facePose']['ParamMouthOpenY']})
plan['faceReviewFrames']=face_reviews
plan['diagnosticPeakFrameIndices']=peaks+[skirt_opposite];plan['reviewFrameIndices']=review;plan['gestureWindowFrameIndices']=peaks[:2]+[peaks[2]]
(D/'frames.json').write_text(json.dumps(plan,ensure_ascii=False));result={'passed':True,'sections':results,'torso_identical_across_all_540_diagnostic_frames':True,'mesh_sha256':{r:hashlib.sha256((D/f'mesh-{r}.bin').read_bytes()).hexdigest() for r in mesh},'roles':plan['roles'],'layers':plan['layers'],'method':'Float32 output from chronological production BodyRig.frames; each diagnostic scene initializes a resting rig, then simulates every 1/30 s frame. Natural section uses one uninterrupted PerformanceMotion/BodyRig instance.'}
(D/'isolation-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(results,indent=2))
