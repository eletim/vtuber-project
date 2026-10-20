function shader(gl,type,source) {
  const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
  if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));
  return s;
}
const vertex=`attribute vec2 a; varying vec2 uv; uniform vec2 size;
uniform vec3 angle; uniform float body; uniform float breath; uniform float clock;
void main(){
 uv=a; vec2 p=a*size;
 float head=1.0-smoothstep(410.0,610.0,p.y);
 vec2 q=p-vec2(540.,395.); float z=radians(angle.z)*head;
 p=vec2(cos(z)*q.x-sin(z)*q.y,sin(z)*q.x+cos(z)*q.y)+vec2(540.,395.);
 p.x+=angle.x*.65*head;
 p.y+=angle.y*.35*head;
 p.x+=(p.y-900.)*radians(body)*.25;
 p.y-=(breath-.5)*3.*(1.-smoothstep(450.,1250.,a.y*size.y));
 float hair=smoothstep(130.,280.,abs(a.x*size.x-540.))*(1.-smoothstep(650.,900.,a.y*size.y));
 p.x+=sin(clock*1.65+a.y*5.)*.65*hair;
 gl_Position=vec4(p.x/size.x*2.-1.,1.-p.y/size.y*2.,0.,1.);
}`;
const fragment=`precision mediump float; varying vec2 uv; uniform sampler2D tex;
void main(){gl_FragColor=texture2D(tex,uv);}`;

export class AvatarRenderer {
  async load(canvas) {
    this.canvas=canvas;
    this.model=await (await fetch('/model/model.json')).json();
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
    const vertices=[];
    for(let y=0;y<40;y++)for(let x=0;x<30;x++){
      const x0=x/30,x1=(x+1)/30,y0=y/40,y1=(y+1)/40;
      vertices.push(x0,y0,x1,y0,x0,y1,x1,y0,x1,y1,x0,y1);
    }
    this.count=vertices.length/2;
    gl.bindBuffer(gl.ARRAY_BUFFER,gl.createBuffer());gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);
    const at=gl.getAttribLocation(program,'a');gl.enableVertexAttribArray(at);gl.vertexAttribPointer(at,2,gl.FLOAT,false,0,0);
    gl.bindTexture(gl.TEXTURE_2D,gl.createTexture());
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    this.uniform=Object.fromEntries(['size','angle','body','breath','clock'].map(k=>[k,gl.getUniformLocation(program,k)]));
    gl.uniform2f(this.uniform.size,...this.model.size);
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
    const gl=this.gl,u=this.uniform;
    gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,this.paint);
    gl.uniform3f(u.angle,p.ParamAngleX,p.ParamAngleY,p.ParamAngleZ);
    gl.uniform1f(u.body,p.ParamBodyAngleX);gl.uniform1f(u.breath,p.ParamBreath);gl.uniform1f(u.clock,time);
    gl.drawArrays(gl.TRIANGLES,0,this.count);
    this.frames++;
  }
}
