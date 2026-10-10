import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
const root=path.dirname(fileURLToPath(import.meta.url));
const game='H:/SteamLibrary/steamapps/common/Beastieball';
const digest=b=>crypto.createHash('sha256').update(b).digest('hex');
export function parseCsv(input){
 let rows=[],row=[],cell='',quoted=false,afterQuote=false;
 input=input.replace(/^\uFEFF/,'');
 for(let i=0;i<input.length;i++){
  const c=input[i];
  if(quoted){if(c==='"'){if(input[i+1]==='"'){cell+='"';i++;}else{quoted=false;afterQuote=true;}}else cell+=c;continue;}
  if(c==='"'){if(cell||afterQuote)throw Error('Invalid quote');quoted=true;continue;}
  if(c===','){row.push(cell);cell='';afterQuote=false;continue;}
  if(c==='\r'||c==='\n'){if(c==='\r'&&input[i+1]==='\n')i++;row.push(cell);rows.push(row);row=[];cell='';afterQuote=false;continue;}
  if(afterQuote)throw Error('Text after closing quote');
  cell+=c;
 }
 if(quoted)throw Error('Unclosed quoted field');
 if(cell||row.length||afterQuote){row.push(cell);rows.push(row);}
 return rows;
}
export function writeCsv(rows){const field=s=>/[",\r\n]/.test(s)?'"'+s.replaceAll('"','""')+'"':s;return rows.map(r=>r.map(field).join(',')).join('\r\n')+'\r\n';}
assert.deepEqual(parseCsv(writeCsv([['ID','English'],['id','عربي, "English"\nسطر ثان']])),[['ID','English'],['id','عربي, "English"\nسطر ثان']]);
assert.throws(()=>parseCsv('a,"broken'));assert.throws(()=>parseCsv('a,"text"junk'));
const baseline=JSON.parse(await fs.readFile(root+'/initial-baseline.json','utf8'));
const catalog=JSON.parse(await fs.readFile(root+'/catalog/translated-catalog.json','utf8'));
const original=await fs.readFile(game+'/loc/English.csv');
assert.equal(digest(original),baseline.original_fingerprints['loc/English.csv'],'Unsupported original CSV');
const source=parseCsv(original.toString('utf8'));assert.deepEqual(source[0],['ID','English']);assert.equal(source.length,catalog.length+1);
// Arabic is authored from English but occupies Russian's selectable slot.
// English.csv is never an installation target.
const slot=JSON.parse(await fs.readFile(root+'/language-slot.json','utf8'));
const targetPath=slot.path;
let targetOriginal=await fs.readFile(game+'/'+targetPath);
if(digest(targetOriginal)!==slot.original_sha256)targetOriginal=await fs.readFile(game+'/.beastieball-arabic-backup/'+targetPath);
assert.equal(digest(targetOriginal),slot.original_sha256,'Unsupported original language slot');
const targetSource=parseCsv(targetOriginal.toString('utf8'));
assert.equal(targetSource[0].length,2);
const records=[],rows=[targetSource[0]];
for(let i=0;i<catalog.length;i++){
 const r=catalog[i];assert.deepEqual(source[i+1],[r.id,r.en]);assert.equal(digest(r.en),r.source_sha256);assert.notEqual(r.status,'pending');
 const text=r.status==='preserve'?r.en:r.ar;assert.equal(typeof text,'string');rows.push([r.id,text]);
 if(text!==r.en)records.push({id:r.id,source_sha256:r.source_sha256,ar:text});
}
const candidate=writeCsv(rows);assert.deepEqual(parseCsv(candidate),rows);
const out=root+'/staging/language';await fs.mkdir(out,{recursive:true});
await fs.writeFile(out+'/'+path.basename(targetPath),candidate,'utf8');
const patch={format:'beastieball-source-bound-language-v2',path:targetPath,source_path:'loc/English.csv',source_sha256:digest(original),original_sha256:digest(targetOriginal),target_sha256:digest(candidate),records};
await fs.writeFile(out+'/language-patch.json',JSON.stringify(patch,null,2)+'\n');
const report={scope:'Logical Unicode language candidate only',target_path:targetPath,translation_source:'English',english_file_install_target:false,records:catalog.length,translated_records:records.length,preserved_records:catalog.length-records.length,source_sha256:digest(original),original_slot_sha256:digest(targetOriginal),candidate_sha256:digest(candidate),roundtrip_verified:true,source_order_verified:true,source_hashes_verified:true,configuration_preserved:rows[1][1]===source[1][1],csv_parser_tests_passed:3,original_files_modified:false,saves_accessed:false,native_rendering_ready:false,installer_ready:false};
await fs.writeFile(root+'/review/language-candidate.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
