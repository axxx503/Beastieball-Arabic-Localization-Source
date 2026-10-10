"""Execute generated x64 code against a synthetic ABI, never a game process.

Allocated memory contains only router payload and mock engine entry points.
No original game code is executed. Exercises language switching, argument-vector
ownership and original-input preservation independently of visual game tests.
"""
from pathlib import Path
import ctypes as C,json,struct
R=Path(__file__).resolve().parent
report=json.loads((R/'review/native-language-router-build.json').read_text('utf8'))
file=(R/'staging/beastieball-language-router-candidate.exe').read_bytes()
k=C.WinDLL('kernel32',use_last_error=True)
k.VirtualAlloc.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32,C.c_uint32];k.VirtualAlloc.restype=C.c_void_p
k.VirtualFree.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32];k.VirtualFree.restype=C.c_int
base=k.VirtualAlloc(None,report['image_size'],0x3000,0x40)
assert base,'Synthetic image allocation failed'
keep=[];errors=[];state={};constructions=0;destructions=0
def write(rva,b):C.memmove(base+rva,b,len(b))
def string_value(text):
 utf=C.create_string_buffer(text.encode('utf8'));ref=C.create_string_buffer(16);value=C.create_string_buffer(16)
 C.memmove(ref,struct.pack('<QII',C.addressof(utf),1,len(utf.raw)-1),16)
 C.memmove(value,struct.pack('<QII',C.addressof(ref),0,1),16)
 keep.extend([utf,ref,value]);return C.addressof(value)
def read_string(value):
 ptr=C.c_void_p.from_address(value).value
 return C.string_at(C.c_void_p.from_address(ptr).value).decode('utf8')
getter_type=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_int)
@getter_type
def getter(obj,var):return state['language_value']
ctor_type=C.CFUNCTYPE(None,C.c_void_p,C.c_void_p)
@ctor_type
def ctor(out,text):
 global constructions
 constructions+=1;ref=C.create_string_buffer(16);keep.append(ref)
 C.memmove(ref,struct.pack('<QII',text,1,len(C.string_at(text))),16)
 C.memmove(out,struct.pack('<QII',C.addressof(ref),0,1),16)
free_type=C.CFUNCTYPE(None,C.c_void_p)
@free_type
def free(value):
 global destructions
 destructions+=1
 C.memset(value,0,16)
gml_type=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_int,C.c_void_p)
@gml_type
def original(self,other,result,argc,argv):
 try:
  assert self==0x1234 and other==0x5678 and argc==state['argc']
  args=[C.c_void_p.from_address(argv+i*8).value for i in range(argc)] if argc else []
  assert args[1:]==state['args'][1:]
  if argc:assert read_string(args[0])==state['expected']
  state['called']+=1
 except Exception as e:errors.append(str(e))
 return result
def jump(callback):return bytes.fromhex('ff2500000000')+struct.pack('<Q',C.cast(callback,C.c_void_p).value)
try:
 write(report['section_rva'],file[report['section_raw']:])
 write(0x387E150,jump(ctor));write(0x1EC6D0,jump(free))
 vtable=C.create_string_buffer(24);C.memmove(C.addressof(vtable)+8,struct.pack('<Q',C.cast(getter,C.c_void_p).value),8)
 obj=C.create_string_buffer(8);C.memmove(obj,struct.pack('<Q',C.addressof(vtable)),8);keep.extend([vtable,obj])
 write(0x50C7810,struct.pack('<Q',C.addressof(obj)));write(0x4FB5818,struct.pack('<I',99))
 rows=json.loads((R/'catalog/embedded-translated-catalog.json').read_text('utf8'))['rows']
 samples=[r for r in rows if r['status']!='preserve'];sample=samples[0]
 scenarios=[('Русский',sample['en'],sample['ar'],3),('English',sample['en'],sample['en'],3),('Português Brasileiro',sample['en'],sample['en'],1),('Русский','Unmapped English text','Unmapped English text',1),('Русский',sample['ar'],sample['ar'],2),('Русский',sample['en'],sample['ar'],16),('Русский',sample['en'],sample['en'],17),('Русский',sample['en'],None,0)]
 passed=0
 for hook in report['hooks']:
  write(hook['target_rva']+5,jump(original))
  fn=gml_type(base+hook['wrapper_rva'])
  for lang,text,expected,count in scenarios:
   args=[string_value(text)]+[string_value('arg '+str(i)) for i in range(1,count)] if count else []
   vector=(C.c_void_p*max(1,count))(*args);result=C.create_string_buffer(16)
   snapshots=[C.string_at(a,16) for a in args]
   state.update(language_value=string_value(lang),argc=count,args=args,expected=expected,called=0)
   before=(constructions,destructions)
   returned=fn(0x1234,0x5678,C.addressof(result),count,C.addressof(vector))
   assert not errors,errors
   assert returned==C.addressof(result) and state['called']==1
   assert [C.string_at(a,16) for a in args]==snapshots,'Original argument mutated'
   translated=count<=16 and count>0 and text==sample['en'] and lang=='Русский'
   assert (constructions-before[0],destructions-before[1])==((1,1) if translated else (0,0)),'Temporary RValue ownership mismatch'
   passed+=1
 # Every audited embedded string must route correctly, then revert to English.
 hook=report['hooks'][0];fn=gml_type(base+hook['wrapper_rva'])
 for row in samples:
  for lang,expected in [('Русский',row['ar']),('English',row['en'])]:
   arg=string_value(row['en']);vector=(C.c_void_p*1)(arg);result=C.create_string_buffer(16)
   state.update(language_value=string_value(lang),argc=1,args=[arg],expected=expected,called=0)
   assert fn(0x1234,0x5678,C.addressof(result),1,C.addressof(vector))==C.addressof(result)
   assert not errors,errors
   assert state['called']==1
   passed+=1
 evidence=dict(cases_passed=passed,synthetic_native_execution=True,original_game_code_executed=False,game_launched=False,language_switch_roundtrip=True,argument_vectors_preserved=True,temporary_values_constructed=constructions,temporary_values_destroyed=destructions,in_game_verified=False)
 (R/'review/native-language-router-tests.json').write_text(json.dumps(evidence,indent=2)+'\n','utf8')
 print(json.dumps(evidence))
finally:k.VirtualFree(base,0,0x8000)
