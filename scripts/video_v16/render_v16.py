from pathlib import Path
import ctypes as C, json, itertools, subprocess, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from test_egl import G
D=Path(__file__).resolve().parent; R=D/'source/runtime'
W,H=1600,1080; AW,AH=756,1008
plan=json.loads((D/'frames.json').read_text());FPS=plan['fps'];DURATION=plan['duration']
model=json.loads((R/'model/model.json').read_text()); poses=plan['frames']
mesh=np.fromfile(D/'mesh.bin',dtype=np.float32).reshape(len(poses),-1,2)

def g(name,ret,*args):
 f=getattr(G,name);f.restype=ret;f.argtypes=list(args);return f
void=None; uint=C.c_uint; integer=C.c_int; enum=C.c_uint; ptr=C.c_void_p; f32=C.c_float
Viewport=g('glViewport',void,integer,integer,integer,integer)
ClearColor=g('glClearColor',void,f32,f32,f32,f32);Clear=g('glClear',void,uint)
Enable=g('glEnable',void,enum);Disable=g('glDisable',void,enum)
MatrixMode=g('glMatrixMode',void,enum);LoadIdentity=g('glLoadIdentity',void)
Ortho=g('glOrtho',void,*([C.c_double]*6))
GenTextures=g('glGenTextures',void,integer,C.POINTER(uint));BindTexture=g('glBindTexture',void,enum,uint)
TexParameteri=g('glTexParameteri',void,enum,enum,integer)
TexImage2D=g('glTexImage2D',void,enum,integer,integer,integer,integer,integer,enum,enum,ptr)
EnableClient=g('glEnableClientState',void,enum)
VertexPointer=g('glVertexPointer',void,integer,enum,integer,ptr)
TexCoordPointer=g('glTexCoordPointer',void,integer,enum,integer,ptr)
DrawElements=g('glDrawElements',void,enum,integer,enum,ptr)
ReadPixels=g('glReadPixels',void,integer,integer,integer,integer,enum,enum,ptr)
Finish=g('glFinish',void);GetError=g('glGetError',enum)
Viewport(0,0,AW,AH);ClearColor(0,0,0,0);Disable(0x0BE2);Enable(0x0DE1)
MatrixMode(0x1701);LoadIdentity();Ortho(0,1,1,0,-1,1);MatrixMode(0x1700);LoadIdentity()
nx,ny=model['mesh'];uv=np.array([(x/nx,y/ny) for y in range(ny+1) for x in range(nx+1)],dtype=np.float32)
indices=np.array([v for y in range(ny) for x in range(nx) for v in (y*(nx+1)+x,y*(nx+1)+x+1,(y+1)*(nx+1)+x,y*(nx+1)+x+1,(y+1)*(nx+1)+x+1,(y+1)*(nx+1)+x)],dtype=np.uint16)
EnableClient(0x8074);EnableClient(0x8078);TexCoordPointer(2,0x1406,0,uv.ctypes.data)

# Premultiplied source-over FBO matches canvas 2D compositing, with exact float strip bounds
# exported by the actual runtime featureBands helper. No offline approximation of those bands.
BindFramebuffer=g('glBindFramebuffer',void,enum,uint)
GenFramebuffers=g('glGenFramebuffers',void,integer,C.POINTER(uint))
FramebufferTexture2D=g('glFramebufferTexture2D',void,enum,enum,enum,uint,integer)
CheckFramebuffer=g('glCheckFramebufferStatus',enum,enum)
BlendFunc=g('glBlendFunc',void,enum,enum)
Begin=g('glBegin',void,enum);End=g('glEnd',void)
TexCoord=g('glTexCoord2d',void,C.c_double,C.c_double);Vertex=g('glVertex2d',void,C.c_double,C.c_double)
textures={}
def upload(file):
 if file not in textures:
  im=Image.open(R/'model'/file).convert('RGBA');a=np.array(im);a[:,:,:3]=np.rint(a[:,:,:3].astype(np.float32)*a[:,:,3:4]/255).astype(np.uint8)
  tid=uint();GenTextures(1,C.byref(tid));BindTexture(0x0DE1,tid)
  for key,val in [(0x2801,0x2601),(0x2800,0x2601),(0x2802,0x812F),(0x2803,0x812F)]:TexParameteri(0x0DE1,key,val)
  TexImage2D(0x0DE1,0,0x1908,*im.size,0,0x1908,0x1401,a.ctypes.data);textures[file]=(tid,im.size)
 return textures[file]
for state in poses:
 upload(state['base'])
 for part in state['draw']:upload(part['file'])
