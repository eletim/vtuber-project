// Minimal fragmented AVC MP4 muxer. One sample per fragment, exact 30 fps ticks.
const u=n=>{const b=Buffer.alloc(4);b.writeUInt32BE(n>>>0);return b};
const h=n=>{const b=Buffer.alloc(2);b.writeUInt16BE(n);return b};
const z=n=>Buffer.alloc(n),str=s=>Buffer.from(s),box=(name,...parts)=>{const b=Buffer.concat(parts);return Buffer.concat([u(b.length+8),str(name),b])};
const full=(name,flags,...parts)=>box(name,u(flags),...parts);
const matrix=Buffer.concat([u(65536),u(0),u(0),u(0),u(65536),u(0),u(0),u(0),u(0x40000000)]);
export function muxCfr({width,height,description,chunks,fps=30}){
 if(![10,30].includes(fps)||!chunks.length)throw Error('Expected nonempty 10fps or 30fps sequence');
 chunks=[...chunks].sort((a,b)=>a.timestamp-b.timestamp);
 for(let i=0;i<chunks.length;i++)if(chunks[i].timestamp!==Math.round(i*1e6/fps))throw Error('Missing or duplicate input timestamp '+i);
 const scale=30000,tick=scale/fps,duration=chunks.length*tick;
 const avc1=box('avc1',z(6),h(1),z(16),h(width),h(height),u(0x00480000),u(0x00480000),u(0),h(1),z(32),h(24),h(65535),box('avcC',description));
 const stbl=box('stbl',full('stsd',0,u(1),avc1),full('stts',0,u(0)),full('stsc',0,u(0)),full('stsz',0,u(0),u(0)),full('stco',0,u(0)));
 const minf=box('minf',full('vmhd',1,z(8)),box('dinf',full('dref',0,u(1),full('url ',1))),stbl);
 const mdia=box('mdia',full('mdhd',0,u(0),u(0),u(scale),u(duration),h(0x55c4),h(0)),full('hdlr',0,u(0),str('vide'),z(12),str('Koma CFR\0')),minf);
 const trak=box('trak',full('tkhd',7,u(0),u(0),u(1),u(0),u(duration),z(8),h(0),h(0),h(0),h(0),matrix,u(width*65536),u(height*65536)),mdia);
 const moov=box('moov',full('mvhd',0,u(0),u(0),u(scale),u(duration),u(65536),h(256),z(10),matrix,z(24),u(2)),trak,box('mvex',full('trex',0,u(1),u(1),u(tick),u(0),u(0))));
 const result=[box('ftyp',str('isom'),u(512),str('isomiso6avc1mp41')),moov];
 for(let i=0;i<chunks.length;i++){
  const c=chunks[i],data=c.data,tfhd=full('tfhd',0x20000,u(1)),tfdt=full('tfdt',0x1000000,u(0),u(i*tick));
  const make=offset=>box('moof',full('mfhd',0,u(i+1)),box('traf',tfhd,tfdt,full('trun',0x701,u(1),u(offset),u(tick),u(data.length),u(c.type==='key'?0x02000000:0x01010000))));
  const fragment=make(0);result.push(make(fragment.length+8),box('mdat',data));
 }
 return Buffer.concat(result);
}
