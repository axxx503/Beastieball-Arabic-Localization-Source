"""Embed compiled position-independent code, OS imports and unwind records."""
import struct
def embed(blob,new_rva,add,payload,source,raw,optional):
 pe=struct.unpack_from('<I',blob,60)[0];op=pe+24
 assert struct.unpack_from('<H',blob,pe+4)[0]==0x8664
 size=struct.unpack_from('<I',blob,op+56)[0];mapped=bytearray(size)
 table=op+struct.unpack_from('<H',blob,pe+20)[0]
 for i in range(struct.unpack_from('<H',blob,pe+6)[0]):
  vs,va,rs,rp=struct.unpack_from('<4I',blob,table+40*i+8)
  mapped[va:va+rs]=blob[rp:rp+rs]
 directory=lambda i:struct.unpack_from('<II',blob,op+112+8*i)
 assert directory(5)==(0,0),'Absolute relocations require explicit support'
 assert directory(9)==(0,0) and directory(13)==(0,0),'TLS/delay imports not supported'
 def cstr(p):return mapped[p:mapped.index(0,p)].decode('ascii')
 er,_=directory(0);e=struct.unpack_from('<IIHHIIIIIII',mapped,er)
 exports={}
 for i in range(e[7]):
  name=cstr(struct.unpack_from('<I',mapped,e[9]+4*i)[0]);ordinal=struct.unpack_from('<H',mapped,e[10]+2*i)[0]
  exports[name]=struct.unpack_from('<I',mapped,e[8]+4*ordinal)[0]
 # Reserve the complete linked module layout; RIP-relative instructions remain valid.
 module_rva=add(bytes(mapped),4096);offset=module_rva-new_rva
 imports=[];descriptors=[];ir,_=directory(1)
 for p in range(ir,ir+4096,20):
  ilt,timestamp,forward,name,iat=struct.unpack_from('<5I',mapped,p)
  if not any((ilt,timestamp,forward,name,iat)):break
  dll=cstr(name);assert ilt and not timestamp
  for j in range(8192):
   entry=struct.unpack_from('<Q',mapped,ilt+8*j)[0]
   if not entry:break
   assert not entry>>63,'Ordinal import unsupported'
   func=cstr(entry+2);imports.append(dict(dll=dll,name=func,iat_rva=module_rva+iat+8*j))
   for thunk in [ilt,iat]:struct.pack_into('<Q',payload,offset+thunk+8*j,module_rva+entry)
  descriptors.append(struct.pack('<5I',module_rva+ilt,0,0,module_rva+name,module_rva+iat))
 orig_rva,orig_size=struct.unpack_from('<II',source,optional+112+8)
 old=[]
 for p in range(raw(orig_rva),raw(orig_rva)+orig_size,20):
  d=source[p:p+20]
  if not any(d):break
  old.append(d)
 import_rva=add(b''.join(old+descriptors)+bytes(20),4)
 pdata,pdatasize=directory(3)
 functions=[tuple(module_rva+x for x in struct.unpack_from('<3I',mapped,p)) for p in range(pdata,pdata+pdatasize,12)]
 return {name:module_rva+rva for name,rva in exports.items()},functions,import_rva,20*(len(old)+len(descriptors)+1),imports

def builtin_wrapper(Code,rva,guard_rva,shape_rva,free_rva,trampoline_rva,arg_index):
 c=Code(rva);c.emit('48 81 ec c8 01 00 00') # 456 bytes; contiguous RValues at +128
 c.emit('48 89 4c 24 40 48 89 54 24 48 4c 89 44 24 50 4c 89 4c 24 58')
 c.emit('48 8b 84 24 f0 01 00 00 48 89 44 24 60') # fifth arg
 c.emit('48 c7 84 24 a0 01 00 00 00 00 00 00')
 c.emit('41 83 f9 '+format(arg_index,'02x'));c.rel('0f 8e','original')
 c.emit('41 83 f9 10');c.rel('0f 8f','original');c.emit('48 85 c0');c.rel('0f 84','original')
 c.emit('48 8d 48 '+format(arg_index*16,'02x'));c.rel('e8',guard_rva)
 c.emit('48 85 c0');c.rel('0f 84','original');c.emit('48 89 c1');c.rel('e8',shape_rva)
 c.emit('48 85 c0');c.rel('0f 84','original');c.emit('48 89 84 24 a0 01 00 00')
 c.emit('48 89 c2 48 8d 8c 24 80 01 00 00');c.rel('e8',0x387E150)
 c.emit('48 8b 54 24 60 44 8b 4c 24 58 41 c1 e1 01 31 c9')
 c.label('copy');c.emit('4c 8b 14 ca 4c 89 94 cc 80 00 00 00 ff c1 44 39 c9');c.rel('0f 8c','copy')
 c.emit('f3 0f 6f 84 24 80 01 00 00 f3 0f 7f 84 24');c.b.extend(struct.pack('<I',128+16*arg_index))
 c.emit('48 8d 84 24 80 00 00 00');c.rel('e9','call')
 c.label('original');c.emit('48 8b 44 24 60')
 c.label('call');c.emit('48 89 44 24 20 48 8b 4c 24 40 48 8b 54 24 48 4c 8b 44 24 50 4c 8b 4c 24 58')
 c.rel('e8',trampoline_rva);c.emit('48 89 84 24 a8 01 00 00')
 c.emit('48 83 bc 24 a0 01 00 00 00');c.rel('0f 84','done')
 c.emit('48 8d 8c 24 80 01 00 00');c.rel('e8',0x1EC6D0)
 c.emit('48 8b 8c 24 a0 01 00 00');c.rel('e8',free_rva)
 c.label('done');c.emit('48 8b 84 24 a8 01 00 00 48 81 c4 c8 01 00 00 c3')
 return c.finish()

