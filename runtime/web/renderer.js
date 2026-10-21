import {BodyRig} from './body-rig.js';

function shader(gl,type,source) {
  const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
  if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));
  return s;
}
const vertex=`attribute vec2 a; attribute vec2 position; varying vec2 uv;
void main(){
 uv=a; gl_Position=vec4(position.x*2.-1.,1.-position.y*2.,0.,1.);
}`;
const fragment=`precision mediump float; varying vec2 uv; uniform sampler2D tex;
void main(){gl_FragColor=texture2D(tex,uv);}`;

export class AvatarRenderer {
  async load(canvas) {
    this.canvas=canvas;
    this.model=await (await fetch('/model/model.json')).json();
    this.rig=new BodyRig(this.model,await (await fetch('/model/'+this.model.skinning)).json());
    this.paint=document.createElement('canvas');this.paint.width=this.model.size[0];this.paint.height=this.model.size[1];
    this.ctx=this.paint.getContext('2d');
    const get=async file=>{const im=new Image();im.src='/model/'+file;await im.decode();return im;};
    this.base=await get(this.model.base);
    this.parts=await Promise.all(this.model.parts.map(async p=>({...p,image:await get(p.file)})));
    const gl=this.gl=canvas.getContext('webgl',{alpha:true,premultipliedAlpha:false,antialias:true,preserveDrawingBuffer:true});
    if(!gl)throw Error('WebGLを利用できません。ブラウザのグラフィック設定を確認してください。');
    const program=this.program=gl.createProgram();
    gl.attachShader(program,shader(gl,gl.VERTEX_SHADER,vertex));gl.attachShader(program,shader(gl,gl.FRAGMENT_SHADER,fragment));gl.linkProgram(program);
    if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);
    const indices=[],[nx,ny]=this.model.mesh;
    for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){
      const a=y*(nx+1)+x,b=a+1,c=a+nx+1,d=c+1;
      indices.push(a,b,c,b,d,c);
    }
    this.count=indices.length;
    gl.bindBuffer(gl.ARRAY_BUFFER,gl.createBuffer());gl.bufferData(gl.ARRAY_BUFFER,this.rig.rest,gl.STATIC_DRAW);
    const at=gl.getAttribLocation(program,'a');gl.enableVertexAttribArray(at);gl.vertexAttribPointer(at,2,gl.FLOAT,false,0,0);
    this.positionBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,this.positionBuffer);
    gl.bufferData(gl.ARRAY_BUFFER,this.rig.rest,gl.DYNAMIC_DRAW);
    const position=gl.getAttribLocation(program,'position');gl.enableVertexAttribArray(position);gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,gl.createBuffer());gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(indices),gl.STATIC_DRAW);
    gl.bindTexture(gl.TEXTURE_2D,gl.createTexture());
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    this.frames=0;
  }
  render(p,time=0) {
    const ctx=this.ctx;
    ctx.clearRect(0,0,this.paint.width,this.paint.height);ctx.globalAlpha=1;ctx.drawImage(this.base,0,0);
    for(const part of this.parts){
      const value=p[part.parameter];
      // Existing art is two authored endpoints. Keep linework opaque rather
      // than crossfading two sets of lashes/lips into transparent ghost lines.
      const open=value >= (part.parameter.includes('Mouth')?.32:.4);
      ctx.globalAlpha=(part.state==='open')===open?1:0;
      ctx.drawImage(part.image,part.rect[0],part.rect[1]);
    }
    ctx.globalAlpha=1;
    const gl=this.gl;
    gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,this.paint);
    gl.bindBuffer(gl.ARRAY_BUFFER,this.positionBuffer);gl.bufferSubData(gl.ARRAY_BUFFER,0,this.rig.frame(p,time));
    gl.drawElements(gl.TRIANGLES,this.count,gl.UNSIGNED_SHORT,0);
    this.frames++;
  }
}
