"""Build an English-preserving x64 text router for the supported YYC runner.

This routes audited embedded English strings before loca/Scribble consume them.
Arabic remains logical Unicode: the game's existing Scribble parser performs
Arabic joining, bidi, wrapping and reveal. No script or glyph outlines are made.
The generated executable is a private candidate, never a distributable binary.
"""
from pathlib import Path
import hashlib,json,struct
from embed_direct_arabic import embed,builtin_wrapper,direct_guard,loading_wrapper
R=Path(__file__).resolve().parent
class Code:
 def __init__(self,rva):self.rva=rva;self.b=bytearray();self.labels={};self.fix=[]
 def emit(self,s):self.b.extend(bytes.fromhex(s))
 def label(self,n):self.labels[n]=self.rva+len(self.b)
 def rel(self,opcode,target):
  self.emit(opcode);p=len(self.b);self.b.extend(b'\0'*4);self.fix.append((p,target))
 def finish(self):
  for p,t in self.fix:
   dest=self.labels[t] if isinstance(t,str) else t
   struct.pack_into('<i',self.b,p,dest-(self.rva+p+4))
  return bytes(self.b)
def align(n,a):return (n+a-1)//a*a
def wrapper(rva,match_rva,trampoline_rva):
 c=Code(rva);c.emit('48 81 ec 48 01 00 00') # 328 bytes; preserve Win64 alignment
 c.emit('48 89 4c 24 40 48 89 54 24 48 4c 89 44 24 50 4c 89 4c 24 58')
 c.emit('48 8b 84 24 70 01 00 00 48 89 44 24 60') # incoming fifth argument
 c.emit('48 c7 84 24 20 01 00 00 00 00 00 00') # temporary ownership flag
 c.emit('45 85 c9');c.rel('0f 8e','original');c.emit('41 83 f9 10');c.rel('0f 8f','original')
 c.emit('48 85 c0');c.rel('0f 84','original');c.emit('48 8b 08 48 85 c9');c.rel('0f 84','original')
 c.rel('e8',match_rva);c.emit('48 85 c0');c.rel('0f 84','original')
 c.emit('48 89 84 24 20 01 00 00 48 89 c2 48 8d 8c 24 10 01 00 00')
 c.rel('e8',0x387E150) # actual supported runner's const UTF-8 RValue constructor
 c.emit('48 8b 54 24 60 44 8b 4c 24 58 31 c9')
 c.label('copy');c.emit('4c 8b 14 ca 4c 89 94 cc 80 00 00 00 ff c1 44 39 c9');c.rel('0f 8c','copy')
 c.emit('48 8d 84 24 10 01 00 00 48 89 84 24 80 00 00 00 48 8d 84 24 80 00 00 00')
 c.rel('e9','call')
 c.label('original');c.emit('48 8b 44 24 60')
 c.label('call');c.emit('48 89 44 24 20 48 8b 4c 24 40 48 8b 54 24 48 4c 8b 44 24 50 4c 8b 4c 24 58')
 c.rel('e8',trampoline_rva);c.emit('48 89 84 24 28 01 00 00')
 c.emit('48 83 bc 24 20 01 00 00 00');c.rel('0f 84','done')
 c.emit('48 8d 8c 24 10 01 00 00');c.rel('e8',0x1EC6D0)
 c.label('done');c.emit('48 8b 84 24 28 01 00 00 48 81 c4 48 01 00 00 c3')
 return c.finish()
def matcher(rva,language_rva,map_rva,count):
 c=Code(rva);c.emit('48 83 ec 28 48 89 4c 24 20')
 c.rel('48 8b 0d',0x50C7810);c.emit('48 85 c9');c.rel('0f 84','no')
 c.emit('48 8b 01');c.rel('8b 15',0x4FB5818);c.emit('ff 50 08') # global.lang_loaded_current
 c.emit('48 85 c0');c.rel('0f 84','no');c.emit('8b 50 0c 81 e2 ff ff ff 00 83 fa 01');c.rel('0f 85','no')
 c.emit('48 8b 00 48 85 c0');c.rel('0f 84','no');c.emit('48 8b 10 48 85 d2');c.rel('0f 84','no')
 c.rel('4c 8d 05',language_rva)
 c.label('language');c.emit('8a 02 41 3a 00');c.rel('0f 85','no');c.emit('84 c0');c.rel('0f 84','input')
 c.emit('48 ff c2 49 ff c0');c.rel('e9','language')
 c.label('input');c.emit('48 8b 4c 24 20 8b 41 0c 25 ff ff ff 00 83 f8 01');c.rel('0f 85','no')
 c.emit('48 8b 01 48 85 c0');c.rel('0f 84','no');c.emit('4c 8b 00 4d 85 c0');c.rel('0f 84','no')
 c.rel('48 8d 0d',0);c.rel('4c 8d 15',map_rva);c.emit('41 bb');c.b.extend(struct.pack('<I',count))
 c.label('row');c.emit('41 8b 02 4c 8d 0c 01 4c 89 c2')
 c.label('compare');c.emit('41 8a 01 3a 02');c.rel('0f 85','next');c.emit('84 c0');c.rel('0f 84','found')
 c.emit('49 ff c1 48 ff c2');c.rel('e9','compare')
 c.label('next');c.emit('49 83 c2 08 41 ff cb');c.rel('0f 85','row')
 c.label('no');c.emit('31 c0');c.rel('e9','return')
 c.label('found');c.emit('41 8b 42 04 48 01 c8')
 c.label('return');c.emit('48 83 c4 28 c3')
 return c.finish()