MW,MH=model['size'];paint=uint();GenTextures(1,C.byref(paint));BindTexture(0x0DE1,paint)
for key,val in [(0x2801,0x2601),(0x2800,0x2601),(0x2802,0x812F),(0x2803,0x812F)]:TexParameteri(0x0DE1,key,val)
TexImage2D(0x0DE1,0,0x1908,MW,MH,0,0x1908,0x1401,None)
fbo=uint();GenFramebuffers(1,C.byref(fbo));BindFramebuffer(0x8D40,fbo);FramebufferTexture2D(0x8D40,0x8CE0,0x0DE1,paint,0);assert CheckFramebuffer(0x8D40)==0x8CD5
# FBO image origin is bottom-left; source PNG uploads and JS UVs are top-left.
framebuffer_uv=uv.copy();framebuffer_uv[:,1]=1-framebuffer_uv[:,1]
def quad(file,source,destination,texture=None):
 tid,(w,h)=texture if texture is not None else textures[file];BindTexture(0x0DE1,tid);sx,sy,sw,sh=source;dx,dy,dw,dh=destination
 if sw<=0 or sh<=0 or dw<=0 or dh<=0:return
 Begin(0x0007)
 for u,v,x,y in [(sx/w,sy/h,dx,dy),((sx+sw)/w,sy/h,dx+dw,dy),((sx+sw)/w,(sy+sh)/h,dx+dw,dy+dh),(sx/w,(sy+sh)/h,dx,dy+dh)]:TexCoord(u,v);Vertex(x,y)
 End()
dynamic_mouth=uint();GenTextures(1,C.byref(dynamic_mouth));BindTexture(0x0DE1,dynamic_mouth)
for key,val in [(0x2801,0x2601),(0x2800,0x2601),(0x2802,0x812F),(0x2803,0x812F)]:TexParameteri(0x0DE1,key,val)
mouth_frames=open(D/'mouth-frames.rgba','rb')
def upload_warp(part):
 mouth_frames.seek(part['warp']['offset']);raw=mouth_frames.read(part['warp']['length']);assert len(raw)==part['width']*part['height']*4
 a=np.frombuffer(raw,np.uint8).reshape(part['height'],part['width'],4).copy();a[:,:,:3]=np.rint(a[:,:,:3].astype(np.float32)*a[:,:,3:4]/255).astype(np.uint8)
 BindTexture(0x0DE1,dynamic_mouth);TexImage2D(0x0DE1,0,0x1908,part['width'],part['height'],0,0x1908,0x1401,a.ctypes.data)
 return dynamic_mouth,(part['width'],part['height'])
def composite(state):
 BindFramebuffer(0x8D40,fbo);Viewport(0,0,MW,MH);MatrixMode(0x1701);LoadIdentity();Ortho(0,MW,MH,0,-1,1);MatrixMode(0x1700);LoadIdentity()
 ClearColor(0,0,0,0);Clear(0x4000);Enable(0x0BE2);BlendFunc(1,0x0303)
 quad(state['base'],(0,0,MW,MH),(0,0,MW,MH))
 for p in state['draw']:
  x,y=p['rect'][:2];w,h=p['width'],p['height'];b=p['bands']
  if p.get('warp'):quad(p['file'],(0,0,w,h),(x,y,w,h),upload_warp(p));continue
  if not b:quad(p['file'],(0,0,w,h),(x,y,w,h));continue
  x0,x1=b['x0'],b['x1'];src,dst=b['source'],b['destination']
  if x0>0:quad(p['file'],(0,0,x0,h),(x,y,x0,h))
  if x1<w:quad(p['file'],(x1,0,w-x1,h),(x+x1,y,w-x1,h))
  for j in range(len(src)-1):quad(p['file'],(x0,src[j],x1-x0,src[j+1]-src[j]),(x+x0,y+dst[j],x1-x0,dst[j+1]-dst[j]))
 BindFramebuffer(0x8D40,0);Viewport(0,0,AW,AH);Disable(0x0BE2);MatrixMode(0x1701);LoadIdentity();Ortho(0,1,1,0,-1,1);MatrixMode(0x1700);LoadIdentity()
 BindTexture(0x0DE1,paint);TexCoordPointer(2,0x1406,0,framebuffer_uv.ctypes.data)
