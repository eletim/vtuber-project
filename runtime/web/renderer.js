import {BodyRig} from './body-rig.js';
import {bodyLayers,bodyTextureFile,bodyTextureRect,bodySamplingPlan} from './render-plan.js';
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
const resolveVertex=`attribute vec2 point; varying vec2 uv;
void main(){uv=point*.5+.5;gl_Position=vec4(point,0.,1.);}`;
const resolveFragment=`precision highp float; varying vec2 uv; uniform sampler2D tex;
void main(){gl_FragColor=texture2D(tex,uv);}`;
const fragment=`precision highp float; varying vec2 uv; uniform sampler2D tex; uniform vec4 rect;
void main(){
 vec2 local=(uv-rect.xy)/rect.zw;
 if(local.x<0.||local.x>1.||local.y<0.||local.y>1.)discard;
 gl_FragColor=texture2D(tex,local);
}`;

export class AvatarRenderer {
  async load(canvas) {
    this.canvas=canvas;
    this.model=await (await fetch('/model/model.json')).json();
    this.rig=new BodyRig(this.model,await (await fetch('/model/'+this.model.skinning)).json());
    const images=new Map();
    const get=async file=>{
      if(!images.has(file))images.set(file,(async()=>{const im=new Image();im.src='/model/'+file;await im.decode();return im;})());
      return images.get(file);
    };
    const loadParts=parts=>Promise.all(parts.map(async p=>({...p,image:await get(p.file)})));
    this.base=await get(this.model.base);
    this.parts=await loadParts(this.model.parts);
    this.expressions=new Map([['neutral',{id:'neutral',base:this.base,parts:this.parts,defaults:{}}]]);
    for(const expression of this.model.expressions||[]){
      this.expressions.set(expression.id,{...expression,base:expression.base?await get(expression.base):this.base,
        parts:expression.parts?await loadParts(expression.parts):this.parts});
    }
    // The accepted v17 face/eye/mouth images and local mouth helper remain
    // unchanged. Only their containing head texture is now independently drawn.
    this.mouthPixels=new WeakMap();
    const readPixels=part=>{
      const patch=document.createElement('canvas');patch.width=part.image.width;patch.height=part.image.height;
      const context=patch.getContext('2d',{willReadFrequently:true});context.drawImage(part.image,0,0);
      return {pixels:context.getImageData(0,0,patch.width,patch.height).data,width:patch.width,height:patch.height,rect:part.rect,patch,context};
    };
    for(const expression of this.expressions.values()){
      const closed=expression.parts.find(part=>part.parameter==='ParamMouthOpenY'&&part.state==='closed');
      const shut=closed?readPixels(closed):null;
      for(const part of expression.parts)if(part.parameter==='ParamMouthOpenY'&&part.state==='open')this.mouthPixels.set(part,{...readPixels(part),closed:shut});
    }
    this.transition=new ExpressionTransition();
    const gl=this.gl=canvas.getContext('webgl',{alpha:true,premultipliedAlpha:true,antialias:true,preserveDrawingBuffer:true});
    if(!gl)throw Error('WebGLを利用できません。ブラウザのグラフィック設定を確認してください。');
    const program=this.program=gl.createProgram();
    gl.attachShader(program,shader(gl,gl.VERTEX_SHADER,vertex));gl.attachShader(program,shader(gl,gl.FRAGMENT_SHADER,fragment));gl.linkProgram(program);
    if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);
    const indices=[],[nx,ny]=this.model.mesh;
    for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){
      const a=y*(nx+1)+x,b=a+1,c=a+nx+1,d=c+1;indices.push(a,b,c,b,d,c);
    }
    this.count=indices.length;
    this.uvBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,this.uvBuffer);gl.bufferData(gl.ARRAY_BUFFER,this.rig.rest,gl.STATIC_DRAW);
    this.uvAttribute=gl.getAttribLocation(program,'a');gl.enableVertexAttribArray(this.uvAttribute);gl.vertexAttribPointer(this.uvAttribute,2,gl.FLOAT,false,0,0);
    this.positionAttribute=gl.getAttribLocation(program,'position');gl.enableVertexAttribArray(this.positionAttribute);
    this.rectUniform=gl.getUniformLocation(program,'rect');
    this.indexBuffer=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,this.indexBuffer);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,new Uint16Array(indices),gl.STATIC_DRAW);
    gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,true);
    this.sampling=bodySamplingPlan(this.model,canvas.width,canvas.height,Math.min(gl.getParameter(gl.MAX_TEXTURE_SIZE),gl.getParameter(gl.MAX_RENDERBUFFER_SIZE),...gl.getParameter(gl.MAX_VIEWPORT_DIMS)));
    this.layers=[];
    for(const definition of bodyLayers(this.model)){
      const layer={...definition,images:new Map(),positionBuffer:gl.createBuffer(),texture:gl.createTexture()};
      gl.bindBuffer(gl.ARRAY_BUFFER,layer.positionBuffer);gl.bufferData(gl.ARRAY_BUFFER,this.rig.rest,gl.DYNAMIC_DRAW);
      // For legacy manifests, preserve their original complete expression bases.
      for(const expression of this.model.expressions||[{id:'neutral',base:this.model.base}]){
        const file=bodyTextureFile(definition,expression,this.model);layer.images.set(expression.id,await get(file));
      }
      layer.image=await get(definition.file);
      const [x0,y0,x1,y1]=definition.rect;
      for(const image of [layer.image,...layer.images.values()])if(image.width!==x1-x0||image.height!==y1-y0)throw Error(`body texture size mismatch: ${layer.id}`);
      if(layer.features){
        layer.paint=document.createElement('canvas');layer.paint.width=x1-x0;layer.paint.height=y1-y0;
        layer.ctx=layer.paint.getContext('2d');this.paint=layer.paint;this.ctx=layer.ctx;
      }
      gl.bindTexture(gl.TEXTURE_2D,layer.texture);
      const filter=this.sampling.enabled?gl.NEAREST:gl.LINEAR;
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,filter);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,filter);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
      if(!layer.features)gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,layer.image);
      this.layers.push(layer);
    }
    if(this.sampling.enabled){
      this.resolveTexture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,this.resolveTexture);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
      this.resolveFramebuffer=gl.createFramebuffer();gl.bindFramebuffer(gl.FRAMEBUFFER,this.resolveFramebuffer);
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,this.sampling.width,this.sampling.height,0,gl.RGBA,gl.UNSIGNED_BYTE,null);
      gl.framebufferTexture2D(gl.FRAMEBUFFER,gl.COLOR_ATTACHMENT0,gl.TEXTURE_2D,this.resolveTexture,0);
      if(gl.checkFramebufferStatus(gl.FRAMEBUFFER)!==gl.FRAMEBUFFER_COMPLETE)throw Error('パーツ合成用の描画領域を作成できません。');
      gl.bindFramebuffer(gl.FRAMEBUFFER,null);
      this.resolveProgram=gl.createProgram();
      gl.attachShader(this.resolveProgram,shader(gl,gl.VERTEX_SHADER,resolveVertex));gl.attachShader(this.resolveProgram,shader(gl,gl.FRAGMENT_SHADER,resolveFragment));gl.linkProgram(this.resolveProgram);
      if(!gl.getProgramParameter(this.resolveProgram,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(this.resolveProgram));
      this.resolveAttribute=gl.getAttribLocation(this.resolveProgram,'point');
      this.resolveBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,this.resolveBuffer);
      gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
    }
    this.frames=0;
  }
  drawPart(part,scale=1,expression='neutral',ctx=this.ctx) {
    const [x,y]=part.rect,source=this.mouthPixels?.get(part);
    if(!source||!part.motion||scale>=.9999){ctx.drawImage(part.image,x,y);return;}
    const pixels=deformMouthPixels(source.pixels,source.width,source.height,part,scale,expression,source.closed);
    source.context.putImageData(new ImageData(pixels,source.width,source.height),0,0);
    ctx.drawImage(source.patch,x,y);
  }
  render(p,time=0,expression='neutral',options={}) {
    const requested=this.expressions.has(expression)?expression:'neutral';
    this.transition.request(requested,time);this.expressionFrame=this.transition.update(time);
    const active=this.expressions.get(this.expressionFrame.id),pose=expressionParameters(p,active,this.expressionFrame.gate);
    const visible=active.parts.map(part=>({part,opening:featureOpening(pose[part.parameter],part.parameter.includes('Mouth'))})).filter(({part,opening})=>part.state===opening.state);
    this.visibleParts=visible.map(({part})=>part.name);
    const positions=this.rig.frames(p,time,options),gl=this.gl;
    gl.useProgram(this.program);
    if(this.uvBuffer){
      gl.bindBuffer(gl.ARRAY_BUFFER,this.uvBuffer);gl.enableVertexAttribArray(this.uvAttribute);gl.vertexAttribPointer(this.uvAttribute,2,gl.FLOAT,false,0,0);
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,this.indexBuffer);gl.enableVertexAttribArray(this.positionAttribute);
    }
    gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE_MINUS_SRC_ALPHA);
    gl.bindFramebuffer(gl.FRAMEBUFFER,this.resolveFramebuffer||null);
    gl.viewport(0,0,this.sampling?.width||this.canvas.width,this.sampling?.height||this.canvas.height);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);
    this.lastDraws=[];
    for(const layer of this.layers){
      if(options.onlyRoles&&!options.onlyRoles.includes(layer.role))continue;
      gl.bindTexture(gl.TEXTURE_2D,layer.texture);
      if(layer.features){
        const ctx=layer.ctx;ctx.globalAlpha=1;ctx.clearRect(0,0,layer.paint.width,layer.paint.height);
        ctx.drawImage(layer.images.get(active.id)||layer.image,0,0);
        ctx.save();ctx.translate(-layer.rect[0],-layer.rect[1]);
        for(const {part,opening} of visible)this.drawPart(part,opening.scale,active.id,ctx);
        ctx.restore();gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,layer.paint);
      }
      gl.uniform4fv(this.rectUniform,bodyTextureRect(layer,this.model));
      gl.bindBuffer(gl.ARRAY_BUFFER,layer.positionBuffer);gl.bufferSubData(gl.ARRAY_BUFFER,0,positions[layer.role]);
      gl.vertexAttribPointer(this.positionAttribute,2,gl.FLOAT,false,0,0);
      gl.drawElements(gl.TRIANGLES,this.count,gl.UNSIGNED_SHORT,0);
      this.lastDraws.push({id:layer.id,role:layer.role,vertices:positions[layer.role].length/2});
    }
    if(this.resolveFramebuffer){
      gl.bindFramebuffer(gl.FRAMEBUFFER,null);gl.viewport(0,0,this.canvas.width,this.canvas.height);
      gl.clear(gl.COLOR_BUFFER_BIT);gl.disable(gl.BLEND);gl.useProgram(this.resolveProgram);
      gl.disableVertexAttribArray(this.uvAttribute);gl.disableVertexAttribArray(this.positionAttribute);
      gl.bindBuffer(gl.ARRAY_BUFFER,this.resolveBuffer);gl.enableVertexAttribArray(this.resolveAttribute);
      gl.vertexAttribPointer(this.resolveAttribute,2,gl.FLOAT,false,0,0);
      gl.bindTexture(gl.TEXTURE_2D,this.resolveTexture);gl.drawArrays(gl.TRIANGLES,0,6);
      gl.disableVertexAttribArray(this.resolveAttribute);
    }
    this.frames++;
  }
}