def direct_guard(Code,rva,language_rva):
 # Same source-verified current-language getter; returns only original UTF-8.
 # Build independently to avoid instruction offsets depending on matcher changes.
 c=Code(rva);c.emit('48 83 ec 28 48 89 4c 24 20')
 c.rel('48 8b 0d',0x50C7810);c.emit('48 85 c9');c.rel('0f 84','no')
 c.emit('48 8b 01');c.rel('8b 15',0x4FB5818);c.emit('ff 50 08')
 c.emit('48 85 c0');c.rel('0f 84','no');c.emit('8b 50 0c 81 e2 ff ff ff 00 83 fa 01');c.rel('0f 85','no')
 c.emit('48 8b 00 48 85 c0');c.rel('0f 84','no');c.emit('48 8b 10 48 85 d2');c.rel('0f 84','no')
 c.rel('4c 8d 05',language_rva)
 c.label('language');c.emit('8a 02 41 3a 00');c.rel('0f 85','no');c.emit('84 c0');c.rel('0f 84','input')
 c.emit('48 ff c2 49 ff c0');c.rel('e9','language')
 c.label('input');c.emit('48 8b 4c 24 20 8b 41 0c 25 ff ff ff 00 83 f8 01');c.rel('0f 85','no')
 c.emit('48 8b 01 48 85 c0');c.rel('0f 84','no');c.emit('48 8b 00');c.rel('e9','done')
 c.label('no');c.emit('31 c0');c.label('done');c.emit('48 83 c4 28 c3')
 return c.finish()

def loading_wrapper(Code,rva,guard_rva,is_loading_rva,trampoline_rva,is_length):
 c=Code(rva);c.emit('48 81 ec 88 00 00 00') # 136-byte frame; no copied vector needed
 c.emit('48 89 4c 24 40 48 89 54 24 48 4c 89 44 24 50 4c 89 4c 24 58')
 c.emit('48 8b 84 24 b0 00 00 00 48 89 44 24 60')
 c.emit('45 85 c9');c.rel('0f 8e','original');c.emit('48 85 c0');c.rel('0f 84','original')
 c.emit('48 89 c1');c.rel('e8',guard_rva);c.emit('48 85 c0');c.rel('0f 84','original')
 c.emit('48 89 c1');c.rel('e8',is_loading_rva);c.emit('85 c0');c.rel('0f 84','original')
 if is_length:
  c.emit('48 8b 4c 24 40');c.rel('e8',0x1ec6d0)
  # Native loading coordinates divide by length-1. Three slots avoid 0/0
  # and put the complete phrase at the center slot; edge slots are empty.
  c.emit('48 8b 4c 24 40 48 b8 00 00 00 00 00 00 08 40 48 89 01 c7 41 08 00 00 00 00 c7 41 0c 00 00 00 00')
 else:
  # Copy the complete source RValue with native reference ownership instead of
  # extracting separate glyphs. The bitmap hook shapes this complete run later.
  c.emit('83 7c 24 58 02');c.rel('0f 8c','original')
  c.emit('48 8b 4c 24 60 48 83 c1 10');c.rel('e8',0x3857160)
  c.emit('48 b8 00 00 00 00 00 00 00 40 66 48 0f 6e c8 66 0f 2e c1');c.rel('0f 85','empty')
  c.emit('48 8b 54 24 60 48 8b 4c 24 40');c.rel('e8',0x1ec800);c.rel('e9','returned')
  c.label('empty');c.emit('48 8b 54 24 60 48 8b 12 48 8b 12 48 83 c2 '+format(len('جار التحميل...'.encode('utf8')),'02x')+' 48 8b 4c 24 40');c.rel('e8',0x387e150)
  c.label('returned')
 c.emit('48 8b 44 24 40');c.rel('e9','done')
 c.label('original');c.emit('48 8b 44 24 60 48 89 44 24 20 48 8b 4c 24 40 48 8b 54 24 48 4c 8b 44 24 50 4c 8b 4c 24 58')
 c.rel('e8',trampoline_rva)
 c.label('done');c.emit('48 81 c4 88 00 00 00 c3')
 return c.finish()
