"""Install/remove round-trips in an isolated workspace fixture, never the game."""
from pathlib import Path
import json,hashlib,subprocess,shutil
R=Path(__file__).resolve().parent;G=Path('H:/SteamLibrary/steamapps/common/Beastieball')
from original_inputs import original_input
manifest=json.loads((R/'release/payload/manifest.json').read_text('utf8'))
fixture=R/'staging/installer-test-game';fixture.mkdir(parents=True,exist_ok=True)
exe=R/'release/Beastieball-Arabic-Localization-Test.exe'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for f in manifest['Files']:
 p=fixture/f['Path'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original_input(f['Path']),p)
p=fixture/'loc/English.csv';shutil.copyfile(G/'loc/English.csv',p)
def run(mode):return subprocess.run([str(exe),'--'+mode,str(fixture)],check=False).returncode
def hashes():return {f['Path']:sha(fixture/f['Path']) for f in manifest['Files']}
original=hashes();cases=[]
# A mismatched source must refuse before backups or target changes.
victim=fixture/'ftEditor.yy';before=victim.read_bytes();victim.write_bytes(before+b'\n');altered=hashes()
assert run('install')!=0 and hashes()==altered and not (fixture/'.beastieball-arabic-backup').exists()
victim.write_bytes(before);cases.append('unsupported_source_refused_without_changes')
assert run('install')==0
assert hashes()=={f['Path']:f['Target'] for f in manifest['Files']}
assert sha(fixture/'loc/English.csv')==manifest['English'];cases.append('eight_files_installed_and_verified')
assert run('install')==0;cases.append('repeat_install_is_idempotent')
target_before=victim.read_bytes();victim.write_bytes(target_before+b'\n');altered=hashes()
assert run('remove')!=0 and hashes()==altered;cases.append('later_file_changes_protected_on_remove')
victim.write_bytes(target_before)
assert run('remove')==0 and hashes()==original
assert not (fixture/'.beastieball-arabic-backup').exists()
assert sha(fixture/'loc/English.csv')==manifest['English'];cases.append('byte_exact_remove_restore_and_backup_cleanup')
# Supported game inputs were read only throughout.
for f in manifest['Files']:assert sha(original_input(f['Path']))==f['Original']
assert sha(G/'loc/English.csv')==manifest['English']
report=dict(cases=cases,cases_passed=len(cases),installation_fixture=str(fixture),real_game_files_modified=False,english_unchanged=True,saves_accessed=False,game_launched=False,visual_rendering_verified=False)
(R/'review/installer-tests.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print(json.dumps(report))