pixels=np.zeros((AH,AW,4),np.uint8)
fontfile='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc';boldfile='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
def font(size,bold=False):return ImageFont.truetype(boldfile if bold else fontfile,size,index=0)
F={s:font(s) for s in [16,18,20,21,22,24,26,28,30,34,36]};FB={s:font(s,True) for s in [18,20,22,24,28,30,36,40,44]}
y,x=np.mgrid[0:H,0:W];rad=np.clip(np.sqrt(((x-460)/900)**2+((y-400)/1100)**2),0,1)
colors=np.stack([252-14*rad,247-20*rad,237-27*rad],axis=2).astype(np.uint8)
background=Image.fromarray(colors).convert('RGBA');b=ImageDraw.Draw(background)
b.rounded_rectangle((835,38,1564,1042),radius=24,fill=(255,252,247,245),outline='#ded1be',width=2)
b.text((873,65),'KOMA / MOUTH MOTION CHECK',font=F[20],fill='#99794f')
b.text((871,101),'羽月こま',font=FB[44],fill='#45372e')
b.text((873,168),'口の向き・輪郭の修正確認',font=F[28],fill='#786553')
b.text((873,216),'v16  ·  2026.10.21  ·  42秒',font=F[20],fill='#97846f')
b.line((873,263,1524,263),fill='#ded1be',width=2)
b.text((873,387),'8つの表情',font=FB[22],fill='#6a5139')
labels=['通常','微笑み','にっこり','困り顔','驚き','照れ','不満','考え顔']
for j,label in enumerate(labels):b.text((906,435+j*40),f'{j+1:02d}  {label}',font=F[21],fill='#91806c')
b.text((1144,387),'顔の動き',font=FB[22],fill='#6a5139')
b.rounded_rectangle((1136,428,1524,788),radius=12,outline='#ded1be',width=2)
b.line((873,815,1524,815),fill='#ded1be',width=2)
b.text((873,834),'音声：VOICEVOX:雨晴はう',font=FB[20],fill='#71563c')
b.text((873,874),'保存済み音声を再使用。新しいセリフではありません。',font=F[20],fill='#846b54')
b.text((873,913),'現行コードによる再描画。操作画面の録画ではありません。',font=F[20],fill='#846b54')
b.text((873,956),'未修正：太ももの抜け・髪のマット',font=F[20],fill='#9b653e')
b.text((873,990),'目は開閉2状態、口・体は連続変形。Cubism形式ではありません。',font=F[16],fill='#9c8673')
cmd=['ffmpeg','-v','warning','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{W}x{H}','-framerate',str(FPS),'-i','pipe:0','-i',str(D/'timeline-audio.wav'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-t',str(DURATION),'-movflags','+faststart',str(D/'koma-v16-mouth-motion.mp4')]
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
frames_dir=D/'verified-frames';frames_dir.mkdir(exist_ok=True)
# Each expression has one steady speaking, one independent blink, and one transition sample.
shot_at={int((slot*5+.8)*FPS):f'{slot+1:02d}-{plan["ids"][slot]}-speaking' for slot in range(8)}
shot_at.update({int((slot*5+1.3)*FPS):f'{slot+1:02d}-{plan["ids"][slot]}-blink' for slot in range(8)})
shot_at.update({int((slot*5+.2)*FPS):f'{slot+1:02d}-{plan["ids"][slot]}-transition' for slot in range(1,8)})
shot_at[41*FPS]='return-idle'
for i,s in enumerate(poses):
 composite(s);Clear(0x4000);v=mesh[i];VertexPointer(2,0x1406,0,v.ctypes.data)
 DrawElements(0x0004,len(indices),0x1403,indices.ctypes.data);Finish();ReadPixels(0,0,AW,AH,0x1908,0x1401,pixels.ctypes.data)
 err=GetError();assert err==0,hex(err)
 rgba=pixels[::-1].copy();alpha=rgba[:,:,3:4].astype(np.float32)
 rgba[:,:,:3]=np.clip(np.rint(rgba[:,:,:3].astype(np.float32)*255/np.maximum(alpha,1)),0,255).astype(np.uint8)
 avatar=Image.fromarray(rgba,'RGBA');frame=background.copy();frame.alpha_composite(avatar,(42,35));d=ImageDraw.Draw(frame)
 index=plan['ids'].index(s['requested']); title=(f'{index+1:02d} / 08  '+s['label']) if s['t']<40 else '通常へ戻る'
 d.text((873,281),title,font=FB[36],fill='#704c2d')
 phase={'idle':'表情キープ','closing':'まばたきで切替中','hold':'まばたきで切替中','opening':'まばたきで切替中'}[s['expressionFrame']['phase']]
 d.text((873,339),phase,font=F[20],fill='#97846f')
 d.text((1300,339),f"{s['t']:05.2f} / {DURATION:.2f} 秒",font=F[20],fill='#97846f')
 d.rectangle((900,434+index*40,1128,474+index*40),fill='#fffcf7');d.ellipse((875,445+index*40,889,459+index*40),fill='#a67743');d.text((906,435+index*40),f'{index+1:02d}  {labels[index]}',font=FB[22],fill='#6f4c2e')
 # A crop of the SAME deformed frame, not an independent or idealized face render.
 zoom=frame.crop((225,103,555,409)).resize((384,356),Image.Resampling.LANCZOS);frame.paste(zoom,(1138,430));d=ImageDraw.Draw(frame)
 mouth=s['p']['ParamMouthOpenY'];d.text((873,765),'音量',font=F[18],fill='#9a8067');d.rounded_rectangle((935,779,1099,789),radius=5,fill='#ece3d6')
 if mouth>.01:d.rounded_rectangle((935,779,935+max(10,164*mouth),789),radius=5,fill='#bb8c53')
 d.rounded_rectangle((42,1057,1564,1063),radius=3,fill='#e0d2be')
 if i:d.rounded_rectangle((42,1057,42+(1522*i/(len(poses)-1)),1063),radius=3,fill='#aa7a42')
 if i in shot_at:frame.convert('RGB').save(frames_dir/f'{i:04d}-{shot_at[i]}.png')
 proc.stdin.write(frame.convert('RGB').tobytes())
 if i%150==0:print(f'Rendered {i}/{len(poses)} expression frames',flush=True)
proc.stdin.close();assert proc.wait()==0
print('VIDEO COMPLETE',D/'koma-v16-mouth-motion.mp4',flush=True)
