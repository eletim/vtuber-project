// Actual browser / WebGL / Web Audio regression. Requires built v15 model assets.
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
import {mkdir,writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const output=resolve(root,'runtime/test-results/expressions');await mkdir(output,{recursive:true});
const port=Number(process.env.EXPRESSION_TEST_PORT||18770),base=`http://127.0.0.1:${port}`;
const server=spawn(process.env.PYTHON||'python',[resolve(root,'runtime/server.py'),'--port',String(port)],{cwd:root});
const ids=['neutral','soft_smile','big_smile','worried','surprised','bashful','displeased','thinking'];
const report={checks:[],errors:[],audio:'synthetic sine/silence fixture; not a live microphone or speech quality test'};
let browser;
const api=async(path,body)=>{const response=await fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});assert.equal(response.status,200,await response.clone().text());return response.json();};
function wavFixture(){
  const rate=24000,samples=rate*4,buffer=Buffer.alloc(44+samples*2);
  buffer.write('RIFF',0);buffer.writeUInt32LE(buffer.length-8,4);buffer.write('WAVEfmt ',8);
  buffer.writeUInt32LE(16,16);buffer.writeUInt16LE(1,20);buffer.writeUInt16LE(1,22);
  buffer.writeUInt32LE(rate,24);buffer.writeUInt32LE(rate*2,28);buffer.writeUInt16LE(2,32);buffer.writeUInt16LE(16,34);
  buffer.write('data',36);buffer.writeUInt32LE(samples*2,40);
  for(let i=0;i<samples;i++)buffer.writeInt16LE(Math.round(Math.sin(i/rate*Math.PI*2*330)*(i%rate<rate*.72?9000:0)),44+i*2);
  return buffer;
}
try{
  for(let i=0;i<100;i++){try{if((await fetch(base+'/api/state')).ok)break;}catch{}await new Promise(resolve=>setTimeout(resolve,100));}
  const manifest=await (await fetch(base+'/model/model.json')).json();
  assert.deepEqual(manifest.expressions.map(item=>item.id),ids,'build the v15 expressions before running this test');
  browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_PATH||undefined,args:['--no-sandbox','--enable-unsafe-swiftshader','--autoplay-policy=no-user-gesture-required']});
  const context=await browser.newContext({viewport:{width:1380,height:1100}}),page=await context.newPage();
  page.on('pageerror',error=>report.errors.push(error.message));
  await page.goto(base);await page.waitForFunction(()=>window.koma?.frames>8);
  await page.locator('#autoblink').uncheck();
  assert.equal(await page.locator('#expression option').count(),8);
  await api('/api/performance',{enabled:false});
  const original=await page.evaluate(()=>{
    const renderer=window.koma.renderer,pose={ParamEyeLOpen:1,ParamEyeROpen:1,ParamMouthOpenY:1,ParamAngleX:0,ParamAngleY:0,ParamAngleZ:0,ParamBodyAngleX:0,ParamBreath:.5};
    renderer.render(pose,0,'neutral');
    const expected=document.createElement('canvas');expected.width=renderer.paint.width;expected.height=renderer.paint.height;
    const ctx=expected.getContext('2d');ctx.drawImage(renderer.base,0,0);
    for(const part of renderer.parts)if(part.state==='open')ctx.drawImage(part.image,part.rect[0],part.rect[1]);
    const a=ctx.getImageData(0,0,expected.width,expected.height).data,b=renderer.ctx.getImageData(0,0,expected.width,expected.height).data;
    return a.every((value,index)=>value===b[index]);
  });
  assert.ok(original,'neutral open endpoint must retain exact original pixels');
  report.checks.push('neutral open endpoint is pixel-identical to original base + endpoint layers');
  await api('/api/mode',{mode:'ai'});await page.waitForFunction(()=>window.koma.mode==='ai');
  await api('/api/performance',{enabled:false});
  const images=new Set();
  for(const id of ids){
    await page.locator('#expression').selectOption(id);
    await page.waitForFunction(id=>window.koma.expressionFrame.id===id&&window.koma.expressionFrame.phase==='idle',id);
    for(const mouth of [0,1]){
      await api('/api/control',{source:'ai',parameters:{ParamEyeLOpen:1,ParamEyeROpen:1,ParamMouthOpenY:mouth}});
      await page.waitForFunction(mouth=>Math.abs(window.koma.current.ParamMouthOpenY-mouth)<.00001,mouth);
      const state=await page.evaluate(()=>({parts:window.koma.renderer.visibleParts,image:window.koma.renderer.paint.toDataURL()}));
      assert.equal(state.parts.length,3,`${id}: exactly one endpoint per eye/mouth`);
      assert.equal(new Set(state.parts.map(name=>name.replace(/\.(open|closed)$/,''))).size,3);
      if(mouth===1)images.add(state.image);
      await page.locator('#avatar').screenshot({path:resolve(output,`${id}_mouth_${mouth}.png`)});
    }
    const before=await page.evaluate(()=>window.koma.renderer.paint.toDataURL());
    await api('/api/control',{source:'ai',parameters:{ParamEyeLOpen:0,ParamEyeROpen:1}});
    await page.waitForFunction(()=>window.koma.current.ParamEyeLOpen<.01);
    const after=await page.evaluate(()=>window.koma.renderer.paint.toDataURL());
    assert.equal(before===after,id==='big_smile',`${id}: independent eye close, except intentionally closed smile`);
  }
  assert.equal(images.size,8,'all expression images should be distinct');
  report.checks.push('all eight expressions select/render; all mouths open/close; independent eye control and intentionally closed smile');
  const overlay=await context.newPage();await overlay.goto(base+'/?overlay=1');await overlay.waitForFunction(()=>window.koma?.frames>8);
  await page.evaluate(ids=>{for(let i=0;i<40;i++)window.koma.setExpression(ids[i%ids.length]);window.koma.setExpression('bashful');},ids);
  for(const view of [page,overlay])await view.waitForFunction(()=>window.koma.expressionFrame.id==='bashful'&&window.koma.expressionFrame.phase==='idle');
  await page.locator('#reset').click();
  for(const view of [page,overlay])await view.waitForFunction(()=>window.koma.expression.id==='neutral'&&window.koma.expressionFrame.phase==='idle');
  report.checks.push('rapid repeated picker commands settle to latest state in controller and overlay; reset returns neutral');
  await overlay.close();
  const fixture=resolve(output,'rms-fixture.wav');await writeFile(fixture,wavFixture());
  for(const id of ids){
    await page.locator('#expression').selectOption(id);
    await page.waitForFunction(id=>window.koma.expression.id===id,id);
    await page.locator('#audiofile').setInputFiles(fixture);
    await page.waitForFunction(id=>window.koma.expressionFrame.id===id&&window.koma.current.ParamMouthOpenY>.5,id);
    const opened=await page.evaluate(()=>window.koma.renderer.paint.toDataURL());
    await page.locator('#audio').evaluate(audio=>audio.pause());
    await page.waitForFunction(()=>window.koma.current.ParamMouthOpenY<.01);
    const closed=await page.evaluate(()=>window.koma.renderer.paint.toDataURL());
    assert.notEqual(opened,closed,`${id}: audible file RMS moves actual mouth drawing`);
  }
  report.checks.push('real Web Audio RMS opens all eight mouths, including closed-eye smile; pause closes every mouth');
  await api('/api/expression',{source:'ai',expression:'worried',duration:.2});
  await page.waitForFunction(()=>window.koma.expression.id==='neutral'&&window.koma.expressionFrame.phase==='idle');
  await page.locator('#expression').selectOption('displeased');await page.waitForFunction(()=>window.koma.expression.id==='displeased');
  await page.locator('#human').click();await page.waitForFunction(()=>window.koma.mode==='human'&&window.koma.expression.id==='neutral'&&window.koma.expressionFrame.phase==='idle');
  report.checks.push('bounded expression expiry and source-mode changes reliably return neutral');
  assert.deepEqual(report.errors,[]);report.status='PASS';
}catch(error){report.status='FAIL';report.failure=String(error);throw error;}
finally{await writeFile(resolve(output,'report.json'),JSON.stringify(report,null,2)+'\n');await browser?.close();server.kill();console.log(JSON.stringify(report,null,2));}
