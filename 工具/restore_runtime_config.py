"""Restore a settings backup using the Hub's two-part config write, then read back.
Usage: restore_runtime_config.py --backup ../备份/<file>.json
"""
from probe_device import *
from build_patch import RECORDS
import argparse,time,struct,json
a=argparse.ArgumentParser();a.add_argument('--backup',required=True);args=a.parse_args()
before=json.loads(Path(args.backup).read_text());original=bytes.fromhex(before['keyboard_config_hex']);assert len(original)==56
backup_tail=bytes.fromhex(before['keyboard_config_tail_hex']) if 'keyboard_config_tail_hex' in before else None
h=connect()
def write_part(data,offset):
 seq=(time.monotonic_ns()&0xffff) or 1
 packet=bytearray(64);packet[0]=0xaa;packet[1]=0x15;struct.pack_into('<H',packet,2,offset);packet[4]=len(data);struct.pack_into('<H',packet,5,seq);packet[8:8+len(data)]=data
 assert h.write(b'\0'+packet)==65
 end=time.monotonic()+3
 while time.monotonic()<end:
  r=bytes(h.read(65,200));r=r[1:] if r.startswith(b'\0\xaa') else r
  if len(r)>=8 and r[0]==0xaa and int.from_bytes(r[5:7],'little')==seq:
   assert r[2]!=255,'Device rejected config write';return
 raise TimeoutError('No configuration ACK')
try:
 request(h,0x10);current=request(h,0x14,0,56)[8:64];tail=request(h,0x14,56,8)[8:16]
 assert current[39]==original[39],'Mac/Win mode differs from backup; refusing'
 tail_to_write=backup_tail if backup_tail is not None else tail
 write_part(original,0);write_part(tail_to_write,56)
 time.sleep(0.4)
 result=request(h,0x14,0,56)[8:64];result_tail=request(h,0x14,56,8)[8:16]
 keymaps={f'{c:02x}':b''.join(request(h,c,o,56)[8:64] for o in range(0,392,56)).hex() for c in [0x16,0x17,0x18,0x19,0x1a,0x1c,0x1e,0x20]}
 request(h,0x11)
 differences=[{'offset':i,'expected':x,'actual':y} for i,(x,y) in enumerate(zip(original,result)) if x!=y]
 out={'backup':Path(args.backup).name,'matches_backup_config':result==original,'tail_matches':result_tail==tail_to_write,
  'keymaps_match_backup':(keymaps==before['keymaps']) if 'keymaps' in before else None,
  'remaining_differences':differences,'macWin':result[39],'config_hex':result.hex(),'write_parts':[56,8]}
 RECORDS.mkdir(exist_ok=True)
 (RECORDS/f"config-restoration-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
finally:h.close()
