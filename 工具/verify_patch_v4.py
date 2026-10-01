"""Offline Unicorn checks for revision v4. NO DEVICE ACCESS."""
from emulator_v2 import *
from build_patch_v4 import OUTPUT as V4OUT
cand=V4OUT.read_bytes();v2=patched
PHY=0x20004490;GLOBE=0x29d
results=[]
def done(name,n):results.append({'test':name,'cases':n,'result':'PASS'});print('PASS',name,n,flush=True)
def key(e,k,down):e.invoke(PHY,k//16,k%16,down)
def new(b=cand,mode=1):
 e=Emulator(b);e.install_keymaps();e.set_byte(CFG,mode);return e
def usage(e,k):return k in e.read(REPORT+2,6) or bool(e.byte(REPORT+0xb+k//8)&(1<<(k%8)))
def media(e):return int.from_bytes(e.read(REPORT+0x2b,2),'little')
def no_f24(e):assert not usage(e,0x73),'F24 must not be emitted'
verify_image(cand);done('image header/payload CRC and lengths',1)

e=new();key(e,90,1);assert media(e)==GLOBE and e.byte(REPORT+8)&8;no_f24(e)
key(e,90,0);assert media(e)==0;no_f24(e);assert e.byte(STATE+0x8c)==0
done('Mac Fn tap: Globe down/up, no F24',1)

for k in range(1,13):
 e=new();key(e,k,1)
 assert usage(e,k+0x39) and media(e)==0,(k,e.read(REPORT,0x34).hex())
 key(e,k,0);assert not usage(e,k+0x39)
done('physical F1-F12 default standard key press and release',12)

for k,m in [(1,0x70),(2,0x6f),(3,0x29f),(5,0xcf),(7,0xb6),(8,0xcd),(9,0xb5),(10,0xe2),(11,0xea),(12,0xe9)]:
 for fn_release_first in [False,True]:
  e=new();key(e,90,1);assert media(e)==GLOBE
  key(e,k,1);assert media(e)==m,(k,media(e));no_f24(e)
  if fn_release_first:key(e,90,0);assert media(e)==m,(k,'Fn release must not cut held media key')
  key(e,k,0);assert media(e)==0,(k,'stuck media')
  if not fn_release_first:key(e,90,0);assert media(e)==0
  no_f24(e);assert e.byte(STATE+0x8c)==0 and not usage(e,k+0x39)
done('Fn+F-row media, both key-release orders, no stuck usage',20)

for k in range(1,13):
 e=new();key(e,k,1);key(e,90,1);key(e,k,0)
 assert not usage(e,k+0x39),(k,'released normal key became media/stuck')
 key(e,90,0);assert media(e)==0;no_f24(e)
done('press F-row before Fn, release F-row while Fn held',12)

e=new();key(e,90,1)
for k,m in [(12,0xe9),(11,0xea),(10,0xe2),(12,0xe9)]:
 key(e,k,1);assert media(e)==m;key(e,k,0);assert media(e)==0
key(e,33,1);assert usage(e,0x14);key(e,33,0);key(e,90,0);assert media(e)==0;no_f24(e)
done('held Fn across repeated volume/mute and then Q',1)

# Fn + letters/navigation in Mac mode: keyboard report identical to v2 except v2's F24.
keys=[33,52,48,81,82,89,92]+list(range(16,32))+list(range(34,48))
for k in keys:
 a=new(v2,1);b=new(cand,1)
 for e in [a,b]:key(e,90,1);key(e,k,1)
 ra=bytearray(a.read(REPORT,0x2b));rb=bytes(b.read(REPORT,0x2b))
 for i in range(2,8):
  if ra[i]==0x73:ra[i]=0
 ra=bytes(ra[:2])+bytes(sorted(ra[2:8],reverse=True))+bytes(ra[8:]);rb=rb[:2]+bytes(sorted(rb[2:8],reverse=True))+rb[8:]
 assert ra[:8]==rb[:8] and ra[9:]==rb[9:],(k,ra.hex(),rb.hex())
 for e in [a,b]:key(e,k,0);key(e,90,0)
 assert media(b)==0;no_f24(b)
done('Mac Fn+key keyboard report equals v2 minus F24',len(keys))

for k in list(range(1,13))+[33,52,48,81,82,89,92]:
 for withfn in [False,True]:
  a=new(original,0);b=new(cand,0)
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
done('Win physical dispatcher differential vs official, with/without Fn',38)

for mode in [0,1]:
 for action in range(256):
  if action==2:continue
  e=new(cand,mode);e.stop_on_original=True;e.invoke(FN,action,0x55,1)
  assert e.stopped_original
  assert [e.uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]]==[action,0x55,1]
done('non-Fn special handlers unchanged',510)

for mode,nextmode in [(0,1),(1,0)]:
 e=new(cand,mode);key(e,90,1);e.set_byte(CFG,nextmode);key(e,90,0)
 assert media(e)==0 and not usage(e,0x73) and e.byte(STATE+7)==0 and e.byte(STATE+0x8c)==0
done('Fn released after Win/Mac mode changes',2)

out={'revision':'v4','sha256':hashlib.sha256(cand).hexdigest(),'cases':sum(x['cases'] for x in results),'tests':results,'scope':'ARM firmware routines in Unicorn; 3 non-key scan/report side-effect callbacks stubbed. No USB/radio/bootloader/macOS emulation.'}
(P/'verification-v4.json').write_text(json.dumps(out,indent=2)+'\n');print('TOTAL',out['cases'])
