from pathlib import Path
import csv,json,hashlib,re
R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text('utf-8-sig'))
def digest(s):return hashlib.sha256(s.encode('utf8')).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),'utf8')
from original_inputs import original_input
with original_input('loc/English.csv').open('r',encoding='utf-8-sig',newline='') as f:english=dict(list(csv.reader(f))[1:])
rows=read(R/'source-bindings.json')
for x in rows:
 x['en']=english[x['id']];assert digest(x['en'])==x['source_sha256']
 x['commands']=re.findall(r'\[[^\]\r\n]*\]',x['en'])
write(R/'catalog/source-catalog.json',rows)
strings=read(R/'reverse/strings.json');d=read(R/'embedded-source-bindings.json')
for x in d['rows']:
 x['en']=strings[x['index']];assert digest(x['en'])==x['source_sha256']
write(R/'catalog/embedded-source-catalog.json',d)
print('Private catalogs reconstructed; do not upload English tables or strings.json.')
