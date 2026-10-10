import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {signature} from './contract_rules.mjs';
const root=path.dirname(fileURLToPath(import.meta.url));
const catalog=JSON.parse(await fs.readFile(root+'/catalog/embedded-source-catalog.json','utf8'));
const strings=JSON.parse(await fs.readFile(root+'/reverse/strings.json','utf8'));
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
const byId=new Map(catalog.rows.map(r=>[r.id,r]));const entries=new Map();
for(const file of (await fs.readdir(root+'/embedded-translations')).filter(f=>f.endsWith('.json')).sort()){
 for(const [id,entry] of Object.entries(JSON.parse(await fs.readFile(root+'/embedded-translations/'+file,'utf8')))){
  assert(byId.has(id),'Unknown embedded ID '+id);assert(!entries.has(id),'Duplicate embedded ID '+id);entries.set(id,entry);
 }
}
const rows=catalog.rows.map(r=>({...r}));
for(const row of rows){
 assert.equal(strings[row.index],row.en,'Original string changed '+row.id);assert.equal(hash(row.en),row.source_sha256);
 const entry=entries.get(row.id);
 if(entry){assert.equal(entry.source_sha256,row.source_sha256);assert.equal(typeof entry.ar,'string');assert(entry.ar);assert.notEqual(row.status,'preserve');assert.deepEqual(signature(row.en),signature(entry.ar),'Broken embedded contract '+row.id);row.ar=entry.ar;row.status='authored_pending_review';}
}
const report={scope:catalog.scope,total:rows.length,authored:rows.filter(r=>r.status==='authored_pending_review').length,reused_pending_context_review:rows.filter(r=>r.status==='reused_pending_context_review').length,preserved:rows.filter(r=>r.status==='preserve').length,pending:rows.filter(r=>r.status==='pending').length,source_strings_verified:true,native_reachability_verified:false,game_files_modified:false};
await fs.writeFile(root+'/catalog/embedded-translated-catalog.json',JSON.stringify({...catalog,rows},null,2)+'\n');
await fs.writeFile(root+'/review/embedded-translation-report.json',JSON.stringify(report,null,2)+'\n');
assert.equal(report.pending,0,'Embedded authoring incomplete');assert.equal(report.reused_pending_context_review,0);
const patches=rows.filter(r=>r.ar&&r.ar!==r.en).map(r=>({index:r.index,source_sha256:r.source_sha256,ar:r.ar}));
await fs.mkdir(root+'/staging/embedded',{recursive:true});
await fs.writeFile(root+'/staging/embedded/string-patch.json',JSON.stringify({format:'beastieball-source-bound-strg-v1',path:'data.win',original_sha256:catalog.game_data_sha256,records:patches,native_reachability_verified:false},null,2)+'\n');
console.log(JSON.stringify(report));
