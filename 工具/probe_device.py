"""Read only ATK device info/config through the documented Hub command layout."""
from pathlib import Path
import hid,time,json,struct
P=Path(__file__).resolve().parent

def connect():
 ds=[d for d in hid.enumerate(14139,4507) if d['usage_page']==0xff60 and d['usage']==0x61]
 assert len(ds)==1,'Require one exact ATK Yogo75 PRO configuration interface'
 h=hid.device();h.open_path(ds[0]['path']);return h

def request(h,cmd,offset=0,length=0):
 assert cmd in [0x10,0x11,0x12,0x14,0x16,0x17,0x18,0x19,0x1a,0x1c,0x1e,0x20,0x22,0x24,0x26,0x30], 'read-only commands only'
 seq=(time.monotonic_ns()&0xffff) or 1
 b=bytearray(64);b[0:2]=bytes([0xaa,cmd]);struct.pack_into('<H',b,2,offset);b[4]=length;struct.pack_into('<H',b,5,seq)
 h.write(b'\0'+b)
 end=time.monotonic()+3
 while time.monotonic()<end:
  r=bytes(h.read(65,200))
  if r.startswith(b'\0\xaa'):r=r[1:]
  if len(r)>=8 and r[0]==0xaa and struct.unpack_from('<H',r,5)[0]==seq:
   if r[2]==255:raise RuntimeError('device rejected '+r.hex())
   return r
 raise TimeoutError(f'No matching reply cmd={cmd:02x}')

if __name__=='__main__':
 from build_patch import BACKUPS
 h=connect()
 try:
  request(h,0x10)
  data=request(h,0x12,0,56)[8:64];cfg=request(h,0x14,0,56)[8:64];tail=request(h,0x14,56,8)[8:16]
  mats={f'{cmd:02x}':b''.join(request(h,cmd,o,56)[8:64] for o in range(0,392,56)).hex() for cmd in [0x16,0x17,0x18,0x19,0x1a,0x1c,0x1e,0x20]}
  request(h,0x11)
 finally:h.close()
 out={'vid':int.from_bytes(data[2:4],'little'),'pid':int.from_bytes(data[4:6],'little'),'version':data[6:8][::-1].hex(),'date':time.strftime('%Y-%m-%d'),
  'device_info_hex':data.hex(),'keyboard_config_hex':cfg.hex(),'keyboard_config_tail_hex':tail.hex(),'macWin':cfg[39],'sixN':cfg[38],'keymaps':mats}
 target=BACKUPS/f"键盘备份-V{out['version']}-{time.strftime('%Y%m%d-%H%M%S')}.json"
 assert not target.exists(),'refuse to overwrite'
 BACKUPS.mkdir(exist_ok=True);target.write_text(json.dumps(out,indent=2)+'\n')
 print(target);print(json.dumps({k:v for k,v in out.items() if k!='keymaps'},indent=2))
