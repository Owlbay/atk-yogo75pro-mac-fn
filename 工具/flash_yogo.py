"""Exact-model ATK Yogo75 PRO flasher. Read-only unless explicit CLI command.
Protocol derived from installed ATK HUB Beta; refuses unknown image hashes.
Usage: flash_yogo.py inspect | flash {v2,v4,original} --backup ../备份/<file>.json
"""
from pathlib import Path
import argparse,hashlib,json,struct,time,functools,operator,sys,tempfile
import hid,ctypes
# Share the composite HID interface; never seize ordinary keyboard input.
if sys.platform == "darwin":
 _hidlib=ctypes.CDLL(hid.__file__)
 _hidlib.hid_darwin_set_open_exclusive.argtypes=[ctypes.c_int]
 _hidlib.hid_darwin_set_open_exclusive(0)
from build_patch import verify_image,crc16_modbus,ORIGINAL,EXPECTED,P,RECORDS
from build_patch_v2 import OUTPUT as V2
from build_patch_v4 import OUTPUT as V4
IMAGES={'v2':V2,'v4':V4,'original':ORIGINAL}
LOGS=Path(tempfile.gettempdir())/'atk-yogo-flash-logs'
APP=(14139,4507);BOOT=(14000,13311);REPORT_ID=63
ERRORS={0:'SUCCESS',0xe0:'UNKNOWN_CMD',0xe1:'LENGTH_ERROR',0xe2:'CRC_ERROR',0xe3:'BLOCK_NUM_ERROR',0xe4:'BLOCK_SIZE_ERROR',0xe5:'WRITE_OFFSET_ERROR',0xe6:'READ_OFFSET_ERROR',0xe7:'ARGUMENT_ERROR',0xe8:'FLASH_OPERATION_FAILED',0xe9:'STATUS_ERROR',0xf0:'HEADER_IDENTIFY_ERROR',0xf1:'HEADER_CHIP_ID_ERROR',0xf3:'HEADER_HW_VERSION_ERROR',0xf4:'HEADER_SW_VERSION_ERROR',0xf5:'HEADER_CHECK_INFO_ERROR',0xf6:'HEADER_BLOCK_INFO_ERROR'}

def devices(pair):
 return [d for d in hid.enumerate(*pair) if d['usage_page']==0xff00 and d['usage']==1]

def business(cmd,data=b''):
 b=bytes([cmd])+struct.pack('<H',len(data))+data
 return b+struct.pack('>H',crc16_modbus(b))

def packets(b):
 n=(len(b)+55)//56
 for i in range(n):
  data=b[i*56:(i+1)*56]
  frame=bytearray(63);frame[0]=0xaa;frame[2]=n-i-1;frame[3]=0x80 if i==0 else 0;struct.pack_into('<H',frame,4,len(data));frame[6:6+len(data)]=data
  frame[6+len(data)]=functools.reduce(operator.xor,frame[1:6+len(data)],0)
  yield bytes(frame)

def image_packets(b):
 yield list(packets(business(0xa0,b[:128])))
 block=struct.unpack_from('<H',b,66)[0];data=b[128:];n=(len(data)+block-1)//block
 for i in range(n):
  off=i*block;part=data[off:off+block]
  yield list(packets(business(0xa1,struct.pack('<HI',0xffff if i==n-1 else i,off)+part)))
 yield list(packets(business(0xa4,struct.pack('<H',1000))))

class Link:
 def __init__(self,pair):
  ds=devices(pair)
  if len(ds)!=1:raise RuntimeError(f'Expected one {pair}; got {len(ds)}')
  self.pair=pair;self.h=hid.device();self.h.open_path(ds[0]['path']);self.rx=[];self.acks=[]
 def close(self):self.h.close()
 def read(self,timeout=200):
  r=bytes(self.h.read(65,timeout))
  if not r:return None
  if r[0]!=REPORT_ID:return None # never log ordinary keyboard reports
  r=r[1:]
  if r and r[0]==0xaa:
   self.rx.append(r.hex())
   # Hub's updater reads business ACK at bytes 6/7.
   if len(r)>7 and r[6]==0xb0:
    status=r[7];self.acks.append(status)
    if status!=0:raise RuntimeError(f'Bootloader rejected: {ERRORS.get(status,hex(status))}; response={r.hex()}')
   return r
  return None
 def drain(self,ms=200):
  until=time.monotonic()+ms/1000
  while time.monotonic()<until:
   self.read(20)
 def send_frame(self,frame):
  count=self.h.write(bytes([REPORT_ID])+frame)
  if count!=64:raise RuntimeError(f'Short HID write {count}')
  return self.read(250)
 def send_business(self,b):
  replies=[]
  for f in packets(b):
   r=self.send_frame(f)
   if r is not None:replies.append(r)
  return replies
 def save(self,label):
  LOGS.mkdir(exist_ok=True);(LOGS/f'{label}-vendor-replies.json').write_text(json.dumps({'pair':self.pair,'acks':self.acks,'vendor_replies':self.rx},indent=2)+'\n')

