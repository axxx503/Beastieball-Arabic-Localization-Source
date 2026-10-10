from pathlib import Path
import hashlib,json,re
from text_contract import differences
R=Path(__file__).resolve().parent
source=json.loads((R/'catalog/source-catalog.json').read_text('utf8'));by_id={x['id']:x for x in source}
exemptions=json.loads((R/'catalog/contract-exceptions.json').read_text('utf8'))
preserved_entries=json.loads((R/'catalog/preserved-records.json').read_text('utf8'))
def contract_source(row,ar):
    repair=exemptions['repairs'].get(row['id'])
    literal=exemptions['literal_labels'].get(row['id'])
    if repair:
        assert repair['source_sha256']==row['source_sha256'] and row['en'].count(repair['find'])==1, 'Stale repair '+row['id']
        return row['en'].replace(repair['find'],repair['replace']),ar
    if literal:
        assert literal['source_sha256']==row['source_sha256'] and literal['source']==row['en'] and literal['arabic']==ar, 'Invalid literal label '+row['id']
        return '', ''
    return row['en'],ar
authored={};errors=[]
for p in sorted((R/'translations').glob('*.json')):
    for key,entry in json.loads(p.read_text('utf8')).items():
        if key in authored:raise ValueError('Duplicate author key '+key)
        if key not in by_id:raise ValueError('Unknown source key '+key)
        row=by_id[key]
        if entry['source_sha256']!=row['source_sha256']:raise ValueError('Source changed '+key)
        text=entry['ar'];assert isinstance(text,str) and text
        # Native square-bracket tokens include sprite references and parser
        # commands. Until their behavior is analyzed, preserve exact tokens and
        # source order rather than silently changing formatting/state controls.
        contract_en,contract_ar=contract_source(row,text)
        for difference in differences(contract_en,contract_ar):errors.append(dict(id=key,reason=difference+' differs'))
        authored[key]=entry
assert not errors,errors
for key,entry in preserved_entries.items():
    row=by_id.get(key)
    assert row and row['source_sha256']==entry['source_sha256'] and entry['reason'] and key not in authored, 'Invalid preservation '+key
    row.update(status='preserve',preservation_reason=entry['reason'])
for row in source:
    if row['id'] in authored:row.update(ar=authored[row['id']]['ar'],status='authored_pending_review')
remaining=sum(r['status']=='pending' for r in source);done=len(authored)
(R/'catalog/translated-catalog.json').write_text(json.dumps(source,ensure_ascii=False,indent=2)+'\n','utf8')
report=dict(scope='Extracted CSV only',editorial_review_complete=False,native_integration_complete=False,installer_complete=False,baseline_nonempty_candidates=17690,preservation_audit_count=len(preserved_entries),authored=done,pending=remaining,preserved=sum(r['status']=='preserve' for r in source),translation_percent=round(100*done/(done+remaining),3),errors=errors,in_game_verified=False)
(R/'catalog/translation-report.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
print(json.dumps(report))
