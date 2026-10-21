"""Offline adaptation of v19's ordered, cropped, independent WebGL layer draws.
Uses the runtime-exported role meshes, texture plan and exact mouth pixel output.
"""
from pathlib import Path
import ctypes as C,json,os
import numpy as np
from PIL import Image
from test_egl import G
AW,AH=int(os.getenv('KOMA_OUTPUT_WIDTH','900')),int(os.getenv('KOMA_OUTPUT_HEIGHT','1200'))
U=C.c_uint;I=C.c_int;P=C.c_void_p;F=C.c_float

def g(name,ret,*args):
 fn=getattr(G,name);fn.restype=ret;fn.argtypes=list(args);return fn
Viewport=g('glViewport',None,I,I,I,I);ClearColor=g('glClearColor',None,F,F,F,F);Clear=g('glClear',None,U)
Enable=g('glEnable',None,U);Disable=g('glDisable',None,U);BlendFunc=g('glBlendFunc',None,U,U)
MatrixMode=g('glMatrixMode',None,U);LoadIdentity=g('glLoadIdentity',None);Ortho=g('glOrtho',None,*([C.c_double]*6))
GenTextures=g('glGenTextures',None,I,C.POINTER(U));BindTexture=g('glBindTexture',None,U,U);TexParameteri=g('glTexParameteri',None,U,U,I)
TexImage2D=g('glTexImage2D',None,U,I,I,I,I,I,U,U,P)
EnableClient=g('glEnableClientState',None,U);VertexPointer=g('glVertexPointer',None,I,U,I,P);TexCoordPointer=g('glTexCoordPointer',None,I,U,I,P)
DrawElements=g('glDrawElements',None,U,I,U,P);ReadPixels=g('glReadPixels',None,I,I,I,I,U,U,P);Finish=g('glFinish',None);GetError=g('glGetError',U)
BindFramebuffer=g('glBindFramebuffer',None,U,U);GenFramebuffers=g('glGenFramebuffers',None,I,C.POINTER(U));FramebufferTexture2D=g('glFramebufferTexture2D',None,U,U,U,U,I);CheckFramebuffer=g('glCheckFramebufferStatus',U,U)
Begin=g('glBegin',None,U);End=g('glEnd',None);TexCoord=g('glTexCoord2d',None,C.c_double,C.c_double);Vertex=g('glVertex2d',None,C.c_double,C.c_double)
CreateShader=g('glCreateShader',U,U);ShaderSource=g('glShaderSource',None,U,I,C.POINTER(C.c_char_p),C.POINTER(I));CompileShader=g('glCompileShader',None,U);GetShaderiv=g('glGetShaderiv',None,U,U,C.POINTER(I));GetShaderInfoLog=g('glGetShaderInfoLog',None,U,I,C.POINTER(I),C.c_char_p)
CreateProgram=g('glCreateProgram',U);AttachShader=g('glAttachShader',None,U,U);LinkProgram=g('glLinkProgram',None,U);GetProgramiv=g('glGetProgramiv',None,U,U,C.POINTER(I));UseProgram=g('glUseProgram',None,U);GetUniformLocation=g('glGetUniformLocation',I,U,C.c_char_p);Uniform1i=g('glUniform1i',None,I,I);Uniform4f=g('glUniform4f',None,I,F,F,F,F)

def shader(kind,source):
 sh=CreateShader(kind);data=C.c_char_p(source.encode());ShaderSource(sh,1,C.byref(data),None);CompileShader(sh);ok=I();GetShaderiv(sh,0x8B81,C.byref(ok))
 if not ok.value:
  log=C.create_string_buffer(4096);GetShaderInfoLog(sh,4096,None,log);raise RuntimeError(log.value.decode())
 return sh

def layer_program():
 program=CreateProgram();AttachShader(program,shader(0x8B31,'#version 120\nvarying vec2 uv;void main(){uv=gl_MultiTexCoord0.xy;gl_Position=gl_ModelViewProjectionMatrix*gl_Vertex;}'))
 # Same local crop/discard and premultiplied sample math as renderer.js. The
 # flip uniform only accounts for native OpenGL FBO storage of the head canvas.
 AttachShader(program,shader(0x8B30,'#version 120\nvarying vec2 uv;uniform sampler2D tex;uniform vec4 rect;uniform int flipV;void main(){vec2 local=(uv-rect.xy)/rect.zw;if(local.x<0.||local.x>1.||local.y<0.||local.y>1.)discard;if(flipV==1)local.y=1.-local.y;gl_FragColor=texture2D(tex,local);}'));LinkProgram(program);ok=I();GetProgramiv(program,0x8B82,C.byref(ok));assert ok.value,'Layer shader link failed'
 return program

