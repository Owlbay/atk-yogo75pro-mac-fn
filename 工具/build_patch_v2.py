"""Offline revision 2: Mac Fn=F24 transport; F-row standard by default."""
from build_patch import P,FW,ORIGINAL,EXPECTED,BASE,TARGET,OFFSET,APPEND,verify_image,crc16_modbus,assemble
import hashlib,struct,json
OUTPUT=FW/'YOGO75PRO-v1.26-MAC-Fn-F24-StandardFRow-v2.bin'
RAM_SRC=0x0204da90;RAM_DST=0x200043b8

def image_offset(a):return a-BASE+128

def ram_offset(a):return RAM_SRC+(a-RAM_DST)-BASE+128

def jump_absolute(a,target):
 if a%4==2:return bytes.fromhex('dff804f000bf')+struct.pack('<I',target|1)+bytes.fromhex('00bf')
 assert a%4==0
 return bytes.fromhex('dff800f0')+struct.pack('<I',target|1)+bytes.fromhex('00bf00bf')

def build():
 b=ORIGINAL.read_bytes();assert hashlib.sha256(b).hexdigest()==EXPECTED;verify_image(b)
 code=assemble(P/'globe_patch_v2.s',P/'globe_patch_v2.o');assert len(code)==168
 hook=assemble(P/'entry_hook.s',P/'entry_hook.o')
 patches=[(OFFSET,b[OFFSET:OFFSET+4],hook,'special Fn handler'),
 (ram_offset(0x200044f2),bytes.fromhex('017902780244d1729df85710'),jump_absolute(0x200044f2,APPEND+0x2c),'cache Fn state for F-row key-down'),
 (ram_offset(0x20004548),bytes.fromhex('c97a817200211491807a0146'),jump_absolute(0x20004548,APPEND+0x58),'mask cached layer for keymap lookup'),
 (ram_offset(0x200045ce),bytes.fromhex('90f82700012840f04283ffe7'),jump_absolute(0x200045ce,APPEND+0x6c),'Mac F-row media only with Fn'),
 (ram_offset(0x20004766),bytes.fromhex('0bd1'),bytes.fromhex('00bf'),'allow Mac Fn+F6 focus function')]
 out=bytearray(b+code)
 for off,old,new,name in patches:
  assert b[off:off+len(old)]==old,(name,b[off:off+len(old)].hex())
  assert len(old)==len(new)
  out[off:off+len(new)]=new
 struct.pack_into('<I',out,110,len(out)-128)
 struct.pack_into('>H',out,62,crc16_modbus(out[128:]))
 struct.pack_into('>H',out,126,crc16_modbus(out[:126]))
 verify_image(out);assert BASE+len(out)-128<=0x02051000
 OUTPUT.write_bytes(out)
 m={'revision':2,'status':'OFFLINE TEST PENDING','behavior':'Mac Fn emits held F24, host maps device F24 to native Fn; F1-F12 standard, Fn+F-row uses original media actions. Win logic unchanged.','input_sha256':EXPECTED,'output_sha256':hashlib.sha256(out).hexdigest(),'output_file':OUTPUT.name,'size':len(out),'stub_address':hex(APPEND),'stub_length':len(code),'patches':[{'name':name,'file_offset':hex(off),'old':old.hex(),'new':new.hex()} for off,old,new,name in patches],'host_mapping':{'src':0x700000073,'dst':0xff00000003},'limitations':['No hardware validation of this revision yet','FnFunction keys use original ATK media actions; OS may interpret modifier+media differently','Bluetooth/2.4 GHz not tested']}
 (P/'patch-manifest-v2.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
if __name__=='__main__':build()
