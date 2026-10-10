import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
export function decodeBc3(data,width,height){
 assert(width%4===0&&height%4===0);assert(data.length>=width*height);const pixels=Buffer.alloc(width*height*4);
 const rgb565=n=>{const r=(n>>>11)&31,g=(n>>>5)&63,b=n&31;return [(r<<3)|(r>>>2),(g<<2)|(g>>>4),(b<<3)|(b>>>2)];};
 let pos=0;for(let by=0;by<height;by+=4)for(let bx=0;bx<width;bx+=4){
  const a0=data[pos],a1=data[pos+1],alpha=[a0,a1];if(a0>a1)for(let j=1;j<=6;j++)alpha.push(Math.floor(((7-j)*a0+j*a1)/7));else{for(let j=1;j<=4;j++)alpha.push(Math.floor(((5-j)*a0+j*a1)/5));alpha.push(0,255);}
  let abits=0n;for(let j=0;j<6;j++)abits|=BigInt(data[pos+2+j])<<BigInt(j*8);
  const c0=rgb565(data.readUInt16LE(pos+8)),c1=rgb565(data.readUInt16LE(pos+10)),colors=[c0,c1,c0.map((v,j)=>Math.floor((2*v+c1[j])/3)),c0.map((v,j)=>Math.floor((v+2*c1[j])/3))],bits=data.readUInt32LE(pos+12);
  for(let k=0;k<16;k++){const color=colors[(bits>>>(k*2))&3],a=alpha[Number((abits>>BigInt(k*3))&7n)],p=((by+(k>>>2))*width+bx+(k&3))*4;pixels[p]=color[0];pixels[p+1]=color[1];pixels[p+2]=color[2];pixels[p+3]=a;}pos+=16;
 }return {width,height,pixels};
}
function fixture(alpha0,alpha1,index){const b=Buffer.alloc(16);b[0]=alpha0;b[1]=alpha1;b.writeUInt16LE(0xffff,8);let bits=0n;for(let k=0;k<16;k++)bits|=BigInt(index)<<BigInt(k*3);for(let j=0;j<6;j++)b[2+j]=Number((bits>>BigInt(j*8))&255n);return b;}
assert.deepEqual([...decodeBc3(fixture(255,0,0),4,4).pixels.subarray(0,4)],[255,255,255,255]);
assert.equal(decodeBc3(fixture(255,0,2),4,4).pixels[3],218);
assert.equal(decodeBc3(fixture(0,255,6),4,4).pixels[3],0);assert.equal(decodeBc3(fixture(0,255,7),4,4).pixels[3],255);
const baseline=JSON.parse(await fs.readFile(root+'/initial-baseline.json','utf8'));
const file=await fs.readFile('H:/SteamLibrary/steamapps/common/Beastieball/data.win');assert.equal(crypto.createHash('sha256').update(file).digest('hex'),baseline.original_fingerprints['data.win']);
const chunks=new Map();for(let p=8;p<file.length;){const n=file.readUInt32LE(p+4);assert(p+n+8<=file.length);chunks.set(file.toString('ascii',p,p+4),{data:p+8,size:n});p+=n+8;}
function ptrs(tag){const d=chunks.get(tag).data,n=file.readUInt32LE(d);return Array.from({length:n},(_,i)=>file.readUInt32LE(d+4+i*4));}
const fptr=ptrs('FONT'),tptr=ptrs('TXTR'),pptr=ptrs('TPAG'),inventory=JSON.parse(await fs.readFile(root+'/reverse/font-inventory.json','utf8'));assert.equal(fptr.length,inventory.length);
const roles=new Set(['ftText','ftBold','ftSport','ftUI','ftEditor']);const pages=new Map();let records=[];
for(let i=0;i<inventory.length;i++){
 const font=inventory[i];if(!roles.has(font.name))continue;
 const pointer=file.readUInt32LE(fptr[i]+28);assert(pptr.includes(pointer));const v=Array.from({length:11},(_,j)=>file.readUInt16LE(pointer+j*2));const tx=tptr[v[10]];assert(tx);const size=file.readUInt32LE(tx+8),start=file.readUInt32LE(tx+24);assert(start+size<=file.length);assert.equal(file.toString('ascii',start,start+4),'DDS ');assert.equal(file.toString('ascii',start+84,start+88),'DXT5');const width=file.readUInt32LE(start+16),height=file.readUInt32LE(start+12);assert(width===file.readUInt32LE(tx+12)&&height===file.readUInt32LE(tx+16));assert(size>=128+width*height);assert.equal(v[2],v[6]);assert.equal(v[3],v[7]);assert.equal(v[4],0);assert.equal(v[5],0);
 let image=pages.get(v[10]);if(!image){image=decodeBc3(file.subarray(start+128,start+128+width*height),width,height);pages.set(v[10],image);}
 assert(v[0]+v[2]<=width&&v[1]+v[3]<=height);
 for(const glyph of font.glyphs)assert(glyph.SourceX+glyph.SourceWidth<=v[2]&&glyph.SourceY+glyph.SourceHeight<=v[3]);
 records.push({font:font.name,page:image,sourceX:v[0],sourceY:v[1],sourceWidth:v[2],sourceHeight:v[3],glyphs:font.glyphs});
}
export const originalFontPages=records;
await fs.mkdir(root+'/review',{recursive:true});await fs.writeFile(root+'/review/original-font-page-decode.json',JSON.stringify({source_data_sha256:baseline.original_fingerprints['data.win'],codec:'BC3/DXT5',synthetic_decoder_cases_passed:4,decoded_font_roles:records.map(r=>r.font),glyph_and_source_rectangles_verified:true,original_files_modified:false,native_roundtrip_verified:false},null,2)+'\n');
