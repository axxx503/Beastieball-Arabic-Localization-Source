"""Execute actual injected direct-render wrappers and OS bidi code with mock game ABI."""
from pathlib import Path
import ctypes as C,json,struct
from arabic_reshaper import reshape
from bidi.algorithm import get_display
R=Path(__file__).resolve().parent
r=json.loads((R/'review/native-language-router-build.json').read_text('utf8'))
b=(R/'staging/beastieball-language-router-candidate.exe').read_bytes()
k=C.WinDLL('kernel32',use_last_error=True)
k.VirtualAlloc.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32,C.c_uint32];k.VirtualAlloc.restype=C.c_void_p
k.VirtualFree.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32];k.VirtualFree.restype=C.c_int
base=k.VirtualAlloc(None,r['image_size'],0x3000,0x40);assert base
keep=[];state={};errors=[];ctor_count=0;free_count=0
def write(addr,data):C.memmove(base+addr,data,len(data))
def string_value(s):
 text=C.create_string_buffer(s.encode('utf8'));ref=C.create_string_buffer(16)
 C.memmove(ref,struct.pack('<QII',C.addressof(text),1,len(text.raw)-1),16);keep.extend([text,ref])
 return struct.pack('<QII',C.addressof(ref),0,1)
def read_string(addr):return C.string_at(C.c_void_p.from_address(C.c_void_p.from_address(addr).value).value).decode('utf8')
@C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_int)
def getter(obj,var):return state['language']
@C.CFUNCTYPE(None,C.c_void_p,C.c_void_p)
def ctor(out,text):
 global ctor_count
 ctor_count+=1;ref=C.create_string_buffer(16);keep.append(ref)
 C.memmove(ref,struct.pack('<QII',text,1,len(C.string_at(text))),16);C.memmove(out,struct.pack('<QII',C.addressof(ref),0,1),16)
@C.CFUNCTYPE(None,C.c_void_p)
def free(value):
 global free_count
 free_count+=1;C.memset(value,0,16)
gml=C.CFUNCTYPE(C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_int,C.c_void_p)
@gml
def original(result,self,other,argc,argv):
 try:
  assert (result,self,other,argc)==(state.get('result',0x9876),0x1234,0x5678,state['argc'])
  idx=state['index'];actual=C.string_at(argv,argc*16) if argc else b''
  for i in range(argc):
   if i==idx and state['expected'] is not None:assert read_string(argv+16*i)==state['expected']
   else:assert actual[16*i:16*i+16]==state['original'][16*i:16*i+16]
  state['called']+=1
 except Exception as e:errors.append(str(e))
 return result
