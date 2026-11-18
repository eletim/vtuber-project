// Read the fragmented AVC MP4 emitted by our Chrome MediaRecorder.
// No third-party decoder/demuxer or installation is required.
export function samples(b){
 const u=(p)=>b.readUInt32BE(p),i=p=>b.readInt32BE(p);
 function boxes(start,end){const out=[];for(let p=start;p+8<=end;){let n=u(p),h=8;if(n===1){n=Number(b.readBigUInt64BE(p+8));h=16}if(!n)n=end-p;if(n<h||p+n>end)throw Error('invalid MP4 box');out.push({type:b.toString('ascii',p+4,p+8),p,start:p+h,end:p+n});p+=n}return out}
 const child=(box,t)=>boxes(box.start,box.end).find(x=>x.type===t),top=boxes(0,b.length),moov=top.find(x=>x.type==='moov'),trak=child(moov,'trak'),mdia=child(trak,'mdia'),mdhd=child(mdia,'mdhd'),timescale=u(mdhd.start+(b[mdhd.start]===1?20:12));
 const stsd=child(child(child(mdia,'minf'),'stbl'),'stsd'),avc=boxes(stsd.start+8,stsd.end).find(x=>x.type==='avc1'),config=boxes(avc.start+78,avc.end).find(x=>x.type==='avcC');
 const description=b.subarray(config.start,config.end),codec='avc1.'+description.subarray(1,4).toString('hex');
 const trex=child(child(moov,'mvex'),'trex');const defaults={duration:u(trex.start+12),size:u(trex.start+16),flags:u(trex.start+20)};
 const result=[];
 for(const moof of top.filter(x=>x.type==='moof'))for(const traf of boxes(moof.start,moof.end).filter(x=>x.type==='traf')){
  const tfhd=child(traf,'tfhd'),flags=u(tfhd.start)&0xffffff;let p=tfhd.start+8,base=moof.p,d={...defaults};
  if(flags&1){base=Number(b.readBigUInt64BE(p));p+=8}if(flags&2)p+=4;if(flags&8){d.duration=u(p);p+=4}if(flags&16){d.size=u(p);p+=4}if(flags&32)d.flags=u(p);
  const tfdt=child(traf,'tfdt');let time=b[tfdt.start]===1?Number(b.readBigUInt64BE(tfdt.start+4)):u(tfdt.start+4);
  for(const trun of boxes(traf.start,traf.end).filter(x=>x.type==='trun')){
   const f=u(trun.start)&0xffffff,count=u(trun.start+4);p=trun.start+8;let offset=base,first=d.flags;
   if(f&1){offset+=i(p);p+=4}if(f&4){first=u(p);p+=4}
   for(let k=0;k<count;k++){let duration=d.duration,size=d.size,sflags=k?d.flags:first,cto=0;if(f&256){duration=u(p);p+=4}if(f&512){size=u(p);p+=4}if(f&1024){sflags=u(p);p+=4}if(f&2048){cto=b[trun.start]===1?i(p):u(p);p+=4}if(!size||offset+size>b.length)throw Error('bad sample offset');result.push({offset,size,timestamp:Math.round((time+cto)*1e6/timescale),duration:Math.round(duration*1e6/timescale),type:sflags&0x10000?'delta':'key'});offset+=size;time+=duration}
  }
 }
 return {codec,description:description.toString('base64'),timescale,samples:result};
}
