from pathlib import Path
import json,hashlib,wave,argparse
import numpy as np
D=Path(__file__).resolve().parent;parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path,default=D.parent/'vtuber-v17-preview');args=parser.parse_args();O=args.baseline;plan=json.loads((D/'frames.json').read_text());model=json.loads((D/'source/runtime/model/model.json').read_text());n=len(plan['frames']);nx,ny=model['mesh'];width,height=model['size']
a=np.fromfile(O/'mesh.bin',dtype=np.float32).reshape(n,-1,2)*[width,height];b=np.fromfile(D/'mesh.bin',dtype=np.float32).reshape(n,-1,2)*[width,height]
def point(mesh,p):
 u,v=p[0]/width*nx,p[1]/height*ny;x,y=int(u),int(v);fx,fy=u-x,v-y;k=y*(nx+1)+x
 if fx+fy<=1:return mesh[:,k]*(1-fx-fy)+mesh[:,k+1]*fx+mesh[:,k+nx+1]*fy
 return mesh[:,k+1]*(1-fy)+mesh[:,k+nx+1]*(1-fx)+mesh[:,k+nx+2]*(fx+fy-1)
landmarks={'left_hand':[185,1305],'right_hand':[980,1320],'left_shoulder':[365,565],'right_shoulder':[780,585],'waist':[543,1000],'chest':[543,700]}
def local(mesh):
 pts={k:point(mesh,v) for k,v in landmarks.items()};up=pts['chest']-pts['waist'];up/=np.linalg.norm(up,axis=1,keepdims=True);right=np.stack((-up[:,1],up[:,0]),axis=1)
 return {side:np.stack((np.sum((pts[side]-pts['waist'])*right,axis=1),np.sum((pts[side]-pts['waist'])*up,axis=1)),axis=1) for side in ['left_hand','right_hand']}
old,new=local(a),local(b);voiced=np.array([f['voice'] for f in plan['frames']]);delta=np.zeros(n);metrics={}
for side in old:
 diff=np.linalg.norm(new[side]-old[side],axis=1);delta=np.maximum(delta,diff)
 stats={}
 for name,data in [('v17',old[side]),('v18',new[side])]:
  span=np.ptp(data[voiced],axis=0);stats[name]={'voiced_axis_span_source_px':span.tolist(),'voiced_span_diagonal_source_px':float(np.linalg.norm(span)),'final_half_second_step_max_source_px':float(np.linalg.norm(np.diff(data[-15:],axis=0),axis=1).max())}
 stats['matched_frame_difference_max_source_px']=float(diff.max());stats['largest_difference_frame']=int(diff.argmax());metrics[side]=stats
picks=[0,48,468,653,1230,1259];peaks=[]
for lo,hi in [(15,270),(315,570),(615,870),(915,1170)]:peaks.append(int(lo+delta[lo:hi].argmax()))
picks+=peaks
picks=sorted(set(picks));plan['reviewFrameIndices']=picks;plan['gesturePeakFrameIndices']=peaks;plan['gestureWindowFrameIndices']=[48,1044];(D/'frames.json').write_text(json.dumps(plan))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(D/'timeline-audio.wav')==sha(O/'timeline-audio.wav')
oldp=json.loads((O/'source-provenance.json').read_text())['file_sha256'];newp=json.loads((D/'source-provenance.json').read_text())['file_sha256'];assert all(newp[k]==v for k,v in oldp.items() if k.startswith('runtime/model/')),'Approved face/art/model changed'
result={'method':'Fixed original-art landmark positions interpolated through actual mesh triangles; hands expressed in chest-to-waist torso coordinates to exclude simple global translation/rotation. Approximate artwork landmarks, not anatomical tracking.','landmarks_original_px':landmarks,'hand_motion':metrics,'review_frame_indices':picks,'same_audio_sha256':sha(D/'timeline-audio.wav'),'approved_v17_model_files_identical':True,'mesh_intentionally_changed':sha(D/'mesh.bin')!=sha(O/'mesh.bin')}
old_frames=json.loads((O/'frames.json').read_text())['frames'];face_keys=['ParamAngleX','ParamAngleY','ParamAngleZ','ParamEyeLOpen','ParamEyeROpen','ParamMouthOpenY']
face_equal={k:all(x['p'][k]==y['p'][k] for x,y in zip(old_frames,plan['frames'])) for k in face_keys};assert all(face_equal.values())
result['approved_face_parameter_timeline_identical']=face_equal
(D/'motion-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