class LayeredRenderer:
 def __init__(self,directory,supersample=None):
  self.d=Path(directory);self.root=self.d/'source/runtime/model';self.plan=json.loads((self.d/'frames.json').read_text());self.model=json.loads((self.root/'model.json').read_text());self.layers=self.plan['layers'];assert self.layers and all(l['id']!='legacy' for l in self.layers)
  sampling=self.plan.get('sampling',{'enabled':False,'scale':1,'width':AW,'height':AH});self.supersample=sampling['scale'] if supersample is None else supersample;self.coverage=sampling['enabled'] if supersample is None else supersample!=1;self.scene_fbo=0;self.sw=sampling['width'] if supersample is None else AW*supersample;self.sh=sampling['height'] if supersample is None else AH*supersample
  nx,ny=self.model['mesh'];self.uv=np.array([(x/nx,y/ny) for y in range(ny+1) for x in range(nx+1)],np.float32);self.indices=np.array([v for y in range(ny) for x in range(nx) for v in (y*(nx+1)+x,y*(nx+1)+x+1,(y+1)*(nx+1)+x,y*(nx+1)+x+1,(y+1)*(nx+1)+x+1,(y+1)*(nx+1)+x)],np.uint16)
  self.mesh={r:np.memmap(self.d/f'mesh-{r}.bin',dtype=np.float32,mode='r',shape=(len(self.plan['frames']),len(self.uv),2)) for r in self.plan['roles']};self.textures={};self.mouth=open(self.d/'mouth-frames.rgba','rb')
  self.program=layer_program()
  UseProgram(self.program);Uniform1i(GetUniformLocation(self.program,b'tex'),0);self.rect_uniform=GetUniformLocation(self.program,b'rect');self.flip_uniform=GetUniformLocation(self.program,b'flipV')
  EnableClient(0x8074);EnableClient(0x8078);Enable(0x0DE1);Enable(0x0BE2);BlendFunc(1,0x0303)
  self.dynamic_mouth=self.new_texture();self.head_texture=self.new_texture();self.head=next(l for l in self.layers if l.get('features'));x0,y0,x1,y1=self.head['rect'];self.hw,self.hh=x1-x0,y1-y0
  BindTexture(0x0DE1,self.head_texture);TexImage2D(0x0DE1,0,0x1908,self.hw,self.hh,0,0x1908,0x1401,None)
  self.fbo=U();GenFramebuffers(1,C.byref(self.fbo));BindFramebuffer(0x8D40,self.fbo);FramebufferTexture2D(0x8D40,0x8CE0,0x0DE1,self.head_texture,0);assert CheckFramebuffer(0x8D40)==0x8CD5
  self.pixels=np.zeros((AH,AW,4),np.uint8)
  if self.coverage:
   getint=g('glGetIntegerv',None,U,C.POINTER(I));maximum=I();renderbuffer=I();getint(0x0D33,C.byref(maximum));getint(0x84E8,C.byref(renderbuffer));maximum.value=min(maximum.value,renderbuffer.value);assert max(self.sw,self.sh)<=maximum.value,'Supersampled target exceeds MAX_TEXTURE_SIZE';self.max_texture_size=maximum.value
   self.scene_texture=self.new_texture();TexImage2D(0x0DE1,0,0x1908,self.sw,self.sh,0,0x1908,0x1401,None);self.scene_fbo=U();GenFramebuffers(1,C.byref(self.scene_fbo));BindFramebuffer(0x8D40,self.scene_fbo);FramebufferTexture2D(0x8D40,0x8CE0,0x0DE1,self.scene_texture,0);assert CheckFramebuffer(0x8D40)==0x8CD5
 def new_texture(self):
  tid=U();GenTextures(1,C.byref(tid));BindTexture(0x0DE1,tid)
  for k,v in [(0x2801,0x2601),(0x2800,0x2601),(0x2802,0x812F),(0x2803,0x812F)]:TexParameteri(0x0DE1,k,v)
  return tid
 def premultiplied(self,rgba):
  a=rgba.copy();a[:,:,:3]=np.rint(a[:,:,:3].astype(np.float32)*a[:,:,3:4]/255).astype(np.uint8);return a
 def upload(self,file):
  if file not in self.textures:
   im=Image.open(self.root/file).convert('RGBA');a=self.premultiplied(np.array(im));tid=self.new_texture();TexImage2D(0x0DE1,0,0x1908,im.width,im.height,0,0x1908,0x1401,a.ctypes.data);self.textures[file]=(tid,im.size)
  return self.textures[file]
 def warped(self,part):
  self.mouth.seek(part['warp']['offset']);raw=self.mouth.read(part['warp']['length']);a=self.premultiplied(np.frombuffer(raw,np.uint8).reshape(part['height'],part['width'],4));BindTexture(0x0DE1,self.dynamic_mouth);TexImage2D(0x0DE1,0,0x1908,part['width'],part['height'],0,0x1908,0x1401,a.ctypes.data);return self.dynamic_mouth,(part['width'],part['height'])
 def quad(self,texture,x,y):
  tid,(w,h)=texture;BindTexture(0x0DE1,tid);Begin(0x0007)
  for u,v,px,py in [(0,0,x,y),(1,0,x+w,y),(1,1,x+w,y+h),(0,1,x,y+h)]:TexCoord(u,v);Vertex(px,py)
  End()
 def paint_head(self,state,file):
  UseProgram(0);BindFramebuffer(0x8D40,self.fbo);Viewport(0,0,self.hw,self.hh);MatrixMode(0x1701);LoadIdentity();Ortho(0,self.hw,self.hh,0,-1,1);MatrixMode(0x1700);LoadIdentity();ClearColor(0,0,0,0);Clear(0x4000);Enable(0x0BE2);BlendFunc(1,0x0303)
  self.quad(self.upload(file),0,0);ox,oy=self.head['rect'][:2]
  for part in state['draw']:self.quad(self.warped(part) if part.get('warp') else self.upload(part['file']),part['rect'][0]-ox,part['rect'][1]-oy)
 def scene_state(self):
  BindFramebuffer(0x8D40,self.scene_fbo);Viewport(0,0,self.sw,self.sh);MatrixMode(0x1701);LoadIdentity();Ortho(-.08,1.08,1.08,-.08,-1,1);MatrixMode(0x1700);LoadIdentity();UseProgram(self.program);Enable(0x0BE2);BlendFunc(1,0x0303);TexCoordPointer(2,0x1406,0,self.uv.ctypes.data)
 def render(self,index,only_roles=None):
  state=self.plan['frames'][index];self.scene_state();ClearColor(0,0,0,0);Clear(0x4000)
  for k,layer in enumerate(self.layers):
   if only_roles is not None and layer['role'] not in only_roles:continue
   if layer.get('features'):
    self.paint_head(state,state['layerFiles'][k]);self.scene_state();texture=self.head_texture;flip=1
   else:texture=self.upload(layer['file'])[0];flip=0
   BindTexture(0x0DE1,texture)
   if self.coverage:
    TexParameteri(0x0DE1,0x2801,0x2600);TexParameteri(0x0DE1,0x2800,0x2600)
   Uniform4f(self.rect_uniform,*layer['textureRect']);Uniform1i(self.flip_uniform,flip);v=self.mesh[layer['role']][index];VertexPointer(2,0x1406,0,v.ctypes.data);DrawElements(0x0004,len(self.indices),0x1403,self.indices.ctypes.data)
  if self.coverage:
   BindFramebuffer(0x8D40,0);Viewport(0,0,AW,AH);UseProgram(0);Disable(0x0BE2);MatrixMode(0x1701);LoadIdentity();Ortho(0,1,1,0,-1,1);MatrixMode(0x1700);LoadIdentity();BindTexture(0x0DE1,self.scene_texture);Begin(0x0007)
   for x,y,u,v in [(0,0,0,1),(1,0,1,1),(1,1,1,0),(0,1,0,0)]:TexCoord(u,v);Vertex(x,y)
   End()
  Finish();ReadPixels(0,0,AW,AH,0x1908,0x1401,self.pixels.ctypes.data);assert GetError()==0
  rgba=self.pixels[::-1].copy();alpha=rgba[:,:,3:4].astype(np.float32);rgba[:,:,:3]=np.clip(np.rint(rgba[:,:,:3].astype(np.float32)*255/np.maximum(alpha,1)),0,255).astype(np.uint8)
  return Image.fromarray(rgba,'RGBA')