def jump(fn):return bytes.fromhex('ff2500000000')+struct.pack('<Q',C.cast(fn,C.c_void_p).value)
try:
 write(r['section_rva'],b[r['section_raw']:])
 dlls={}
 for imp in r['system_imports']:
  dll=dlls.setdefault(imp['dll'],C.WinDLL(imp['dll']));fn=getattr(dll,imp['name'])
  write(imp['iat_rva'],struct.pack('<Q',C.cast(fn,C.c_void_p).value))
 write(0x387e150,jump(ctor));write(0x1ec6d0,jump(free))
 vtable=C.create_string_buffer(24);C.memmove(C.addressof(vtable)+8,struct.pack('<Q',C.cast(getter,C.c_void_p).value),8)
 obj=C.create_string_buffer(struct.pack('<Q',C.addressof(vtable)));keep.extend([vtable,obj])
 write(0x50c7810,struct.pack('<Q',C.addressof(obj)));write(0x4fb5818,struct.pack('<I',99))
 samples=['جار التحميل...','تمهيدي (لا تدعم الإنجازات)','للوصول للجميع','اضغط SHIFT للتفاصيل','رمز الفريق 42GMC15','لاتصال الإنترنت']
 scenarios=[('Русский',s,get_display(reshape(s)),6) for s in samples]
 scenarios+=[('English',samples[0],samples[0],6),('Русский','English','English',6),('Русский',get_display(reshape(samples[0])),get_display(reshape(samples[0])),6),('Русский',samples[0],get_display(reshape(samples[0])),16),('Русский',samples[0],samples[0],17),('Русский',samples[0],None,0)]
 passed=0
 for h in r['direct_hooks']:
  write(h['trampoline_rva'],jump(original));entry=gml(base+h['wrapper_rva'])
  for language,text,expected,argc in scenarios:
   raw=bytearray().join(struct.pack('<dII',i+.25,0,0) for i in range(argc))
   if argc>h['arg_index']:raw[16*h['arg_index']:16*h['arg_index']+16]=string_value(text)
   elif argc:expected=None
   args=C.create_string_buffer(bytes(raw) or bytes(1));lang=C.create_string_buffer(string_value(language));keep.extend([args,lang])
   state.update(language=C.addressof(lang),argc=argc,index=h['arg_index'],expected=expected,original=bytes(raw),called=0)
   assert entry(0x9876,0x1234,0x5678,argc,C.addressof(args))==0x9876
   assert state['called']==1 and not errors,(h,errors)
   assert args.raw[:len(raw)]==bytes(raw),'Original caller arguments modified'
   passed+=1
 assert ctor_count==free_count
 temporary_free_count=free_count
 copies=[]
 @C.CFUNCTYPE(None,C.c_void_p,C.c_void_p)
 def copy_value(dst,src):copies.append((dst,src));C.memmove(dst,src,16)
 write(0x1ec800,jump(copy_value))
 @C.CFUNCTYPE(C.c_double,C.c_void_p)
 def numeric_value(src):
  kind=C.c_uint32.from_address(src+12).value
  return float(C.c_int32.from_address(src).value) if kind==7 else C.c_double.from_address(src).value
 write(0x3857160,jump(numeric_value))
 loading_cases=0;loading_slots={};loading_length=None
 for h in r['loading_hooks']:
  write(h['trampoline_rva'],jump(original));entry=gml(base+h['wrapper_rva'])
  for language,text,argc,index,kind in [('Русский','جار التحميل...',2,i,k) for i in [1,2,3] for k in [0,7]]+[('English','جار التحميل...',2,1,0),('Русский','Other text',2,1,0),('Русский','جار التحميل...',0,1,0)]:
   value=struct.pack('<iIII',index,0,0,7) if kind==7 else struct.pack('<dII',float(index),0,0)
   raw=string_value(text)+value if argc else b''
   args=C.create_string_buffer(raw or bytes(1));lang=C.create_string_buffer(string_value(language));result=C.create_string_buffer(16);keep.extend([args,lang,result])
   state.update(language=C.addressof(lang),argc=argc,index=0,expected=text if argc else None,original=raw,called=0,result=C.addressof(result))
   assert entry(C.addressof(result),0x1234,0x5678,argc,C.addressof(args))==C.addressof(result)
   if language=='Русский' and text=='جار التحميل...' and argc:
    assert state['called']==0
    if h['is_length']:assert struct.unpack('<dII',result.raw)==(3.,0,0)
    elif index==2:assert read_string(C.addressof(result))==text and result.raw==raw[:16]
    else:assert read_string(C.addressof(result))==''
    if kind==0:
     if h['is_length']:loading_length=struct.unpack_from('<d',result.raw)[0]
     else:loading_slots[index]=read_string(C.addressof(result))
   else:assert state['called']==1 and not errors
   assert args.raw[:len(raw)]==raw
   loading_cases+=1
 # Source trace at 0x2bd1dc4 subtracts 1 from length; 0x2bd1e89 divides
 # width*i by that value. Old length=1 produced 0/0 on the only iteration.
 import math
 assert loading_length==3 and loading_slots=={1:'',2:'جار التحميل...',3:''}
 for screen,width in [(1280,400),(1920,620),(2560,900)]:
  visible=[]
  for i in range(int(loading_length)):
   x=screen*.5-width*.5+width*i/(loading_length-1)
   assert math.isfinite(x)
   if loading_slots[i+1]:visible.append(x)
  assert visible==[screen*.5]
 report=dict(cases_passed=passed+loading_cases,direct_cases=passed,loading_cases=loading_cases,loading_geometry_scenarios=3,loading_visible_runs=1,loading_centered=True,direct_wrappers=len(r['direct_hooks']),injected_native_code_executed=True,os_imports_resolved=True,caller_arguments_preserved=True,temporary_constructed=ctor_count,temporary_destroyed=temporary_free_count,loading_native_reference_copies=len(copies),game_code_executed=False,in_game_verified=False)
 (R/'review/direct-hook-tests.json').write_text(json.dumps(report,indent=2)+'\n','utf8');print(json.dumps(report))
finally:k.VirtualFree(base,0,0x8000)
