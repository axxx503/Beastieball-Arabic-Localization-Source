import fs from 'node:fs/promises';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const root=path.dirname(fileURLToPath(import.meta.url));
import {originalFontPages} from './decode_original_font_pages.mjs';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function crc32(b){let c=0xffffffff;for(const v of b){c^=v;for(let k=0;k<8;k++)c=(c>>>1)^((c&1)?0xedb88320:0);}return (c^0xffffffff)>>>0;}
function paeth(a,b,c){const p=a+b-c,pa=Math.abs(p-a),pb=Math.abs(p-b),pc=Math.abs(p-c);return pa<=pb&&pa<=pc?a:pb<=pc?b:c;}
function decodePng(b){
 assert.equal(b.subarray(0,8).toString('hex'),'89504e470d0a1a0a');let w,h,parts=[];
 for(let p=8;p<b.length;){const n=b.readUInt32BE(p),name=b.toString('ascii',p+4,p+8),d=b.subarray(p+8,p+8+n);assert(p+n+12<=b.length);assert.equal(crc32(b.subarray(p+4,p+8+n)),b.readUInt32BE(p+8+n));if(name==='IHDR'){w=d.readUInt32BE(0);h=d.readUInt32BE(4);assert.equal(d[8],8);assert.equal(d[9],6);assert.equal(d[12],0);}if(name==='IDAT')parts.push(d);p+=n+12;}
 const raw=zlib.inflateSync(Buffer.concat(parts)),stride=w*4,pixels=Buffer.alloc(w*h*4);assert.equal(raw.length,(stride+1)*h);
 for(let y=0;y<h;y++){const filter=raw[y*(stride+1)];assert(filter<5);for(let x=0;x<stride;x++){const a=x>=4?pixels[y*stride+x-4]:0,bb=y?pixels[(y-1)*stride+x]:0,c=y&&x>=4?pixels[(y-1)*stride+x-4]:0,v=raw[y*(stride+1)+1+x];pixels[y*stride+x]=(v+(filter===0?0:filter===1?a:filter===2?bb:filter===3?Math.floor((a+bb)/2):paeth(a,bb,c)))&255;}}
 return {width:w,height:h,pixels};
}
function chunk(name,data){const tag=Buffer.from(name),n=Buffer.alloc(4),crc=Buffer.alloc(4);n.writeUInt32BE(data.length);crc.writeUInt32BE(crc32(Buffer.concat([tag,data])));return Buffer.concat([n,tag,data,crc]);}
function encodePng(im){const header=Buffer.alloc(13);header.writeUInt32BE(im.width);header.writeUInt32BE(im.height,4);header[8]=8;header[9]=6;const raw=Buffer.alloc((im.width*4+1)*im.height);for(let y=0;y<im.height;y++)im.pixels.copy(raw,y*(im.width*4+1)+1,y*im.width*4,(y+1)*im.width*4);return Buffer.concat([Buffer.from('89504e470d0a1a0a','hex'),chunk('IHDR',header),chunk('IDAT',zlib.deflateSync(raw)),chunk('IEND',Buffer.alloc(0))]);}
// Verify codec with distinct alpha/colors and multiple rows before touching derived outputs.
const fixture={width:2,height:2,pixels:Buffer.from([255,0,0,255,0,255,0,128,0,0,255,64,1,2,3,0])};assert.deepEqual(decodePng(encodePng(fixture)),fixture);
const originals=JSON.parse(await fs.readFile(root+'/fonts/selected-fonts.json','utf8'));
for(const f of originals.fonts)assert.equal(sha(await fs.readFile(root+'/fonts/'+f.workspace_file)),f.sha256,'TTF changed');
const caches={};for(const role of ['heavy']){const lines=(await fs.readFile(root+'/font-assets/'+role+'-64.tsv','utf8')).trim().split(/\r?\n/);const keys=lines.shift().split('\t');const rows=lines.map(l=>Object.fromEntries(l.split('\t').map((v,i)=>[keys[i],Number(v)])));caches[role]={image:decodePng(await fs.readFile(root+'/font-assets/'+role+'-64.png')),glyphs:new Map(rows.map(g=>[g.character,g]))};}
// Human selected the existing settings font for every ordinary game text role.
const profiles=[{font:'ftText',role:'heavy',scale:.85,baseline:60,height:93},{font:'ftBold',role:'heavy',scale:.85,baseline:60,height:93},{font:'ftUI',role:'heavy',scale:.85,baseline:60,height:93},{font:'ftSport',role:'heavy',scale:1,baseline:70,height:112},{font:'ftEditor',role:'heavy',scale:.34,baseline:23,height:38}];
const out=root+'/staging/font-resources';await fs.mkdir(out,{recursive:true});const reports=[];
for(const profile of profiles){
 let candidates=[...caches[profile.role].glyphs.values()].map(g=>({g,sourceRole:profile.role}));
 // Unmapped punctuation retains the original game bitmap below; no Saudi fallback.
 candidates.sort((a,b)=>a.g.character-b.g.character);const image={width:2048,height:2048,pixels:Buffer.alloc(2048*2048*4)};
 let x=2,y=2,records=[];
 for(const {g,sourceRole} of candidates){const w=Math.max(1,Math.round(g.width*profile.scale)),h=Math.max(1,Math.round(g.height*profile.scale)),top=profile.baseline-Math.round(g.origin_y*profile.scale);assert(top>=0&&top+h<=profile.height,'Glyph exceeds baseline box '+profile.font+'/'+g.character);
  if(x+w+2>image.width){x=2;y+=profile.height+2;}assert(y+profile.height+2<=image.height,'Atlas overflow '+profile.font);
  const source=caches[sourceRole].image;assert(g.x+g.width<=source.width&&g.y+g.height<=source.height);
  for(let dy=0;dy<h;dy++)for(let dx=0;dx<w;dx++){const sx=g.x+Math.min(g.width-1,Math.floor(dx/profile.scale)),sy=g.y+Math.min(g.height-1,Math.floor(dy/profile.scale)),pos=(sy*source.width+sx)*4,dest=((y+top+dy)*image.width+x+dx)*4;source.pixels.copy(image.pixels,dest,pos,pos+4);}
  records.push({character:g.character,x,y,w,h:profile.height,shift:Math.round(g.advance*profile.scale),offset:Math.round(g.origin_x*profile.scale),sourceRole,original_glyph_id:g.glyph_id});x+=w+2;
 }
 const originalPage=originalFontPages.find(f=>f.font===profile.font);assert(originalPage);
 const used=new Set(records.map(g=>g.character));let preservedOriginalGlyphs=0;
 for(const g of originalPage.glyphs){if(used.has(g.Character))continue;assert(g.SourceHeight<=profile.height);if(x+g.SourceWidth+2>image.width){x=2;y+=profile.height+2;}assert(y+profile.height+2<=image.height);
  const top=profile.height-g.SourceHeight;
  for(let dy=0;dy<g.SourceHeight;dy++){const source=((originalPage.sourceY+g.SourceY+dy)*originalPage.page.width+originalPage.sourceX+g.SourceX)*4,dest=((y+top+dy)*image.width+x)*4;originalPage.page.pixels.copy(image.pixels,dest,source,source+g.SourceWidth*4);}
  records.push({character:g.Character,x,y:y+top,w:g.SourceWidth,h:g.SourceHeight,shift:g.Shift,offset:g.Offset,sourceRole:'original',original_glyph_id:null});x+=g.SourceWidth+2;preservedOriginalGlyphs++;
 }
 records.sort((a,b)=>a.character-b.character);
 assert.equal(new Set(records.map(r=>r.character)).size,records.length);
 assert(originalPage.glyphs.every(g=>records.some(r=>r.character===g.Character)));
 const png=encodePng(image);assert.deepEqual(decodePng(png),image);
 await fs.writeFile(out+'/'+profile.font+'.png',png);
 await fs.writeFile(out+'/'+profile.font+'.glyphs.json',JSON.stringify(records,null,2)+'\n');
 // These are supplemental external .yy metrics; preserve all other original resource settings.
 const yyBytes=await fs.readFile('H:/SteamLibrary/steamapps/common/Beastieball/'+profile.font+'.yy');const yy=JSON.parse(yyBytes.toString('utf8').replace(/,\s*([}\]])/g,'$1'));assert.equal(yy.name,profile.font);yy.glyphs=Object.fromEntries(records.map(g=>[String(g.character),{character:g.character,h:g.h,offset:g.offset,shift:g.shift,w:g.w,x:g.x,y:g.y}]));yy.ascender=profile.baseline;yy.ascenderOffset=0;yy.fontName=profile.role==='normal'?'Saudi':'Academia Friendly';yy.bold=false;yy.italic=false;yy.applyKerning=0;yy.first=records[0].character;yy.last=records.at(-1).character;
 await fs.writeFile(out+'/'+profile.font+'.yy',JSON.stringify(yy,null,2)+'\n');reports.push({...profile,characters:records.length,preserved_original_glyphs:preservedOriginalGlyphs,atlas_sha256:sha(png),original_yy_sha256:sha(yyBytes),native_yy_baseline_agreement:true,png_roundtrip_verified:true});
}
await fs.writeFile(out+'/font-resource-plan.json',JSON.stringify({profiles:reports,font_outlines_modified:false,new_ttf_created:false,native_resources_built:false,in_game_verified:false,sizing_status:'Offline candidate sizing only; actual native line spacing must be verified'},null,2)+'\n');console.log(reports.map(p=>({font:p.font,characters:p.characters,baseline:p.baseline,height:p.height})));
