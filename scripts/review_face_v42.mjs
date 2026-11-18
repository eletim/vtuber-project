import {createRequire} from 'node:module';import {spawn,execFileSync} from 'node:child_process';import {mkdir,writeFile} from 'node:fs/promises';
const require=createRequire(import.meta.url),{chromium}=require(process.env.PLAYWRIGHT_MODULE),out='assets/parts/v42/face-review';await mkdir(out,{recursive:true});
const refs={v39:'58b73ac',v40:'b7a01cf',v41:'e3b7b78'},cache=new Map(),report={errors:[],poses:[]};let browser;
const server=spawn(process.env.PYTHON,['runtime/server.py','--port','18783'],{windowsHide:true});
try{
for(let i=0;i<100;i++){try{if((await fetch('http://127.0.0.1:18783/api/state')).ok)break}catch{}await new Promise(r=>setTimeout(r,100))}
browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH});const page=await browser.newPage();page.on('pageerror',e=>report.errors.push(e.message));
await page.route('**/face-review',r=>r.fulfill({contentType:'text/html',body:'<!doctype html>'}));
await page.route(/\/(v39|v40|v41)\/.*\.js$/,r=>{const [,v,name]=new URL(r.request().url()).pathname.split('/'),key=v+name;if(!cache.has(key))cache.set(key,execFileSync('git',['show',refs[v]+':runtime/web/'+name],{encoding:'utf8'}));return r.fulfill({contentType:'text/javascript',body:cache.get(key)})});
await page.goto('http://127.0.0.1:18783/face-review');
await page.evaluate(async()=>{window.rs=[];window.labels=['v39','v40','v41','v42'];const {neutral}=await import('/web/controls.js');window.neutral=neutral;
for(const v of ['v39','v40','v41','web']){const {AvatarRenderer}=await import('/'+v+'/renderer.js'),{BodyRig}=await import('/'+v+'/body-rig.js'),r=new AvatarRenderer(),c=document.createElement('canvas');c.width=1086;c.height=1448;await r.load(c);rs.push({r,BodyRig})}
window.shot=(x,y,expression,mouth)=>{const c=document.createElement('canvas');c.width=1680;c.height=470;const ctx=c.getContext('2d');ctx.fillStyle=mouth?'#397e91':'#fff';ctx.fillRect(0,0,c.width,c.height);
rs.forEach(({r,BodyRig},i)=>{r.rig=new BodyRig(r.model,{weights:r.rig.weights});const p={...neutral(),ParamAngleX:x,ParamAngleY:y,ParamMouthOpenY:mouth};r.render(p,0,expression,{ambient:false});r.render(p,1,expression,{ambient:false});ctx.drawImage(r.canvas,330,100,420,440,i*420,30,420,440);ctx.fillStyle=mouth?'white':'black';ctx.font='15px sans-serif';ctx.fillText(labels[i]+' x='+x+' y='+y+' '+expression+' mouth='+mouth,i*420+5,20)});return c.toDataURL().split(',')[1]};});
const full=process.env.FACE_FULL==='1';const expressions=full?['neutral','soft_smile','big_smile','worried','surprised','bashful','displeased','thinking']:['neutral'];
const angles=full?[[0,0],...[-15,-10,-5,5,10,15].map(x=>[x,0]),...[ -10,-5,5,10].map(y=>[0,y]),[-15,-10],[-15,10],[15,-10],[15,10]]:[[0,0],[-15,0],[15,0],[-15,-10],[15,10]];
for(const expression of expressions)for(const mouth of (full?[0,1]:[0]))for(const [x,y] of angles){const name=`${expression}-mouth${mouth}-x${x}-y${y}.png`,data=await page.evaluate(a=>shot(...a),[x,y,expression,mouth]);await writeFile(out+'/'+name,Buffer.from(data,'base64'));report.poses.push({name,x,y,expression,mouth});}console.log('face poses '+report.poses.length);
}catch(e){report.errors.push(e.stack);process.exitCode=1}finally{await browser?.close();server.kill();await writeFile(out+'/report.json',JSON.stringify(report,null,2));console.log(JSON.stringify({errors:report.errors,poses:report.poses.length}))}
