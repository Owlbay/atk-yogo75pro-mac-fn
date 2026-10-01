"""Offline revision v4: Mac Fn = Consumer Globe 0x029D; v2 F-row logic kept. No device access."""
from build_patch import P,FW,ORIGINAL,EXPECTED,BASE,OFFSET,APPEND,verify_image,crc16_modbus,assemble
from build_patch_v2 import ram_offset,jump_absolute,OUTPUT as V2
import hashlib,struct,json
OUTPUT=FW/'YOGO75PRO-v1.26-MAC-Fn-Globe-v4.bin'

def build():
 b=ORIGINAL.read_bytes();assert hashlib.sha256(b).hexdigest()==EXPECTED;verify_image(b)
 v2code=assemble(P/'globe_patch_v2.s',P/'globe_patch_v2.o');assert len(v2code)==168
 code=assemble(P/'globe_patch_v4.s',P/'globe_patch_v4.o')
 # Trampoline targets used by v2 patches must be byte-identical.
 for start,end in [(0x2c,0x58),(0x58,0x6c),(0x6c,168)]:assert code[start:end]==v2code[start:end],hex(start)
 hook=assemble(P/'entry_hook.s',P/'entry_hook.o')
 patches=[(OFFSET,b[OFFSET:OFFSET+4],hook,'special Fn handler'),
 (ram_offset(0x200044f2),bytes.fromhex('017902780244d1729df85710'),jump_absolute(0x200044f2,APPEND+0x2c),'cache Fn state for F-row key-down'),
 (ram_offset(0x20004548),bytes.fromhex('c97a817200211491807a0146'),jump_absolute(0x20004548,APPEND+0x58),'mask cached layer for keymap lookup'),
 (ram_offset(0x200045ce),bytes.fromhex('90f82700012840f04283ffe7'),jump_absolute(0x200045ce,APPEND+0x6c),'Mac F-row media only with Fn'),
 (ram_offset(0x20004766),bytes.fromhex('0bd1'),bytes.fromhex('00bf'),'allow Mac Fn+F6 focus function')]
 out=bytearray(b+code)
 for off,old,new,name in patches:
  assert b[off:off+len(old)]==old,(name,b[off:off+len(old)].hex());assert len(old)==len(new)
  out[off:off+len(new)]=new
 struct.pack_into('<I',out,110,len(out)-128)
 struct.pack_into('<I',out,68,(len(out)-128+255)//256)
 struct.pack_into('>H',out,62,crc16_modbus(out[128:]))
 struct.pack_into('>H',out,126,crc16_modbus(out[:126]))
 verify_image(out);assert BASE+len(out)-128<=0x02051000,'must stay in existing last flash sector'
 v2=V2.read_bytes()
 diff=[i for i in range(128,len(v2)) if i<len(out) and v2[i]!=out[i]]
 assert all(i>=128+APPEND-BASE for i in diff),'only the appended stub may differ from v2'
 OUTPUT.write_bytes(out)
 m={'revision':'v4','status':'BUILT; see patch-manifest-v4.json history','behavior':'Mac Fn emits Consumer 0x029D (Globe) via the original media report; no host mapping needed. F1-F12 standard, Fn+F-row media as v2. Win logic unchanged.','input_sha256':EXPECTED,'v2_sha256':hashlib.sha256(v2).hexdigest(),'output_sha256':hashlib.sha256(out).hexdigest(),'output_file':OUTPUT.name,'size':len(out),'stub_address':hex(APPEND),'stub_length':len(code),'differs_from_v2_only_in':'header CRC/length and appended stub','patches':[{'name':name,'file_offset':hex(off),'old':old.hex(),'new':new.hex()} for off,old,new,name in patches],'limitations':['Globe is not a modifier in macOS IOHIDFamily; Fn+letter shortcuts may not work','Single media slot: Fn+F-row media temporarily replaces Globe while held','2.4 GHz untested']}
 (P/'patch-manifest-v4.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps({k:v for k,v in m.items() if k!='patches'},indent=2))
if __name__=='__main__':build()
