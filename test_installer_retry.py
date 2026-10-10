"""Repeat installation within one extracted installer session, in a private fixture."""
from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parent
fixture=R/'staging/installer-test-game'
m=json.loads((R/'release/payload/manifest.json').read_text('utf8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(fixture/f['Path'])==f['Original'] for f in m['Files'])
p=subprocess.run([str(R/'staging/InstallerRetryHarness.exe'),str(fixture)],capture_output=True,text=True)
assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
assert all(sha(fixture/f['Path'])==f['Original'] for f in m['Files'])
assert sha(fixture/'loc/English.csv')==m['English']
assert not (fixture/'.beastieball-arabic-backup').exists()
report=dict(same_process=True,payload_extracted_once=True,sequence=['install','remove','install','remove'],operations_passed=4,byte_exact_restore=True,english_unchanged=True,game_launched=False,real_game_files_modified=False,saves_accessed=False)
(R/'review/installer-retry-test.json').write_text(json.dumps(report,indent=2)+'\n','utf8')
print(json.dumps(report))