def build():
 source=Path('H:/SteamLibrary/steamapps/common/Beastieball/beastieball.exe').read_bytes()
 assert hashlib.sha256(source).hexdigest()=='ef8295592bfe1541bdea70097518c5e38e96516527a5ee5f6843debbdcce29d5'
 b=bytearray(source);pe=struct.unpack_from('<I',b,60)[0];op=pe+24;table=op+struct.unpack_from('<H',b,pe+20)[0];count=struct.unpack_from('<H',b,pe+6)[0]
 base=struct.unpack_from('<Q',b,op+24)[0];sa,fa=struct.unpack_from('<II',b,op+32);sections=[]
 for i in range(count):
  size,rva,rawsize,raw=struct.unpack_from('<4I',b,table+40*i+8);sections.append((size,rva,rawsize,raw))
 def raw(rva):
  _,v,n,p=next(s for s in sections if s[1]<=rva<s[1]+s[2]);return p+rva-v
 new_rva=align(max(v+max(n,s) for s,v,n,p in sections),sa);new_raw=align(len(b),fa);payload=bytearray()
 def add(data,boundary=16):
  payload.extend(b'\0'*(align(len(payload),boundary)-len(payload)));addr=new_rva+len(payload);payload.extend(data);return addr
 rows=json.loads((R/'catalog/embedded-translated-catalog.json').read_text('utf8'))['rows']
 pairs={}
 for row in rows:
  if row['status']=='preserve':continue
  assert '\0' not in row['en']+row['ar']
  if row['en'] in pairs:assert pairs[row['en']]==row['ar'],'Ambiguous text replacement'
  pairs[row['en']]=row['ar']
 language_rva=add('Русский'.encode('utf8')+b'\0');entries=[]
 for en,ar in pairs.items():entries.append((add(en.encode('utf8')+b'\0',1),add(ar.encode('utf8')+b'\0',1)))
 map_rva=add(b''.join(struct.pack('<II',a,z) for a,z in entries))
 match_rva=align(new_rva+len(payload),16);match_code=matcher(match_rva,language_rva,map_rva,len(entries));assert add(match_code)==match_rva
 functions=[(match_rva,match_rva+len(match_code),add(bytes.fromhex('01 04 01 00 04 42 00 00'),4))]
 hooks=[]
 for name,target,stolen in [('loca',0x1538E20,'4889542410'),('scribble',0x1C64430,'44894c2420')]:
  p=raw(target);assert b[p:p+5]==bytes.fromhex(stolen),'Unsupported native prologue'
  tramp_rva=align(new_rva+len(payload),16);c=Code(tramp_rva);c.emit(stolen);c.rel('e9',target+5);assert add(c.finish())==tramp_rva
  hook_rva=align(new_rva+len(payload),16);code=wrapper(hook_rva,match_rva,tramp_rva);assert add(code)==hook_rva
  unwind=add(bytes.fromhex('01 07 02 00 07 01 29 00'),4);functions.append((hook_rva,hook_rva+len(code),unwind))
  struct.pack_into('<Bi',b,p,0xE9,hook_rva-(target+5));hooks.append(dict(name=name,target_rva=target,wrapper_rva=hook_rva,wrapper_size=len(code),trampoline_rva=tramp_rva))
 exports,module_functions,imports_rva,imports_size,system_imports=embed((R/'staging/DirectArabic.dll').read_bytes(),new_rva,add,payload,source,raw,op)
 functions+=module_functions
 guard_rva=align(new_rva+len(payload),16);guard=direct_guard(Code,guard_rva,language_rva);assert add(guard)==guard_rva
 functions.append((guard_rva,guard_rva+len(guard),add(bytes.fromhex('01 04 01 00 04 42 00 00'),4)))
 direct_hooks=[]
 # Native registration table proves these bitmap API entry points. Explicitly
 # wrapped draw_text_ext paths are left intact; Scribble never enters these hooks.
 specs=[('draw_text',0x38c4df0,2,'40574883ec40'),('draw_text_transformed',0x38c5390,2,'48895c2408'),('draw_text_colour',0x38c4e50,2,'48895c2408'),('draw_text_transformed_colour',0x38c5470,2,'488bc448895808'),('string_width',0x38cb990,0,'48895c2408'),('string_height',0x38cb860,0,'48895c2408')]
 for name,target,index,stolen in specs:
  p=raw(target);n=len(bytes.fromhex(stolen));assert b[p:p+n]==bytes.fromhex(stolen),'Unsupported bitmap API '+name
  trampoline=align(new_rva+len(payload),16);c=Code(trampoline);c.emit(stolen);c.rel('e9',target+n);assert add(c.finish())==trampoline
  hook=align(new_rva+len(payload),16);code=builtin_wrapper(Code,hook,guard_rva,exports['ShapeArabicUtf8'],exports['FreeArabicUtf8'],trampoline,index);assert add(code)==hook
  functions.append((hook,hook+len(code),add(bytes.fromhex('01 07 02 00 07 01 39 00'),4)))
  b[p:p+n]=bytes([0xe9])+struct.pack('<i',hook-(target+5))+b'\x90'*(n-5)
  direct_hooks.append(dict(name=name,target_rva=target,wrapper_rva=hook,wrapper_size=len(code),trampoline_rva=trampoline,arg_index=index))
 loading_hooks=[]
 for name,target,is_length in [('string_length',0x38b1860,True),('string_char_at',0x38b15e0,False)]:
  p=raw(target);stolen=bytes.fromhex('40534883ec20' if is_length else '48895c2418');n=len(stolen);assert b[p:p+n]==stolen,'Unsupported loading API '+name
  trampoline=align(new_rva+len(payload),16);c=Code(trampoline);c.b.extend(stolen);c.rel('e9',target+n);assert add(c.finish())==trampoline
  hook=align(new_rva+len(payload),16);code=loading_wrapper(Code,hook,guard_rva,exports['IsLoadingArabic'],trampoline,is_length);assert add(code)==hook
  functions.append((hook,hook+len(code),add(bytes.fromhex('01 07 02 00 07 01 11 00'),4)))
  b[p:p+n]=bytes([0xe9])+struct.pack('<i',hook-(target+5))+b'\x90'*(n-5)
  loading_hooks.append(dict(name=name,target_rva=target,wrapper_rva=hook,wrapper_size=len(code),trampoline_rva=trampoline,is_length=is_length))
 # Extend exception metadata so Win64 stack unwinding remains defined for calls.
 pd_rva,pd_size=struct.unpack_from('<II',b,op+112+3*8);old_pd=source[raw(pd_rva):raw(pd_rva)+pd_size]
 records=[struct.unpack_from('<III',old_pd,i) for i in range(0,len(old_pd),12)]+functions;records.sort()
 pd=add(b''.join(struct.pack('<III',*r) for r in records),4)
 assert table+(count+3)*40<=min(p for s,v,n,p in sections if p) and not any(b[table+count*40:table+(count+3)*40])
 assert struct.unpack_from('<II',b,op+112+4*8)==(0,0),'Signed original not supported'
 payload_size=align(len(payload),fa);b.extend(b'\0'*(new_raw-len(b)));b.extend(payload);b.extend(b'\0'*(payload_size-len(payload)))
 # Loader writes new import addresses outside the original IAT-directory range.
 # Keep their page writable and non-executable; surrounding adapter code is RX.
 iat_start=min(i['iat_rva'] for i in system_imports)//sa*sa
 iat_end=align(max(i['iat_rva']+8 for i in system_imports),sa)
 slices=[(b'.arloc\0\0',new_rva,iat_start-new_rva,0x60000040),(b'.arimp\0\0',iat_start,iat_end-iat_start,0xc0000040),(b'.artail\0',iat_end,new_rva+len(payload)-iat_end,0x60000040)]
 for index,(name,rva,size,flags) in enumerate(slices):
  offset=rva-new_rva;raw_size=align(size,fa)
  struct.pack_into('<8sIIIIIIHHI',b,table+(count+index)*40,name,size,rva,raw_size,new_raw+offset,0,0,0,0,flags)
 struct.pack_into('<H',b,pe+6,count+3);struct.pack_into('<I',b,op+56,align(new_rva+len(payload),sa));struct.pack_into('<I',b,op+8,struct.unpack_from('<I',b,op+8)[0]+payload_size);struct.pack_into('<I',b,op+64,0);struct.pack_into('<II',b,op+112+3*8,pd,len(records)*12)
 struct.pack_into('<II',b,op+112+8,imports_rva,imports_size)
 report=dict(original_sha256=hashlib.sha256(source).hexdigest(),candidate_sha256=hashlib.sha256(b).hexdigest(),translation_slot='Русский',embedded_map_count=len(entries),embedded_source_records=463,original_literals_preserved=True,unconditional_literal_patch=False,english_csv_untouched=True,router_shaping='Existing native Scribble Arabic parser; logical Unicode input',hooks=hooks,matcher_rva=match_rva,matcher_size=len(match_code),section_rva=new_rva,section_raw=new_raw,image_size=align(new_rva+len(payload),sa),unwind_records_added=len(functions),synthetic_runtime_tested=False,in_game_verified=False,installable_candidate_ready=False)
 report.update(direct_hooks=direct_hooks,loading_hooks=loading_hooks,direct_exports=exports,system_imports=system_imports,direct_guard_rva=guard_rva,wrapped_bitmap_paths_changed=False)
 report['adapter_sections']=[dict(name=name.rstrip(b'\0').decode(),rva=rva,size=size,flags=flags) for name,rva,size,flags in slices]
 (R/'staging/beastieball-language-router-candidate.exe').write_bytes(b)
 (R/'review/native-language-router-build.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print(json.dumps(report))
if __name__=='__main__':build()
