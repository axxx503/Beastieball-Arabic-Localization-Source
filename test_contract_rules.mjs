import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';
import {signature,contractSource} from './contract_rules.mjs';
const root=path.dirname(fileURLToPath(import.meta.url));
const source=JSON.parse(await fs.readFile(root+'/catalog/source-catalog.json','utf8'));
const exceptions=JSON.parse(await fs.readFile(root+'/catalog/contract-exceptions.json','utf8'));
let tests=[];
function test(name,fn){fn();tests.push({name,passed:true});}
function equal(a,b){return JSON.stringify(signature(a))===JSON.stringify(signature(b));}
for(const id of Object.keys(exceptions.repairs)){
 const row=source.find(r=>r.id===id);
 test('repair '+id,()=>{const [s]=contractSource(row,'test',exceptions);assert(s.includes(exceptions.repairs[id].replace));});
 test('reject stale repair hash '+id,()=>assert.throws(()=>contractSource({...row,source_sha256:'changed'},'test',exceptions)));
 test('reject missing repair token '+id,()=>assert.throws(()=>contractSource({...row,en:'plain'},'test',exceptions)));
}
for(const [id,entry] of Object.entries(exceptions.literal_labels)){
 const row=source.find(r=>r.id===id);
 test('allow exact literal '+id,()=>assert.deepEqual(contractSource(row,entry.arabic,exceptions),['','']));
 test('reject arbitrary command-like literal '+id,()=>assert.throws(()=>contractSource(row,'[other]',exceptions)));
 test('reject literal source change '+id,()=>assert.throws(()=>contractSource({...row,en:'[other]'},entry.arabic,exceptions)));
}
test('retain normal sprite contract',()=>assert(!equal('[sprStatus,17]Ready','[sprStatus,18]جاهز')));
test('retain command order',()=>assert(!equal('[wave]hi[/wave]','[/wave]مرحبًا[wave]')));
test('retain repeated placeholder count',()=>assert(!equal('{0} {0}','{0}')));
test('allow placeholder reordering',()=>assert(equal('{0} and {1}','{1} و{0}')));
test('retain placeholder case',()=>assert(!equal('{name}','{Name}')));
test('retain pause run order',()=>assert(!equal('a|b||c','أ||ب|ج')));
test('allow grammatical gender branches',()=>assert(equal('{g:man,woman,coach}','{g:رجل,امرأة,مدرب}')));
test('reject lost gender branch',()=>assert(!equal('{g:man,woman,coach}','{g:رجل,امرأة}')));
test('retain plural branches',()=>assert(!equal('{p:{0},one,many}','{p:{0},واحد}')));
test('retain escaped newlines',()=>assert(!equal('one\ntwo','واحد اثنان')));
test('retain choice prefixes',()=>assert(!equal('>yes','نعم')));
test('retain malformed brace check',()=>assert(!equal('hi {0}','أهلا {0} {')));
await fs.mkdir(root+'/review',{recursive:true});
const report={runner:'Node.js',scope:'Changed contract exceptions and regression cases; no native rendering tested',passed:tests.length,failed:0,tests};
await fs.writeFile(root+'/review/contract-tests.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({passed:tests.length,failed:0}));
