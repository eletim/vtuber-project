"""Synthetic cropped-layer alpha regression, using the exact offline layer shader."""
from layered_egl import *
D=Path(__file__).resolve().parent
program=layer_program();UseProgram(program);Uniform1i(GetUniformLocation(program,b'tex'),0);Uniform1i(GetUniformLocation(program,b'flipV'),0);rect=GetUniformLocation(program,b'rect')
BindFramebuffer(0x8D40,0);Viewport(0,0,AW,AH);MatrixMode(0x1701);LoadIdentity();Ortho(0,1,1,0,-1,1);MatrixMode(0x1700);LoadIdentity();Enable(0x0BE2);BlendFunc(1,0x0303);Enable(0x0DE1)
v=np.array([[0,0],[1,0],[0,1],[1,1]],np.float32);idx=np.array([0,1,2,1,3,2],np.uint16);EnableClient(0x8074);EnableClient(0x8078);VertexPointer(2,0x1406,0,v.ctypes.data);TexCoordPointer(2,0x1406,0,v.ctypes.data)
textures=[]
for color in [[255,0,0,128],[0,0,255,128]]:
 tid=U();GenTextures(1,C.byref(tid));BindTexture(0x0DE1,tid)
 for k,value in [(0x2801,0x2601),(0x2800,0x2601),(0x2802,0x812F),(0x2803,0x812F)]:TexParameteri(0x0DE1,k,value)
 a=np.array([[color]],np.uint8);a[:,:,:3]=np.rint(a[:,:,:3].astype(float)*a[:,:,3:4]/255).astype(np.uint8);TexImage2D(0x0DE1,0,0x1908,1,1,0,0x1908,0x1401,a.ctypes.data);textures.append(tid)
result={}
for name,bg in [('transparent',(0,0,0,0)),('white',(1,1,1,1)),('black',(0,0,0,1))]:
 ClearColor(*bg);Clear(0x4000)
 for tid,crop in zip(textures,[(0,0,1,1),(0,0,.5,1)]):
  BindTexture(0x0DE1,tid);Uniform4f(rect,*crop);DrawElements(0x0004,6,0x1403,idx.ctypes.data)
 Finish();p=np.zeros((AH,AW,4),np.uint8);ReadPixels(0,0,AW,AH,0x1908,0x1401,p.ctypes.data);assert GetError()==0
 result[name]={'overlap':p[600,225].tolist(),'red_only':p[600,675].tolist()}
 Image.fromarray(p[::-1]).resize((450,600)).save(D/f'alpha-regression-{name}.png')
expected={'transparent':{'overlap':[64,0,128,192],'red_only':[128,0,0,128]},'white':{'overlap':[127,63,191,255],'red_only':[255,127,127,255]},'black':{'overlap':[64,0,128,255],'red_only':[128,0,0,255]}}
for name,positions in expected.items():
 for position,pixel in positions.items():assert np.max(abs(np.array(result[name][position])-pixel))<=1,(name,position,result[name][position])
(D/'alpha-regression.json').write_text(json.dumps({'passed':True,'observed':result,'expected':expected,'method':'Real offline GL draw/readPixels. Two straight-RGBA inputs premultiplied once, ONE/ONE_MINUS_SRC_ALPHA, production crop/discard shader, separate draws. No browser claim.'},indent=2));print(json.dumps(result))
# A feature-layer FBO must not premultiply a second time at its later mesh draw.
fixture=D/'alpha-fixture';root=fixture/'source/runtime/model';root.mkdir(parents=True,exist_ok=True)
Image.new('RGBA',(100,100),(255,0,0,128)).save(root/'root.png');Image.new('RGBA',(50,100),(0,0,255,128)).save(root/'head.png')
(root/'model.json').write_text(json.dumps({'size':[100,100],'mesh':[1,1]}));(fixture/'mouth-frames.rgba').write_bytes(b'')
layers=[{'id':'bottom','role':'root','file':'root.png','rect':[0,0,100,100],'textureRect':[0,0,1,1]},{'id':'top','role':'head','file':'head.png','rect':[0,0,50,100],'textureRect':[0,0,.5,1],'features':True}]
(fixture/'frames.json').write_text(json.dumps({'roles':['root','head'],'layers':layers,'frames':[{'draw':[],'layerFiles':['root.png','head.png']}]}))
for role in ['root','head']:(fixture/f'mesh-{role}.bin').write_bytes(v.tobytes())
r=LayeredRenderer(fixture);output=r.render(0);a=np.array(output);sample={'overlap':a[600,225].tolist(),'red_only':a[600,675].tolist()};assert np.max(abs(np.array(sample['overlap'])-[85,0,170,192]))<=1;assert sample['red_only']==[255,0,0,128];output.save(D/'alpha-regression-head-fbo.png')
report=json.loads((D/'alpha-regression.json').read_text());report['head_FBO_straight_RGBA_samples']=sample;report['head_FBO_double_premultiply_test']='PASS';(D/'alpha-regression.json').write_text(json.dumps(report,indent=2));print('Head FBO parity PASS',sample)

r2=LayeredRenderer(fixture,2);a2=np.array(r2.render(0));assert np.max(abs(a2[600,225].astype(int)-[85,0,170,192]))<=1;assert a2[600,675].tolist()==[255,0,0,128]
report=json.loads((D/'alpha-regression.json').read_text());report['coverage_2x_head_FBO_test']='PASS';report['max_texture_and_renderbuffer_size']=r2.max_texture_size;(D/'alpha-regression.json').write_text(json.dumps(report,indent=2));print('Coverage2x FBO alpha PASS')