def wait_device(pair,seconds=15):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  if len(devices(pair))==1:return True
  time.sleep(.25)
 return False

def enter_boot():
 if devices(BOOT):raise RuntimeError('Already in bootloader; do not issue switch again')
 link=Link(APP)
 try:
  link.drain(150)
  # Byte-for-byte command from the installed Hub, including fixed token.
  frame=bytearray(63);frame[:15]=bytes.fromhex('aa0000800700c002006400690f4700')
  try:r=link.send_frame(frame);print('SWITCH_BOOT reply',r.hex() if r else 'device disconnected before reply',flush=True)
  except OSError:print('device disconnected during mode switch',flush=True)
 finally:link.save('enter-boot');link.close()
 if not wait_device(BOOT):raise RuntimeError('Bootloader did not enumerate; no flash erase/write has been sent')
 print('BOOTLOADER_ENUMERATED',flush=True)

def return_app():
 link=Link(BOOT)
 try:link.send_business(business(0xa4,struct.pack('<H',1000)))
 finally:link.save('return-app');link.close()
 if not wait_device(APP):raise RuntimeError('Application did not enumerate')
 print('APPLICATION_ENUMERATED',flush=True)

def allowed_hashes():
 h={EXPECTED}
 for m in ['patch-manifest-v2.json','patch-manifest-v4.json']:h.add(json.loads((P/m).read_text())['output_sha256'])
 return h

def flash(path,backup_path):
 b=path.read_bytes();verify_image(b)
 digest=hashlib.sha256(b).hexdigest()
 if digest not in allowed_hashes():raise RuntimeError('Unknown firmware hash')
 # Settings are reset by flashing; require this keyboard's settings backup first.
 backup=json.loads(Path(backup_path).read_text())
 assert (backup['vid'],backup['pid'])==APP and len(bytes.fromhex(backup['keyboard_config_hex']))==56,'invalid settings backup'
 assert path.resolve() in [x.resolve() for x in IMAGES.values()]
 # A completed read-only check and boot return trial is required.
 assert (P/'boot-return-verified.json').exists(),'Need successful bootloader return trial first'
 if not devices(BOOT):enter_boot()
 link=Link(BOOT);stage='start'
 try:
  link.drain(100)
  print('BEGIN',path.name,'sha256',digest,flush=True)
  groups=list(image_packets(b));before=len(link.acks)
  for frame in groups[0]:link.send_frame(frame)
  link.drain(2000)
  if len(link.acks)<=before:raise RuntimeError('No explicit START success ACK; refusing further writes')
  print('HEADER_ACCEPTED',flush=True)
  stage='write';total=len(groups)-2;last_progress=-1
  for i,group in enumerate(groups[1:-1]):
   for frame in group:link.send_frame(frame)
   percent=(i+1)*100//total
   if percent//10!=last_progress:
    print('WRITE_PROGRESS',percent,'%',flush=True);last_progress=percent//10
  link.drain(500)
  stage='switch-app'
  for frame in groups[-1]:link.send_frame(frame)
  link.save('flash')
 finally:
  link.save('flash');link.close()
 if not wait_device(APP,20):raise RuntimeError('No application after write; check bootloader before further action')
 receipt={'firmware':path.name,'sha256':digest,'stage':stage,'application_reenumerated':True,'acks':link.acks,'unix_time':time.time(),'note':'Reenumeration is not proof of functional correctness; requires keyboard event test.'}
 RECORDS.mkdir(exist_ok=True)
 (RECORDS/f"flash-receipt-{path.stem}-{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(receipt,indent=2)+'\n')
 print('APPLICATION_ENUMERATED_AFTER_WRITE',flush=True)

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('command',choices=['inspect','enter-boot','return-app','flash'])
 a.add_argument('image',nargs='?',choices=sorted(IMAGES));a.add_argument('--backup');args=a.parse_args()
 if args.command=='inspect':print(json.dumps({'application_interfaces':len(devices(APP)),'boot_interfaces':len(devices(BOOT))}))
 elif args.command=='enter-boot':enter_boot()
 elif args.command=='return-app':return_app()
 else:
  if not args.image or not args.backup:a.error('flash needs an image and --backup')
  flash(IMAGES[args.image],args.backup)
