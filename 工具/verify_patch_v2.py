from emulator_v2 import *
PHY=0x20004490
results=[]
def done(name,n):results.append({'test':name,'cases':n,'result':'PASS'});print('PASS',name,n,flush=True)
def key(e,k,down):e.invoke(PHY,k//16,k%16,down)
def new(b=patched,mode=1):
 e=Emulator(b);e.install_keymaps();e.set_byte(CFG,mode);return e

def usage(e,k):return k in e.read(REPORT+2,6) or bool(e.byte(REPORT+0xb+k//8)&(1<<(k%8)))
def media(e):return int.from_bytes(e.read(REPORT+0x2b,2),'little')
verify_image(original);verify_image(patched);done('image header/payload CRC and lengths',2)

for k in range(1,13):
 e=new();key(e,k,1)
 assert usage(e,k+0x39),(k,e.read(REPORT,0x34).hex())
 assert media(e)==0,(k,media(e))
 key(e,k,0);assert not usage(e,k+0x39),(k,'stuck function key')
done('physical F1-F12 default standard key press and release',12)

for k,m in [(1,0x70),(2,0x6f),(3,0x29f),(5,0xcf),(7,0xb6),(8,0xcd),(9,0xb5),(10,0xe2),(11,0xea),(12,0xe9)]:
 for fn_release_first in [False,True]:
  e=new();key(e,90,1);assert usage(e,0x73),'Mac Fn must emit F24'
  assert e.byte(STATE+4)==0
  key(e,k,1);assert media(e)==m,(k,media(e));assert usage(e,0x73)
  if fn_release_first:key(e,90,0);assert not usage(e,0x73)
  key(e,k,0);assert media(e)==0,(k,'stuck media')
  if not fn_release_first:key(e,90,0)
  assert not usage(e,0x73)
  assert e.byte(STATE+0x8c)==0
  assert not usage(e,k+0x39)
done('Fn+media, F24 coexists, both key-release orders',20)

for k in range(1,13):
 e=new();key(e,k,1);key(e,90,1);key(e,k,0)
 assert not usage(e,k+0x39),(k,'released normal key became media/stuck')
 key(e,90,0);assert not usage(e,0x73)
done('press F-row before Fn, release F-row while Fn held',12)

# Hold Fn across multiple media keys; Fn itself must remain down.
e=new();key(e,90,1)
for k,m in [(12,0xe9),(11,0xea),(10,0xe2),(12,0xe9)]:
 key(e,k,1);assert media(e)==m and usage(e,0x73)
 key(e,k,0);assert media(e)==0 and usage(e,0x73)
key(e,33,1);assert usage(e,0x14) and usage(e,0x73);key(e,33,0);key(e,90,0)
done('held Fn across repeated volume/mute and then Q',1)

# Win remains bit-for-bit identical at the report/layer/key-cache level.
for k in list(range(1,13))+[33,52,48,81,82,89,92]:
 for withfn in [False,True]:
  a=new(original,0);b=new(patched,0)
  for e in [a,b]:
   if withfn:key(e,90,1)
   key(e,k,1)
  assert a.read(REPORT,0x34)==b.read(REPORT,0x34),(k,withfn,'win report down')
  assert a.read(STATE,0x8e)==b.read(STATE,0x8e),(k,withfn,'win state down')
  for e in [a,b]:
   key(e,k,0)
   if withfn:key(e,90,0)
  assert a.read(REPORT,0x34)==b.read(REPORT,0x34),(k,withfn,'win report up')
  assert a.read(STATE,0x8e)==b.read(STATE,0x8e),(k,withfn,'win state up')
done('Win actual physical dispatcher differential, with/without Fn',38)

for mode in [0,1]:
 for action in range(256):
  if action==2:continue
  e=new(patched,mode);e.stop_on_original=True;e.invoke(FN,action,0x55,1)
  assert e.stopped_original
  assert [e.uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]]==[action,0x55,1]
done('non-Fn special handlers unchanged',510)

for mode,nextmode in [(0,1),(1,0)]:
 e=new(patched,mode);key(e,90,1);e.set_byte(CFG,nextmode);key(e,90,0)
 assert not usage(e,0x73) and e.byte(STATE+7)==0 and e.byte(STATE+0x8c)==0
done('Fn released after Win/Mac mode changes',2)

out={'revision':2,'sha256':hashlib.sha256(patched).hexdigest(),'cases':sum(x['cases'] for x in results),'tests':results,'scope':'ARM firmware routines, actual physical dispatcher; 3 non-key scan/report side-effect callbacks stubbed. No radio/bootloader/OS emulation.'}
(P/'verification-v2.json').write_text(json.dumps(out,indent=2)+'\n');print('TOTAL',out['cases'])
