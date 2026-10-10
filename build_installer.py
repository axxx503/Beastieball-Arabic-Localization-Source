"""Package original-dependent deltas into a single local test installer."""
from pathlib import Path
import hashlib,json,subprocess,shutil,zipfile
R=Path(__file__).resolve().parent
from original_inputs import GAME as G,original_input
tool=R.parent/'slayblade/tools/xdelta3/xdelta3-3.2.1-windows-x86_64/xdelta3.exe'
payload=R/'release/payload';payload.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=[('beastieball.exe',R/'staging/beastieball-language-router-candidate.exe'),('data.win',R/'staging/data-font-candidate.win'),('loc/Русский.csv',R/'staging/language/Русский.csv')]+[(f+'.yy',R/('staging/font-resources/'+f+'.yy')) for f in ['ftText','ftBold','ftUI','ftSport','ftEditor']]
manifest=dict(Version='0.1.5-All-in-One-Beta',English=sha(G/'loc/English.csv'),Files=[])
for i,(rel,candidate) in enumerate(spec):
 patch=payload/(str(i)+'.xdelta')
 subprocess.run([str(tool),'-f','-e','-9','-s',str(original_input(rel)),str(candidate),str(patch)],check=True,capture_output=True)
 decoded=R/('staging/delta-roundtrip-'+str(i)+'.bin')
 subprocess.run([str(tool),'-f','-d','-s',str(original_input(rel)),str(patch),str(decoded)],check=True,capture_output=True)
 assert sha(decoded)==sha(candidate),'Delta did not reproduce candidate'
 decoded.unlink()
 manifest['Files'].append(dict(Path=rel,Patch=patch.name,Original=sha(original_input(rel)),Target=sha(candidate)))
(payload/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
shutil.copyfile(tool,payload/'xdelta3.exe')
shutil.copyfile(tool.parent/'README.md',payload/'xdelta3-README.md')
shutil.copytree(R/'licenses',payload/'licenses',dirs_exist_ok=True)
(payload/'font-sources').mkdir(exist_ok=True)
shutil.copy2(R/'fonts/AcademiaFriendly-Regular.ttf',payload/'font-sources/AcademiaFriendly-Regular.ttf')
archive=R/'release/payload.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in sorted(payload.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(payload).as_posix())
out=R/'release/Beastieball-Arabic-Localization-Test.exe'
csc=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
args=[str(csc),'/nologo','/target:winexe','/platform:x64','/optimize+', '/out:'+str(out), '/resource:'+str(archive)+',payload.zip','/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll','/r:System.IO.Compression.dll','/r:System.IO.Compression.FileSystem.dll',str(R/'Installer.cs')]
subprocess.run(args,check=True)
report=dict(version=manifest['Version'],patched_files=len(spec),delta_roundtrips_passed=len(spec),installer_compiled=True,installer_bytes=out.stat().st_size,installer_sha256=sha(out),english_install_target=False,game_files_modified=False,saves_accessed=False,full_game_binaries_distributed=False,in_game_verified=False)
(R/'review/installer-build.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print(json.dumps(report))
