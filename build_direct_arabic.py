from pathlib import Path
import subprocess,unicodedata,json
R=Path(__file__).resolve().parent
forms={}
for cp in range(0xfb50,0xff00):
 d=unicodedata.decomposition(chr(cp)).split()
 if len(d)==2 and d[0] in ['<isolated>','<initial>','<medial>','<final>']:
  base=int(d[1],16)
  if 0x600<=base<=0x6ff:forms.setdefault(base,{})[d[0]]=cp
header='static const Form forms[]={\n'
for base,f in sorted(forms.items()):header+='{'+','.join(hex(v) for v in [base]+[f.get(k,0) for k in ['<isolated>','<initial>','<medial>','<final>']])+'},\n'
header+='};\n#define FORM_COUNT '+str(len(forms))+'\n'
(R/'ArabicPresentationTable.h').write_text(header,'ascii')
msvc=Path('C:/Program Files (x86)/Microsoft Visual Studio/18/BuildTools/VC/Tools/MSVC/14.51.36231')
sdk=Path('C:/Program Files (x86)/Windows Kits/10')
out=R/'staging/DirectArabic.dll'
args=[str(msvc/'bin/Hostx64/x64/cl.exe'),'/nologo','/O2','/GS-','/Zl','/LD','/Fo'+str(R/'staging/DirectArabic.obj'),'/I'+str(msvc/'include')]
args+=['/I'+str(sdk/('Include/10.0.26100.0/'+d)) for d in ['um','shared','ucrt']]
args+=[str(R/'DirectArabic.c'),'/link','/NOENTRY','/NODEFAULTLIB','/OUT:'+str(out),'/IMPLIB:'+str(R/'staging/DirectArabic.lib'),'/LIBPATH:'+str(sdk/'Lib/10.0.26100.0/um/x64'),'kernel32.lib','usp10.lib']
subprocess.run(args,check=True)
print('Compiled native direct-text shaping module; no TTF changes.')
