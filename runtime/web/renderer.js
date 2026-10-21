import {BodyRig} from './body-rig.js';
import {ExpressionTransition,expressionParameters,featureOpening,deformMouthPixels} from './expressions.js';

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
    const loadParts=parts=>Promise.all(parts.map(async p=>({...p,image:await get(p.file)})));
    this.base=await get(this.model.base);
    this.parts=await loadParts(this.model.parts);
    this.expressions=new Map([['neutral',{id:'neutral',base:this.base,parts:this.parts,defaults:{}}]]);
    for(const expression of this.model.expressions||[]){
      this.expressions.set(expression.id,{...expression,base:expression.base?await get(expression.base):this.base,
        parts:expression.parts?await loadParts(expression.parts):this.parts});
    }
    // Decode once. Runtime and offline video share the same alpha-aware local
    // mouth deformation; no screen-aligned Canvas strip resizing remains.
    this.mouthPixels=new WeakMap();
    const readPixels=part=>{
      const patch=document.createElement('canvas');patch.width=part.image.width;patch.height=part.image.height;
      const context=patch.getContext('2d',{willReadFrequently:true});context.drawImage(part.image,0,0);
      return {pixels:context.getImageData(0,0,patch.width,patch.height).data,width:patch.width,height:patch.height,rect:part.rect,patch,context};
    };
    for(const expression of this.expressions.values()){
      const closed=expression.parts.find(part=>part.parameter==='ParamMouthOpenY'&&part.state==='closed');
      const shut=closed?readPixels(closed):null;
      for(const part of expression.parts)if(part.parameter==='ParamMouthOpenY'&&part.state==='open'){
        this.mouthPixels.set(part,{...readPixels(part),closed:shut});
      }
    }
    this.transition=new ExpressionTransition();
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
  drawPart(part,scale=1,expression='neutral') {
    const ctx=this.ctx,[x,y]=part.rect;
    const source=this.mouthPixels?.get(part);
    if(!source||!part.motion||scale>=.9999){ctx.drawImage(part.image,x,y);return;}
    const pixels=deformMouthPixels(source.pixels,source.width,source.height,part,scale,expression,source.closed);
    source.context.putImageData(new ImageData(pixels,source.width,source.height),0,0);
    ctx.drawImage(source.patch,x,y);
  }

  render(p,time=0,expression='neutral') {
    const requested=this.expressions.has(expression)?expression:'neutral';
    this.transition.request(requested,time);
    this.expressionFrame=this.transition.update(time);
    const active=this.expressions.get(this.expressionFrame.id);
    const pose=expressionParameters(p,active,this.expressionFrame.gate);
    const ctx=this.ctx;
    ctx.clearRect(0,0,this.paint.width,this.paint.height);ctx.globalAlpha=1;ctx.drawImage(active.base,0,0);
    this.visibleParts=[];
    for(const part of active.parts){
      const opening=featureOpening(pose[part.parameter],part.parameter.includes('Mouth'));
      if(part.state!==opening.state)continue;
      this.visibleParts.push(part.name);
      this.drawPart(part,opening.scale,active.id);
    }
    const gl=this.gl;
    gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,this.paint);
    gl.bindBuffer(gl.ARRAY_BUFFER,this.positionBuffer);gl.bufferSubData(gl.ARRAY_BUFFER,0,this.rig.frame(p,time));
    gl.drawElements(gl.TRIANGLES,this.count,gl.UNSIGNED_SHORT,0);
    this.frames++;
  }
}
