from pathlib import Path
import json,hashlib,subprocess,sys
R=Path(__file__).resolve().parent
root=R/'staging/installer-test-game';new=R/'release/Beastieball-Arabic-Localization-Test.exe'
m=json.loads((R/'release/payload/manifest.json').read_text('utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(exe,op):return subprocess.run([str(exe),'--'+op,str(root)]).returncode
cases=[]
for version in (sys.argv[1:] or ['0.1.0','0.1.1','0.1.2','0.1.3','0.1.4']):
 old=R/('release/Beastieball-Arabic-Localization-Previous-'+version+'.exe')
 assert run(old,'install')==0
 backup=root/'.beastieball-arabic-backup'
 previous=(backup/'manifest.json').read_bytes()
 # A modified installed target must prevent upgrade without changing anything.
 victim=root/'ftEditor.yy';before=victim.read_bytes();victim.write_bytes(before+b'\n')
 changed={f['Path']:sha(root/f['Path']) for f in m['Files']}
 assert run(new,'install')!=0
 assert changed=={f['Path']:sha(root/f['Path']) for f in m['Files']}
 assert (backup/'manifest.json').read_bytes()==previous
 victim.write_bytes(before);cases.append(version+': modified target refuses upgrade')
 assert run(new,'install')==0
 for f in m['Files']:
  assert sha(root/f['Path'])==f['Target'] and sha(backup/f['Path'])==f['Original']
 assert sha(root/'loc/English.csv')==m['English']
 assert json.loads((backup/'manifest.json').read_text('utf-8-sig'))['Version']==m['Version']
 cases.append(version+': upgrade retains byte-exact originals and English')
 assert run(new,'remove')==0
 assert all(sha(root/f['Path'])==f['Original'] for f in m['Files']) and not backup.exists()
 cases.append(version+': new installer restores original after upgrade')
report=dict(cases_passed=len(cases),cases=cases,game_files_modified=False,saves_accessed=False)
(R/'review/installer-upgrade-tests.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print(json.dumps(report))
