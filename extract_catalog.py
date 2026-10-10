from pathlib import Path
import csv,json,hashlib,re,collections
R=Path(__file__).resolve().parent;G=Path(r'H:\SteamLibrary\steamapps\common\Beastieball')
source=G/'loc/English.csv';baseline=json.loads((R/'initial-baseline.json').read_text('utf8'))
digest=hashlib.sha256(source.read_bytes()).hexdigest();assert digest==baseline['original_fingerprints']['loc/English.csv']
with source.open('r',encoding='utf-8-sig',newline='') as f:rows=list(csv.reader(f))
assert rows[0]==['ID','English'];assert all(len(r)==2 for r in rows)
ids=set();catalog=[];counts=collections.Counter();commands=collections.Counter()
for line,(key,text) in enumerate(rows[1:],2):
    assert key not in ids;ids.add(key)
    category='empty' if not text else 'configuration' if key=='FONT_STYLE' else 'text_unreviewed'
    tokens=re.findall(r'\[[^\]\r\n]*\]',text)
    counts[category]+=1;commands.update(tokens)
    catalog.append(dict(id=key,csv_record=line,source_sha256=hashlib.sha256(text.encode('utf8')).hexdigest(),en=text,ar=None,status='preserve' if category in ['empty','configuration'] else 'pending',category=category,commands=tokens))
out=R/'catalog';out.mkdir(exist_ok=True)
(out/'source-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n','utf8')
(out/'extraction-report.json').write_text(json.dumps(dict(source_sha256=digest,records=len(catalog),categories=dict(counts),unique_texts=len({x['en'] for x in catalog if x['status']=='pending'}),command_tokens=dict(commands),translated_records=0,in_game_verified=False),ensure_ascii=False,indent=2)+'\n','utf8')
(R/'translations').mkdir(exist_ok=True)
print(json.dumps(dict(records=len(catalog),categories=dict(counts),unique_texts=len({x['en'] for x in catalog if x['status']=='pending'}))))
